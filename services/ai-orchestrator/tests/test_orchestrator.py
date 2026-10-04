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
