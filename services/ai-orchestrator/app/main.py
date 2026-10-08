from fastapi import Depends, FastAPI

from .models import (
    AnswerStatus,
    EvidenceStatus,
    OrchestrationRequest,
    OrchestrationResponse,
    QuestionResolution,
)
from .orchestrator import Orchestrator
from .task import build_task
from .brain import decide
from .source_policy import configured_source_policy
from .auth import require_gateway_service
from .budgets import clamp_budget


orchestrator = Orchestrator()

app = FastAPI(
    title="Corporate AI Orchestrator",
    version="0.1.0",
)


def determine_answer_status(
    *,
    task_type,
    resolution: QuestionResolution,
    verification,
    evidence_status: EvidenceStatus,
) -> AnswerStatus:
    if task_type.value == "GENERAL" and resolution == QuestionResolution.ANSWERABLE:
        return AnswerStatus.GENERAL
    if resolution == QuestionResolution.AMBIGUOUS:
        return AnswerStatus.CLARIFICATION_REQUIRED
    if (
        resolution == QuestionResolution.CONFLICTED
        and verification.passed
        and evidence_status == EvidenceStatus.CONFLICT
    ):
        return AnswerStatus.CONFLICT
    if (
        resolution == QuestionResolution.ANSWERABLE
        and verification.passed
        and evidence_status == EvidenceStatus.SUPPORTED
    ):
        return AnswerStatus.GROUNDED
    return AnswerStatus.NO_ANSWER


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-orchestrator",
        "version": "0.1.0",
    }


@app.post("/v1/orchestrate", response_model=OrchestrationResponse)
async def orchestrate(
    request: OrchestrationRequest,
    _principal: str = Depends(require_gateway_service),
) -> OrchestrationResponse:
    policy_mode, allowed_sources = configured_source_policy()
    effective_budget = clamp_budget(request.budget)
    decision, brain_mode = await decide(
        request.user_request, allowed_sources, effective_budget, orchestrator.registry
    )
    task = build_task(
        request.user_request,
        conversation_id=request.conversation_id,
        source_policy=decision.source_policy,
        requested_freshness=request.requested_freshness,
        answer_constraints=request.output_constraints,
        budget=effective_budget,
        messages=request.messages,
    )
    task.task_type = decision.task_type

    plan = orchestrator.create_plan(
        task,
        decision if brain_mode == "brain" else None,
    )

    (
        _results,
        evaluation,
        _conflicts,
        synthesis,
        verification,
    ) = await orchestrator.execute_plan(task, plan)

    answer_status = determine_answer_status(
        task_type=task.task_type,
        resolution=synthesis.resolution,
        verification=verification,
        evidence_status=evaluation.status,
    )

    return OrchestrationResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        plan=plan,
        resolution=synthesis.resolution,
        answer=synthesis.answer,
        answer_status=answer_status,
        evidence_status=evaluation.status,
        citations=synthesis.evidence_ids,
        provenance=evaluation.applicable,
        clarification=synthesis.clarification_question,
        trace_id=str(task.task_id),
        verification=verification,
        state=task.state,
        brain_decision={**decision.model_dump(mode="json"), "execution_mode": brain_mode},
        source_policy_mode=policy_mode.value,
    )
