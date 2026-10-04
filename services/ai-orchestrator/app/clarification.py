from __future__ import annotations

from pydantic import BaseModel, Field

from .models import Task


class ClarificationResult(BaseModel):
    required: bool = False
    missing_context: list[str] = Field(default_factory=list)
    question: str | None = None
    reason: str | None = None


def no_clarification() -> ClarificationResult:
    return ClarificationResult()


def clarification_required(
    *,
    missing_context: list[str],
    question: str,
    reason: str,
) -> ClarificationResult:
    return ClarificationResult(
        required=True,
        missing_context=missing_context,
        question=question,
        reason=reason,
    )


def evaluate_clarification(task: Task) -> ClarificationResult:
    if not task.missing_context:
        return no_clarification()

    context = ", ".join(task.missing_context)
    return clarification_required(
        missing_context=task.missing_context,
        question=f"Моля, уточнете: {context}.",
        reason="Необходим е допълнителен контекст, за да се изпълни задачата еднозначно.",
    )
