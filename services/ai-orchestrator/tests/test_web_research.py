import pytest
from app.models import EvidenceRecord, SourceClass, Task
from app.web_research import (
    WebFetchSelection,
    build_web_fetch_selection_messages,
    parse_web_fetch_selection,
)


def _evidence():
    return [
        EvidenceRecord(
            evidence_id="WEB:one",
            source_class=SourceClass.WEB,
            source_id="https://example.com/one",
            source_location="https://example.com/one",
            claim="First source content.",
            authority="example.com",
            access_scope="PUBLIC",
            trusted_as_instruction=False,
        ),
        EvidenceRecord(
            evidence_id="WEB:two",
            source_class=SourceClass.WEB,
            source_id="https://example.org/two",
            source_location="https://example.org/two",
            claim="Second source content.",
            authority="example.org",
            access_scope="PUBLIC",
            trusted_as_instruction=False,
        ),
    ]


def test_web_fetch_selection_accepts_only_evidence_ids():
    result = parse_web_fetch_selection(
        '{"evidence_ids":["WEB:one"],"reason":"Primary source needs full fetch."}',
        _evidence(),
    )

    assert isinstance(result, WebFetchSelection)
    assert result.evidence_ids == ["WEB:one"]
    assert result.reason == "Primary source needs full fetch."


def test_web_fetch_selection_rejects_unknown_evidence_id():
    try:
        parse_web_fetch_selection(
            '{"evidence_ids":["WEB:unknown"],"reason":"fetch"}',
            _evidence(),
        )
    except ValueError as exc:
        assert "unknown evidence_id" in str(exc).lower()
    else:
        raise AssertionError("Unknown evidence_id must be rejected")


def test_web_fetch_selection_context_contains_provenance_and_exact_ids():
    messages = build_web_fetch_selection_messages(
        Task(user_request="Кой е актуалният официален източник?"),
        _evidence(),
    )

    prompt = messages[1]["content"]

    assert "WEB:one" in prompt
    assert "WEB:two" in prompt
    assert "https://example.com/one" in prompt
    assert "source_class: WEB" in prompt
    assert "authority: example.com" in prompt


def test_web_fetch_selection_rejects_non_web_evidence():
    evidence = [
        EvidenceRecord(
            evidence_id="CORP:one",
            source_class=SourceClass.CORPORATE,
            source_id="internal-doc",
            claim="Internal content.",
            access_scope="INTERNAL",
        )
    ]

    try:
        parse_web_fetch_selection(
            '{"evidence_ids":["CORP:one"],"reason":"fetch"}',
            evidence,
        )
    except ValueError as exc:
        assert "web" in str(exc).lower()
    else:
        raise AssertionError("Non-WEB evidence must not be selectable for web fetch")


def test_web_fetch_selection_enforces_requested_limit():
    evidence = _evidence()

    try:
        parse_web_fetch_selection(
            '{"evidence_ids":["WEB:one","WEB:two"],"reason":"fetch both"}',
            evidence,
            max_selections=1,
        )
    except ValueError as exc:
        assert "maximum" in str(exc).lower()
    else:
        raise AssertionError("Selection limit must be enforced")


class _FakeLLMCapability:
    capability_type = "LLM_REASONING"

    def __init__(self):
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        from app.capabilities import CapabilityResult

        return CapabilityResult(
            capability=request.capability,
            success=True,
            data={
                "content": (
                    '{"evidence_ids":["WEB:one"],'
                    '"reason":"Primary source requires full content."}'
                )
            },
        )


class _FakeRegistry:
    def __init__(self, capability):
        self.capability = capability

    def get(self, capability_type):
        return self.capability


def test_orchestrator_select_web_fetch_candidates_uses_llm_and_budget():
    import asyncio

    from app.budgets import BudgetController
    from app.models import Budget, CapabilityType
    from app.orchestrator import Orchestrator

    llm = _FakeLLMCapability()
    orchestrator = Orchestrator(registry=_FakeRegistry(llm))
    budget = BudgetController(
        Budget(
            max_steps=12,
            max_capability_calls=1,
            max_retrieval_rounds=3,
            max_web_searches=3,
            max_web_fetches=1,
            max_verification_rounds=2,
            max_context_chars=120000,
        )
    )

    result = asyncio.run(
        orchestrator.select_web_fetch_candidates(
            Task(user_request="Кой е официалният източник?"),
            _evidence(),
            budget,
        )
    )

    assert result.evidence_ids == ["WEB:one"]
    assert len(llm.calls) == 1
    assert budget.usage.capability_calls == 1
    assert llm.calls[0].capability == CapabilityType.LLM_REASONING


def test_web_fetch_step_depends_on_web_search():
    from app.models import CapabilityType, SourceClass, TaskType
    from app.planner import build_plan

    task = Task(user_request="Какво е актуалното състояние?", normalized_question="Какво е актуалното състояние?")
    task.task_type = TaskType.WEB_RESEARCH
    task.allowed_source_classes = [SourceClass.WEB]

    plan = build_plan(task)

    assert any(
        step.capability == CapabilityType.WEB_SEARCH
        for step in plan.steps
    )

    search_step = next(
        step for step in plan.steps
        if step.capability == CapabilityType.WEB_SEARCH
    )

    assert search_step.depends_on == []


def test_web_fetch_step_is_blocked_when_dependency_failed():
    from app.models import CapabilityType, PlanStep, StepStatus

    search_step = PlanStep(
        step_id="web-search-1",
        type="SEARCH_WEB",
        capability=CapabilityType.WEB_SEARCH,
        status=StepStatus.FAILED,
    )

    fetch_step = PlanStep(
        step_id="web-fetch-1",
        type="FETCH_WEB",
        capability=CapabilityType.WEB_FETCH,
        depends_on=["web-search-1"],
    )

    assert search_step.status == StepStatus.FAILED
    assert fetch_step.depends_on == ["web-search-1"]




def test_execute_plan_selectively_fetches_selected_web_source(monkeypatch):
    import asyncio

    from app.capabilities import CapabilityResult
    from app.models import (
        CapabilityType,
        EvidenceRecord,
        SourceClass,
        Task,
        TaskType,
    )
    from app.orchestrator import Orchestrator

    task = Task(
        user_request="Какво е актуалното състояние?",
        normalized_question="Какво е актуалното състояние?",
    )
    task.task_type = TaskType.WEB_RESEARCH
    task.allowed_source_classes = [SourceClass.WEB]

    orchestrator = Orchestrator()

    calls = []

    class FakeCapability:
        async def execute(self, request):
            calls.append(
                (
                    request.capability,
                    dict(request.input),
                )
            )

            if request.capability == CapabilityType.WEB_SEARCH:
                return CapabilityResult(
                    capability=CapabilityType.WEB_SEARCH,
                    success=True,
                    data={
                        "retrieval_status": "FOUND",
                        "source_class": "WEB",
                        "evidence": [
                            {
                                "result_id": "r1",
                                "title": "Official source",
                                "url": "https://example.com/source",
                                "domain": "example.com",
                                "snippet": "Official result",
                                "content": "Official result",
                                "access_scope": "PUBLIC",
                            },
                            {
                                "result_id": "r2",
                                "title": "Other source",
                                "url": "https://example.org/other",
                                "domain": "example.org",
                                "snippet": "Other result",
                                "content": "Other result",
                                "access_scope": "PUBLIC",
                            },
                        ],
                    },
                )

            if request.capability == CapabilityType.WEB_FETCH:
                assert request.input["url"] == "https://example.com/source"
                return CapabilityResult(
                    capability=CapabilityType.WEB_FETCH,
                    success=True,
                    data={
                        "retrieval_status": "FOUND",
                        "source_class": "WEB",
                        "evidence": [
                            {
                                "url": "https://example.com/source",
                                "domain": "example.com",
                                "content": "Full authoritative content",
                                "access_scope": "PUBLIC",
                            }
                        ],
                    },
                )

            if request.capability == CapabilityType.LLM_REASONING:
                return CapabilityResult(
                    capability=CapabilityType.LLM_REASONING,
                    success=True,
                    data={
                        "content": '{"answer":"ok","material_claims":[],"resolution":"ANSWERABLE","needs_clarification":false,"clarification_question":null,"uncertainty":null}'
                    },
                )

            raise AssertionError(f"Unexpected capability: {request.capability}")

    class FakeRegistry:
        def get(self, capability):
            return FakeCapability()

    orchestrator.registry = FakeRegistry()

    async def fake_selector(task_arg, evidence_arg, budget_arg):
        assert len(evidence_arg) == 2
        assert all(item.source_class == SourceClass.WEB for item in evidence_arg)
        return type(
            "Selection",
            (),
            {
                "evidence_ids": [evidence_arg[0].evidence_id],
                "reason": "official source",
            },
        )()

    monkeypatch.setattr(
        orchestrator,
        "select_web_fetch_candidates",
        fake_selector,
    )

    async def fake_synthesize(task_arg, evidence_arg, budget_arg):
        return type(
            "Synthesis",
            (),
            {
                "resolution": __import__("app.models", fromlist=["QuestionResolution"]).QuestionResolution.ANSWERABLE,
                "answer": "ok",
                "material_claims": [],
                "evidence_ids": [],
            },
        )()

    monkeypatch.setattr(
        orchestrator,
        "synthesize_answer",
        fake_synthesize,
    )

    monkeypatch.setattr(
        "app.orchestrator.evaluate_evidence",
        lambda evidence: type(
            "Evaluation",
            (),
            {
                "applicable": evidence,
                "status": None,
            },
        )(),
    )

    monkeypatch.setattr(
        "app.orchestrator.analyze_conflicts",
        lambda evidence: type(
            "Conflicts",
            (),
            {
                "conflicts": [],
            },
        )(),
    )

    result = asyncio.run(
        orchestrator.execute_plan(
            task,
            orchestrator.create_plan(task),
        )
    )

    capability_calls = [item[0] for item in calls]

    assert capability_calls.count(CapabilityType.WEB_SEARCH) == 1
    assert capability_calls.count(CapabilityType.WEB_FETCH) == 1
    assert capability_calls.index(CapabilityType.WEB_SEARCH) < capability_calls.index(
        CapabilityType.WEB_FETCH
    )
    assert any(
        capability == CapabilityType.WEB_FETCH
        and payload["url"] == "https://example.com/source"
        for capability, payload in calls
    )
