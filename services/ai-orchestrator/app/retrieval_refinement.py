from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

from .models import EvidenceRecord, Task


class RetrievalRefinementResult(BaseModel):
    query: str | None = None
    reason: str | None = None


_SYSTEM_PROMPT = """Ти си модул за refinement на корпоративно търсене.

Целта ти е само да подобриш search query за следващ retrieval round.

Правила:
- Не измисляй факти.
- Не отговаряй на потребителския въпрос.
- Не избирай произволно документ, договор, версия или обект.
- Запази смисъла и ограниченията на оригиналния въпрос.
- Върни само един кратък query или null.
- Ако наличните доказателства показват, че проблемът е двусмислие между различни
  обекти/договори/контексти, върни null.
- Ако няма разумна нова формулировка, върни null.

Върни САМО валиден JSON object:
{
  "query": "string или null",
  "reason": "кратко обяснение"
}
"""


class _StructuredRefinementPayload(BaseModel):
    query: str | None = None
    reason: str | None = None


def build_refinement_messages(
    task: Task,
    evidence: list[EvidenceRecord],
) -> list[dict[str, str]]:
    evidence_context = "\n\n".join(
        (
            f"evidence_id: {item.evidence_id}\n"
            f"source_id: {item.source_id}\n"
            f"version: {item.version if item.version is not None else 'unknown'}\n"
            f"claim:\n{item.claim}"
        )
        for item in evidence
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Оригинален въпрос:\n"
                f"{task.normalized_question or task.user_request}\n\n"
                f"Налични доказателства:\n"
                f"{evidence_context or '[NO_EVIDENCE]'}"
            ),
        },
    ]


def parse_refinement_result(answer: str) -> RetrievalRefinementResult:
    try:
        payload = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise ValueError("Retrieval refinement returned invalid JSON") from exc

    try:
        result = _StructuredRefinementPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid retrieval refinement payload") from exc

    if result.query is not None:
        result.query = result.query.strip()
        if not result.query or result.query.lower() == "null":
            result.query = None

    return RetrievalRefinementResult(
        query=result.query,
        reason=result.reason,
    )
