from __future__ import annotations

from .retrieval_strategy import RetrievalStrategy
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


def build_plan(task: Task) -> Plan:
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
            depends_on = (
                ["corporate-retrieval-1"] if steps else []
            )
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

    return Plan(
        task_id=task.task_id,
        steps=steps,
        max_steps=task.budget.max_steps,
    )
