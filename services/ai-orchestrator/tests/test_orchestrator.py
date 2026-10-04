from app.models import (
    Plan,
    SynthesisClaim,
    SynthesisResult,
    Task,
    TaskState,
    QuestionResolution,
    VerificationResult,
)
from app.orchestrator import Orchestrator
from app.models import CapabilityType, EvidenceStatus, TaskType
from app.capabilities import CapabilityResult
from app.planner import build_plan
from app.semantic_verification import (
    SemanticVerificationResult,
    SemanticVerificationStatus,
)


async def _synthesis_with_response_time_mislabeling(
    self,
    task,
    evidence,
    budget,
):
    return SynthesisResult(
        answer="При критичен инцидент времето за реакция е до 4 часа.",
        resolution=QuestionResolution.ANSWERABLE,
        material_claims=[
            SynthesisClaim(
                claim=(
                    "При критичен инцидент времето за реакция е до 1 час, "
                    "а времето за разрешаване е до 4 часа."
                ),
                evidence_ids=["CORP:contract-1"],
            )
        ],
        evidence_ids=["CORP:contract-1"],
    )


async def _supported_claim_verification(
    **kwargs,
):
    return [
        SemanticVerificationResult(
            status=SemanticVerificationStatus.SUPPORTED,
            reason="Claim is supported by cited evidence.",
        )
    ]


async def _contradicted_answer_verification(
    **kwargs,
):
    return SemanticVerificationResult(
        status=SemanticVerificationStatus.CONTRADICTED,
        reason=(
            "The final answer assigns the 4-hour resolution time "
            "to response time."
        ),
    )


def test_execute_plan_rejects_semantically_mislabeled_final_answer(monkeypatch):
    import app.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module.Orchestrator,
        "synthesize_answer",
        _synthesis_with_response_time_mislabeling,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "verify_evidence_support",
        lambda **kwargs: VerificationResult(
            passed=True,
            material_claims_checked=1,
            reason="Evidence traceability checks passed.",
        ),
    )

    monkeypatch.setattr(
        orchestrator_module,
        "verify_claims_semantically",
        _supported_claim_verification,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "verify_answer_semantically",
        _contradicted_answer_verification,
    )

    task = Task(
        user_request="Какви са изискванията за времето за реакция при критични инциденти?"
    )

    plan = Plan(
        task_id=task.task_id,
        steps=[],
    )

    results = __import__("asyncio").run(
        Orchestrator().execute_plan(task, plan)
    )

    _, _, _, synthesis, verification = results

    assert synthesis.resolution == QuestionResolution.ANSWERABLE
    assert task.state == TaskState.NO_ANSWER
    assert verification.passed is False
    assert any(
        "Final answer semantic verification" in error
        for error in verification.semantic_errors
    )


def test_general_task_runs_as_unverified_controlled_response():
    class GeneralCapability:
        async def execute(self, request):
            return CapabilityResult(
                capability=CapabilityType.LLM_REASONING,
                success=True,
                data={"content": "Фотосинтезата преобразува светлина в химична енергия."},
            )

    class Registry:
        def get(self, _capability):
            return GeneralCapability()

    task = Task(
        user_request="Обясни фотосинтезата",
        task_type=TaskType.GENERAL,
    )
    plan = build_plan(task)
    result = __import__("asyncio").run(Orchestrator(Registry()).execute_plan(task, plan))
    _, evaluation, _, synthesis, verification = result
    assert synthesis.answer.startswith("Фотосинтезата")
    assert evaluation.status == EvidenceStatus.NOT_REQUIRED
    assert verification.passed is False
    assert verification.reason == "GENERAL_RESPONSE_IS_NOT_CORPORATE_EVIDENCE_VERIFIED"


def test_insufficient_corporate_evidence_replans_to_bounded_web_fetch(monkeypatch):
    import app.orchestrator as orchestrator_module
    from app.evidence_evaluation import EvidenceEvaluationResult
    from app.models import Budget, EvidenceStatus, SourceClass
    from app.planner import build_plan
    from app.web_research import WebFetchSelection

    class Capability:
        def __init__(self, capability):
            self.capability = capability

        async def execute(self, request):
            if self.capability == CapabilityType.CORPORATE_RETRIEVAL:
                return CapabilityResult(capability=self.capability, success=True, data={"results": []})
            if self.capability == CapabilityType.WEB_SEARCH:
                return CapabilityResult(capability=self.capability, success=True, data={"evidence": [{
                    "url": "https://official.example/prices",
                    "content": "Official price page snippet",
                }]})
            return CapabilityResult(capability=self.capability, success=True, data={"evidence": [{
                "url": "https://official.example/prices",
                "content": "Official service X price is 100 EUR.",
                "fetched_at": "2026-10-04T00:00:00+00:00",
            }]})

    class Registry:
        def get(self, capability):
            return Capability(capability)

    synthesis_rounds = []

    async def synthesize(self, task, evidence, budget):
        synthesis_rounds.append(list(evidence))
        if len(synthesis_rounds) == 1:
            return SynthesisResult(answer="", resolution=QuestionResolution.INSUFFICIENT)
        return SynthesisResult(answer="Verified public information.", resolution=QuestionResolution.ANSWERABLE)

    async def select(self, *args, **kwargs):
        return WebFetchSelection(evidence_ids=["WEB:https://official.example/prices"])

    monkeypatch.setattr(Orchestrator, "synthesize_answer", synthesize)
    monkeypatch.setattr(Orchestrator, "select_web_fetch_candidates", select)
    monkeypatch.setattr(orchestrator_module, "evaluate_evidence", lambda evidence: EvidenceEvaluationResult(
        status=EvidenceStatus.SUPPORTED, applicable=evidence,
    ))
    monkeypatch.setattr(orchestrator_module, "verify_evidence_support", lambda **kwargs: VerificationResult(passed=True))
    monkeypatch.setattr(orchestrator_module, "verify_claims_semantically", lambda **kwargs: __import__("asyncio").sleep(0, result=[]))
    monkeypatch.setattr(orchestrator_module, "verify_answer_semantically", lambda **kwargs: __import__("asyncio").sleep(0, result=SemanticVerificationResult(
        status=SemanticVerificationStatus.SUPPORTED, reason="supported",
    )))

    task = Task(
        user_request="Каква е цената?",
        normalized_question="Каква е цената?",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        allowed_source_classes=[SourceClass.CORPORATE, SourceClass.WEB],
        budget=Budget(max_steps=6, max_web_searches=1, max_web_fetches=1),
    )
    result = __import__("asyncio").run(Orchestrator(Registry()).execute_plan(task, build_plan(task)))
    results, _, _, synthesis, verification = result
    assert synthesis.answer == "Verified public information."
    assert verification.passed is True
    assert sum(item.capability == CapabilityType.WEB_SEARCH for item in results) == 1
    assert sum(item.capability == CapabilityType.WEB_FETCH for item in results) == 1
    assert len(synthesis_rounds) == 2


def test_invalid_web_fetch_selection_fails_closed_without_crashing(monkeypatch):
    import asyncio
    import app.orchestrator as module
    from app.budgets import BudgetExceeded
    from app.evidence_evaluation import EvidenceEvaluationResult
    from app.models import Budget, EvidenceStatus, SourceClass

    class Capability:
        async def execute(self, request):
            if request.capability == CapabilityType.CORPORATE_RETRIEVAL:
                return CapabilityResult(capability=request.capability, success=True, data={"results": []})
            if request.capability == CapabilityType.WEB_SEARCH:
                return CapabilityResult(capability=request.capability, success=True, data={"evidence": [{
                    "url": "https://example.test/search-result", "content": "Unverified search snippet"
                }]})
            raise AssertionError("invalid selector output must not authorize a fetch")

    class Registry:
        def get(self, _capability):
            return Capability()

    async def invalid_selection(*_args, **_kwargs):
        raise ValueError("invalid JSON")

    async def insufficient(*_args, **_kwargs):
        return SynthesisResult(answer="", resolution=QuestionResolution.INSUFFICIENT)

    async def no_refinement(*_args, **_kwargs):
        raise BudgetExceeded("retrieval refinement disabled in test")

    monkeypatch.setattr(Orchestrator, "select_web_fetch_candidates", invalid_selection)
    monkeypatch.setattr(Orchestrator, "synthesize_answer", insufficient)
    monkeypatch.setattr(Orchestrator, "refine_retrieval_query", no_refinement)
    monkeypatch.setattr(module, "evaluate_evidence", lambda evidence: EvidenceEvaluationResult(
        status=EvidenceStatus.INSUFFICIENT_EVIDENCE, unknown=evidence
    ))
    task = Task(
        user_request="Compare contract and current public prices",
        normalized_question="Compare contract and current public prices",
        task_type=TaskType.CORPORATE_AND_WEB,
        allowed_source_classes=[SourceClass.CORPORATE, SourceClass.WEB],
        budget=Budget(max_retrieval_rounds=1, max_web_searches=1, max_web_fetches=1),
    )
    result = asyncio.run(Orchestrator(Registry()).execute_plan(task, build_plan(task)))
    results, _evaluation, _conflicts, synthesis, _verification = result
    assert synthesis.resolution == QuestionResolution.INSUFFICIENT
    assert any(item.capability == CapabilityType.WEB_SEARCH for item in results)
    assert not any(item.capability == CapabilityType.WEB_FETCH for item in results)


def test_corporate_and_web_answer_requires_applicable_evidence_from_both(monkeypatch):
    import asyncio
    from app.budgets import BudgetExceeded
    from app.models import Budget, SourceClass

    class Registry:
        def get(self, capability):
            class Stub:
                async def execute(self, request):
                    if request.capability == CapabilityType.CORPORATE_RETRIEVAL:
                        return CapabilityResult(capability=request.capability, success=True, data={
                            "results": [{"evidence_id": "CORP:contract", "source_id": "contract-1",
                                         "claim": "Contract price is 100 EUR", "version": 1}]
                        })
                    if request.capability == CapabilityType.WEB_SEARCH:
                        return CapabilityResult(capability=request.capability, success=True, data={"evidence": []})
                    raise AssertionError("no other capability expected")
            return Stub()

    async def synthesize(_self, _task, _evidence, _budget):
        return SynthesisResult(
            answer="Current price is 100 EUR.",
            resolution=QuestionResolution.ANSWERABLE,
            material_claims=[SynthesisClaim(claim="Current price is 100 EUR.", evidence_ids=["CORP:contract"])],
            evidence_ids=["CORP:contract"],
        )

    async def stop_refinement(*_args, **_kwargs):
        raise BudgetExceeded("test budget exhausted")

    monkeypatch.setattr(Orchestrator, "synthesize_answer", synthesize)
    monkeypatch.setattr(Orchestrator, "refine_retrieval_query", stop_refinement)
    task = Task(
        user_request="Current public price under contract",
        normalized_question="Current public price under contract",
        task_type=TaskType.CORPORATE_AND_WEB,
        allowed_source_classes=[SourceClass.CORPORATE, SourceClass.WEB],
        budget=Budget(max_retrieval_rounds=1, max_web_searches=1),
    )
    results, evaluation, _conflicts, synthesis, verification = asyncio.run(
        Orchestrator(Registry()).execute_plan(task, build_plan(task))
    )
    assert any(item.capability == CapabilityType.CORPORATE_RETRIEVAL for item in results)
    assert any(item.capability == CapabilityType.WEB_SEARCH for item in results)
    assert synthesis.resolution == QuestionResolution.INSUFFICIENT
    assert synthesis.answer == ""
    assert evaluation.status == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert verification.passed is False
    assert "REQUIRED_SOURCE_CLASS_MISSING:WEB" in verification.conflict_errors
