import json

import pytest

from app.brain import BrainDecisionRejected, deterministic_decision, validate_decision
from app.budgets import clamp_budget
from app.models import Budget, CapabilityType, SourceClass, TaskType
from app.task import classify_task
from app.source_policy import SourcePolicyMode, configured_source_policy


def valid_decision(**overrides):
    value = {
        "decision_version": "1",
        "intent": "contract_lookup",
        "task_type": "CORPORATE_KNOWLEDGE",
        "source_policy": ["CORPORATE"],
        "required_capabilities": ["CORPORATE_RETRIEVAL"],
        "plan": [{"step_id": "retrieve", "capability": "CORPORATE_RETRIEVAL", "depends_on": []}],
        "clarification_required": False,
        "reason": "corporate document question",
    }
    value.update(overrides)
    return json.dumps(value)


def test_accepts_valid_decision():
    decision = validate_decision(
        valid_decision(), question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget()
    )
    assert decision.task_type == TaskType.CORPORATE_KNOWLEDGE


@pytest.mark.parametrize("raw", ["{}", "not-json", valid_decision(extra="chain of thought")])
def test_rejects_invalid_schema(raw):
    with pytest.raises(BrainDecisionRejected):
        validate_decision(raw, question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget())


def test_accepts_structured_query_for_corporate_task():
    raw = valid_decision(
        intent="structured_document_query",
        required_capabilities=["STRUCTURED_QUERY"],
        plan=[
            {
                "step_id": "structured-query",
                "capability": "STRUCTURED_QUERY",
                "input": {
                    "source_file": "DfQueryToExcel (7.1).xls",
                    "sheet": "Export-D2",
                    "filters": [
                        {"column": "Край", "operator": "gte", "value": "05.10.2026"},
                        {"column": "Край", "operator": "lte", "value": "31.01.2027"},
                    ],
                },
            }
        ],
    )

    decision = validate_decision(
        raw,
        question="Покажи договорите от DfQueryToExcel (7.1).xls с крайна дата до 31.01.2027.",
        allowed_sources=[SourceClass.CORPORATE],
        budget=Budget(),
    )

    assert decision.task_type == TaskType.CORPORATE_KNOWLEDGE
    assert decision.plan[0].capability == CapabilityType.STRUCTURED_QUERY
    assert decision.plan[0].input["source_file"] == "DfQueryToExcel (7.1).xls"


def test_rejects_structured_query_without_exact_document_reference():
    raw = valid_decision(
        required_capabilities=["STRUCTURED_QUERY"],
        plan=[
            {
                "step_id": "structured-query",
                "capability": "STRUCTURED_QUERY",
                "input": {
                    "sheet": "Export-D2",
                    "filters": [],
                },
            }
        ],
    )

    with pytest.raises(
        BrainDecisionRejected,
        match="structured query requires exact source_file or document_id/version",
    ):
        validate_decision(
            raw,
            question="Покажи данните от таблицата.",
            allowed_sources=[SourceClass.CORPORATE],
            budget=Budget(),
        )


def test_rejects_structured_query_with_ambiguous_document_reference():
    raw = valid_decision(
        required_capabilities=["STRUCTURED_QUERY"],
        plan=[
            {
                "step_id": "structured-query",
                "capability": "STRUCTURED_QUERY",
                "input": {
                    "source_file": "DfQueryToExcel (7.1).xls",
                    "document_id": "a37ea2b0-a9d8-4b0b-8d35-08e90fee632e",
                    "version": 1,
                },
            }
        ],
    )

    with pytest.raises(
        BrainDecisionRejected,
        match="structured query cannot combine source_file with document_id/version",
    ):
        validate_decision(
            raw,
            question="Покажи данните от конкретния документ.",
            allowed_sources=[SourceClass.CORPORATE],
            budget=Budget(),
        )


def test_rejects_structured_query_without_corporate_source():
    raw = valid_decision(
        source_policy=["WEB"],
        required_capabilities=["STRUCTURED_QUERY"],
        plan=[
            {
                "step_id": "structured-query",
                "capability": "STRUCTURED_QUERY",
                "input": {
                    "source_file": "DfQueryToExcel (7.1).xls",
                },
            }
        ],
    )

    with pytest.raises(BrainDecisionRejected, match="corporate capability is not authorized"):
        validate_decision(
            raw,
            question="Покажи договорите от DfQueryToExcel (7.1).xls.",
            allowed_sources=[SourceClass.WEB],
            budget=Budget(),
        )


def test_rejects_unknown_or_disallowed_capability():
    with pytest.raises(BrainDecisionRejected):
        validate_decision(
            valid_decision(required_capabilities=["LLM_REASONING"], plan=[{"step_id": "x", "capability": "LLM_REASONING"}]),
            question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget(),
        )


def test_rejects_source_policy_self_elevation():
    with pytest.raises(BrainDecisionRejected):
        validate_decision(
            valid_decision(source_policy=["CORPORATE", "WEB"], required_capabilities=["CORPORATE_RETRIEVAL", "WEB_SEARCH"], plan=[
                {"step_id": "retrieve", "capability": "CORPORATE_RETRIEVAL"},
                {"step_id": "search", "capability": "WEB_SEARCH", "depends_on": ["retrieve"]},
            ]),
            question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget(),
        )


def test_rejects_decision_that_drops_required_corporate_source():
    with pytest.raises(BrainDecisionRejected):
        validate_decision(
            valid_decision(task_type="GENERAL", required_capabilities=[], plan=[]),
            question="Какво пише в договора за цена?",
            allowed_sources=[SourceClass.CORPORATE, SourceClass.WEB],
            budget=Budget(),
        )


def test_rejects_brain_adding_corporate_source_to_web_only_question():
    elevated = {
        "decision_version": "1",
        "intent": "current_public_information",
        "task_type": "CORPORATE_AND_WEB",
        "source_policy": ["CORPORATE", "WEB"],
        "required_capabilities": ["CORPORATE_RETRIEVAL", "WEB_SEARCH"],
        "plan": [
            {"step_id": "retrieve", "capability": "CORPORATE_RETRIEVAL", "depends_on": []},
            {"step_id": "search", "capability": "WEB_SEARCH", "depends_on": ["retrieve"]},
        ],
        "clarification_required": False,
        "reason": "The public question requires web research.",
    }
    with pytest.raises(BrainDecisionRejected, match="differs from deterministic"):
        validate_decision(
            elevated,
            question="What is the latest stable Python release? Use the official python.org source.",
            allowed_sources=[SourceClass.CORPORATE, SourceClass.WEB],
            budget=Budget(),
        )


def test_rejects_invalid_dependencies_and_budget():
    with pytest.raises(BrainDecisionRejected):
        validate_decision(
            valid_decision(plan=[{"step_id": "a", "capability": "CORPORATE_RETRIEVAL", "depends_on": ["later"]}]),
            question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget(),
        )
    with pytest.raises(BrainDecisionRejected):
        validate_decision(
            valid_decision(plan=[{"step_id": "a", "capability": "CORPORATE_RETRIEVAL"}, {"step_id": "b", "capability": "CORPORATE_RETRIEVAL"}]),
            question="договор", allowed_sources=[SourceClass.CORPORATE], budget=Budget(max_steps=1),
        )


def test_file_table_query_is_corporate_with_web_fallback_allowed():
    task_type = classify_task(
        "Покажи ми редовете от таблицата във файла DfQueryToExcel",
        [SourceClass.CORPORATE, SourceClass.WEB],
    )
    assert task_type == TaskType.CORPORATE_KNOWLEDGE


def test_deterministic_fallback_is_bounded_and_source_limited():
    decision = deterministic_decision("Покажи договора", [SourceClass.CORPORATE], Budget())
    assert decision.task_type == TaskType.CORPORATE_KNOWLEDGE
    assert {step.capability for step in decision.plan} == {CapabilityType.CORPORATE_RETRIEVAL}


def test_general_fallback_uses_only_controlled_general_response():
    decision = deterministic_decision("Обясни как работи фотосинтезата", [SourceClass.CORPORATE, SourceClass.WEB], Budget())
    assert decision.task_type == TaskType.GENERAL
    assert [step.capability for step in decision.plan] == [CapabilityType.GENERAL_RESPONSE]


def test_contract_and_current_official_price_uses_corporate_then_web_route():
    task_type = classify_task(
        "Какви са актуалните цени на услугите по договор A202300904-000-00? Използвай официалния сайт.",
        [SourceClass.CORPORATE, SourceClass.WEB],
    )
    assert task_type == TaskType.CORPORATE_AND_WEB


@pytest.mark.parametrize("mode, expected", [
    ("INTERNAL_ONLY", [SourceClass.CORPORATE]),
    ("INTERNAL_FIRST_WEB_FALLBACK", [SourceClass.CORPORATE, SourceClass.WEB]),
    ("EXPLICIT_WEB", [SourceClass.WEB]),
    ("RESTRICTED_OFFLINE", [SourceClass.CORPORATE]),
])
def test_server_source_policy_modes(mode, expected):
    resolved_mode, sources = configured_source_policy(mode)
    assert resolved_mode == SourcePolicyMode(mode)
    assert sources == expected


def test_requested_budgets_can_only_reduce_server_limits():
    requested = Budget(
        max_steps=100,
        max_capability_calls=100,
        max_retrieval_rounds=20,
        max_web_searches=20,
        max_web_fetches=50,
        max_verification_rounds=10,
        max_context_chars=1_000_000,
    )
    result = clamp_budget(requested)
    assert result == Budget()
