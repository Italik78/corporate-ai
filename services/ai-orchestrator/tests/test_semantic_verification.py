import asyncio

from app.budgets import BudgetController
from app.capabilities import CapabilityResult
from app.models import (
    Budget,
    CapabilityType,
    EvidenceRecord,
    SourceClass,
    SynthesisClaim,
    Task,
)
from app.semantic_verification import (
    SemanticVerificationStatus,
    build_semantic_verification_messages,
    parse_semantic_verification_result,
    verify_claim_semantically,
    verify_claims_semantically,
)


def _evidence():
    return [
        EvidenceRecord(
            evidence_id="CORP:contract-1",
            source_class=SourceClass.CORPORATE,
            source_id="contract-1",
            source_location="contract-1.pdf",
            claim=(
                "Времето за реакция при критичен инцидент е до 1 час, "
                "а времето за разрешаване е до 4 часа."
            ),
            authority="contract-1",
            access_scope="INTERNAL",
            version=1,
        ),
        EvidenceRecord(
            evidence_id="CORP:contract-2",
            source_class=SourceClass.CORPORATE,
            source_id="contract-2",
            source_location="contract-2.pdf",
            claim=(
                "За различен договор времето за реакция е до 30 минути."
            ),
            authority="contract-2",
            access_scope="INTERNAL",
            version=1,
        ),
    ]


def _budget(max_capability_calls=1, max_verification_rounds=1):
    return BudgetController(
        Budget(
            max_steps=12,
            max_capability_calls=max_capability_calls,
            max_retrieval_rounds=3,
            max_web_searches=3,
            max_web_fetches=5,
            max_verification_rounds=max_verification_rounds,
            max_context_chars=120000,
        )
    )


class _FakeLLMCapability:
    capability_type = CapabilityType.LLM_REASONING

    def __init__(self, content):
        self.content = content
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return CapabilityResult(
            capability=request.capability,
            success=True,
            data={"content": self.content},
        )


class _FakeRegistry:
    def __init__(self, capability):
        self.capability = capability

    def get(self, capability_type):
        assert capability_type == CapabilityType.LLM_REASONING
        return self.capability


def test_parse_semantic_verification_result_accepts_supported():
    result = parse_semantic_verification_result(
        '{"status":"SUPPORTED","reason":"The evidence directly supports the claim."}'
    )

    assert result.status == SemanticVerificationStatus.SUPPORTED
    assert result.reason == "The evidence directly supports the claim."


def test_parse_semantic_verification_result_rejects_invalid_status():
    try:
        parse_semantic_verification_result(
            '{"status":"MAYBE","reason":"unclear"}'
        )
    except ValueError as exc:
        assert "invalid status" in str(exc).lower()
    else:
        raise AssertionError("Invalid semantic verification status must be rejected")


def test_semantic_verification_uses_only_claim_citations():
    messages = build_semantic_verification_messages(
        Task(
            user_request="Какъв е срокът?",
            normalized_question="Какъв е срокът?",
        ),
        SynthesisClaim(
            claim="Времето за реакция е до 1 час.",
            evidence_ids=["CORP:contract-1"],
        ),
        _evidence(),
    )

    prompt = messages[1]["content"]

    assert "CORP:contract-1" in prompt
    assert "CORP:contract-2" not in prompt


def test_semantic_verification_supported():
    llm = _FakeLLMCapability(
        '{"status":"SUPPORTED","reason":"The evidence states a one-hour response time."}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_claim_semantically(
            task=Task(
                user_request="Какъв е срокът за реакция?",
                normalized_question="Какъв е срокът за реакция?",
            ),
            claim=SynthesisClaim(
                claim="Времето за реакция е до 1 час.",
                evidence_ids=["CORP:contract-1"],
            ),
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert result.status == SemanticVerificationStatus.SUPPORTED
    assert len(llm.calls) == 1
    assert llm.calls[0].capability == CapabilityType.LLM_REASONING


def test_semantic_verification_contradicted():
    llm = _FakeLLMCapability(
        '{"status":"CONTRADICTED","reason":"The evidence states resolution takes up to four hours."}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_claim_semantically(
            task=Task(
                user_request="Какъв е срокът за разрешаване?",
                normalized_question="Какъв е срокът за разрешаване?",
            ),
            claim=SynthesisClaim(
                claim="Времето за разрешаване е до 1 час.",
                evidence_ids=["CORP:contract-1"],
            ),
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert result.status == SemanticVerificationStatus.CONTRADICTED


def test_semantic_verification_insufficient():
    llm = _FakeLLMCapability(
        '{"status":"INSUFFICIENT","reason":"The evidence applies to different contracts."}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_claim_semantically(
            task=Task(
                user_request="Какъв е общият срок?",
                normalized_question="Какъв е общият срок?",
            ),
            claim=SynthesisClaim(
                claim="За всички договори времето за реакция е до 1 час.",
                evidence_ids=["CORP:contract-1"],
            ),
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert result.status == SemanticVerificationStatus.INSUFFICIENT


def test_semantic_verification_consumes_verification_budget():
    llm = _FakeLLMCapability(
        '{"status":"SUPPORTED","reason":"Direct support."}'
    )
    registry = _FakeRegistry(llm)
    budget = _budget(max_capability_calls=1, max_verification_rounds=1)

    asyncio.run(
        verify_claim_semantically(
            task=Task(user_request="Какъв е срокът?"),
            claim=SynthesisClaim(
                claim="Времето за реакция е до 1 час.",
                evidence_ids=["CORP:contract-1"],
            ),
            evidence=_evidence(),
            budget=budget,
            registry=registry,
        )
    )

    assert budget.usage.capability_calls == 1
    assert budget.usage.verification_rounds == 1


def test_semantic_verification_batch_checks_each_claim_against_its_citations():
    llm = _FakeLLMCapability(
        '{"results":['
        '{"claim_index":0,"status":"SUPPORTED","reason":"Directly supported."},'
        '{"claim_index":1,"status":"CONTRADICTED","reason":"The cited evidence gives a different value."}'
        ']}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_claims_semantically(
            task=Task(
                user_request="Какви са сроковете?",
                normalized_question="Какви са сроковете?",
            ),
            claims=[
                SynthesisClaim(
                    claim="Времето за реакция е до 1 час.",
                    evidence_ids=["CORP:contract-1"],
                ),
                SynthesisClaim(
                    claim="Времето за разрешаване е до 1 час.",
                    evidence_ids=["CORP:contract-1"],
                ),
            ],
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert len(result) == 2
    assert result[0].status == SemanticVerificationStatus.SUPPORTED
    assert result[1].status == SemanticVerificationStatus.CONTRADICTED
    assert len(llm.calls) == 1

    prompt = llm.calls[0].input["messages"][1]["content"]
    assert "CLAIM_INDEX: 0" in prompt
    assert "CLAIM_INDEX: 1" in prompt
    assert "CORP:contract-1" in prompt
    assert "CORP:contract-2" not in prompt


def test_semantic_answer_verification_supported_when_answer_matches_claims():
    from app.semantic_verification import verify_answer_semantically

    llm = _FakeLLMCapability(
        '{"status":"SUPPORTED","reason":"The final answer faithfully matches the claims and evidence."}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_answer_semantically(
            task=Task(
                user_request="Какъв е срокът за реакция и разрешаване?",
                normalized_question="Какъв е срокът за реакция и разрешаване?",
            ),
            answer=(
                "При критичен инцидент времето за реакция е до 1 час, "
                "а времето за разрешаване е до 4 часа."
            ),
            claims=[
                SynthesisClaim(
                    claim="Времето за реакция е до 1 час.",
                    evidence_ids=["CORP:contract-1"],
                ),
                SynthesisClaim(
                    claim="Времето за разрешаване е до 4 часа.",
                    evidence_ids=["CORP:contract-1"],
                ),
            ],
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert result.status == SemanticVerificationStatus.SUPPORTED
    assert len(llm.calls) == 1

    prompt = llm.calls[0].input["messages"][1]["content"]
    assert "FINAL ANSWER:" in prompt
    assert "Времето за реакция е до 1 час" in prompt
    assert "Времето за разрешаване е до 4 часа" in prompt
    assert "CORP:contract-1" in prompt


def test_semantic_answer_verification_rejects_response_time_mislabeling():
    from app.semantic_verification import verify_answer_semantically

    llm = _FakeLLMCapability(
        '{"status":"CONTRADICTED","reason":"The evidence says four hours is the resolution time, not the response time."}'
    )
    registry = _FakeRegistry(llm)

    result = asyncio.run(
        verify_answer_semantically(
            task=Task(
                user_request="Какъв е срокът за реакция?",
                normalized_question="Какъв е срокът за реакция?",
            ),
            answer="При критичен инцидент времето за реакция е до 4 часа.",
            claims=[
                SynthesisClaim(
                    claim="Времето за реакция е до 1 час.",
                    evidence_ids=["CORP:contract-1"],
                ),
                SynthesisClaim(
                    claim="Времето за разрешаване е до 4 часа.",
                    evidence_ids=["CORP:contract-1"],
                ),
            ],
            evidence=_evidence(),
            budget=_budget(),
            registry=registry,
        )
    )

    assert result.status == SemanticVerificationStatus.CONTRADICTED

    prompt = llm.calls[0].input["messages"][1]["content"]
    assert "FINAL ANSWER:" in prompt
    assert "времето за реакция е до 4 часа" in prompt
    assert "времето за разрешаване е до 4 часа" in prompt
