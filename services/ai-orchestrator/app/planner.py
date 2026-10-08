from __future__ import annotations

from .retrieval_strategy import RetrievalStrategy
from .brain import BrainDecision
from .models import (
    CapabilityType,
    Plan,
    PlanStep,
    SourceClass,
    Task,
    TaskType,
)


def build_corporate_retrieval_input(query: str) -> dict[str, object]:
    strategy = RetrievalStrategy()
    return {
        "query": query,
        "candidate_limit": strategy.candidate_limit,
        "max_documents": strategy.max_documents,
        "max_chunks_per_document": strategy.max_chunks_per_document,
        "score_threshold": strategy.score_threshold,
    }


def build_plan(
    task: Task,
    brain_decision: BrainDecision | None = None,
) -> Plan:
    if brain_decision is not None:
        steps: list[PlanStep] = []

        type_by_capability = {
            CapabilityType.CORPORATE_RETRIEVAL: "RETRIEVE_CORPORATE_EVIDENCE",
            CapabilityType.STRUCTURED_QUERY: "STRUCTURED_DOCUMENT_QUERY",
            CapabilityType.WEB_SEARCH: "SEARCH_WEB",
            CapabilityType.WEB_FETCH: "FETCH_WEB_SELECTED",
            CapabilityType.GENERAL_RESPONSE: "GENERAL_RESPONSE",
        }

        for brain_step in brain_decision.plan:
            step_type = type_by_capability.get(brain_step.capability)
            if step_type is None:
                raise ValueError(
                    f"unsupported Brain capability in Planner: "
                    f"{brain_step.capability}"
                )

            steps.append(
                PlanStep(
                    step_id=brain_step.step_id,
                    type=step_type,
                    capability=brain_step.capability,
                    input=dict(brain_step.input),
                    depends_on=list(brain_step.depends_on),
                    evidence_required=brain_step.capability
                    in {
                        CapabilityType.CORPORATE_RETRIEVAL,
                        CapabilityType.STRUCTURED_QUERY,
                        CapabilityType.WEB_SEARCH,
                        CapabilityType.WEB_FETCH,
                    },
                )
            )

        return Plan(
            task_id=task.task_id,
            steps=steps,
            max_steps=task.budget.max_steps,
        )

    steps: list[PlanStep] = []

    if task.task_type == TaskType.CORPORATE_KNOWLEDGE:
        if SourceClass.CORPORATE in task.allowed_source_classes:
            steps.append(
                PlanStep(
                    step_id="corporate-retrieval-1",
                    type="RETRIEVE_CORPORATE_EVIDENCE",
                    capability=CapabilityType.CORPORATE_RETRIEVAL,
                    input=build_corporate_retrieval_input(task.normalized_question),
                    evidence_required=True,
                )
            )

    elif task.task_type == TaskType.WEB_RESEARCH:
        if SourceClass.WEB in task.allowed_source_classes:
            steps.append(
                PlanStep(
                    step_id="web-search-1",
                    type="SEARCH_WEB",
                    capability=CapabilityType.WEB_SEARCH,
                    input={"query": task.normalized_question},
                    evidence_required=True,
                )
            )

    elif task.task_type == TaskType.CORPORATE_AND_WEB:
        if SourceClass.CORPORATE in task.allowed_source_classes:
            steps.append(
                PlanStep(
                    step_id="corporate-retrieval-1",
                    type="RETRIEVE_CORPORATE_EVIDENCE",
                    capability=CapabilityType.CORPORATE_RETRIEVAL,
                    input=build_corporate_retrieval_input(task.normalized_question),
                    evidence_required=True,
                )
            )
        if SourceClass.WEB in task.allowed_source_classes:
            depends_on = ["corporate-retrieval-1"] if steps else []
            steps.append(
                PlanStep(
                    step_id="web-search-1",
                    type="SEARCH_WEB",
                    capability=CapabilityType.WEB_SEARCH,
                    input={"query": task.normalized_question},
                    depends_on=depends_on,
                    evidence_required=True,
                )
            )

    elif task.task_type == TaskType.GENERAL:
        steps.append(
            PlanStep(
                step_id="general-response-1",
                type="GENERAL_RESPONSE",
                capability=CapabilityType.GENERAL_RESPONSE,
                input={"query": task.normalized_question},
                evidence_required=False,
            )
        )

    return Plan(
        task_id=task.task_id,
        steps=steps,
        max_steps=task.budget.max_steps,
    )
