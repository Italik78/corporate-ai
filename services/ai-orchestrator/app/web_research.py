from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from .models import EvidenceRecord, Task


class WebFetchSelection(BaseModel):
    evidence_ids: list[str] = []
    reason: str | None = None


_SYSTEM_PROMPT = """Ти си модул за избор на web източници за допълнително извличане.

Целта ти е само да избереш кои вече намерени web доказателства трябва
да бъдат извлечени в пълен вид.

Правила:
- Избирай САМО evidence_id, които присъстват в подадените доказателства.
- Никога не измисляй URL или evidence_id.
- Не отговаряй на потребителския въпрос.
- Не избирай произволно източници само заради ranking score.
- Предпочитай първични, официални или авторитетни източници, когато това
  е релевантно към въпроса.
- Ако наличното съдържание е достатъчно, върни празен списък.
- Върни само кратък reason.

Върни САМО валиден JSON object:
{
  "evidence_ids": ["string"],
  "reason": "кратко обяснение"
}
"""


class _StructuredWebFetchSelection(BaseModel):
    evidence_ids: list[str] = []
    reason: str | None = None


def build_web_fetch_selection_messages(
    task: Task,
    evidence: list[EvidenceRecord],
) -> list[dict[str, str]]:
    evidence_context = "\n\n".join(
        (
            f"EXACT_EVIDENCE_ID: {item.evidence_id}\n"
            f"source_class: {item.source_class.value}\n"
            f"source_id: {item.source_id}\n"
            f"location: {item.source_location or 'unknown'}\n"
            f"authority: {item.authority or 'unknown'}\n"
            f"freshness: {item.freshness or 'unknown'}\n"
            f"claim:\n{item.claim}"
        )
        for item in evidence
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Въпрос:\n"
                f"{task.normalized_question or task.user_request}\n\n"
                f"Налични web доказателства:\n"
                f"{evidence_context or '[NO_EVIDENCE]'}"
            ),
        },
    ]


def parse_web_fetch_selection(
    answer: str,
    evidence: list[EvidenceRecord],
    max_selections: int | None = None,
) -> WebFetchSelection:
    try:
        payload = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise ValueError("Web fetch selection returned invalid JSON") from exc

    try:
        result = _StructuredWebFetchSelection.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid web fetch selection payload") from exc

    evidence_by_id = {item.evidence_id: item for item in evidence}

    for evidence_id in result.evidence_ids:
        item = evidence_by_id.get(evidence_id)

        if item is None:
            raise ValueError(
                f"Unknown evidence_id selected for web fetch: {evidence_id}"
            )

        if item.source_class.value != "WEB":
            raise ValueError(
                f"Non-WEB evidence selected for web fetch: {evidence_id}"
            )

        if not item.source_location:
            raise ValueError(
                f"WEB evidence has no fetchable location: {evidence_id}"
            )

    if max_selections is not None and len(result.evidence_ids) > max_selections:
        raise ValueError(
            f"Maximum web fetch selections exceeded: {max_selections}"
        )

    return WebFetchSelection(
        evidence_ids=result.evidence_ids,
        reason=result.reason,
    )
