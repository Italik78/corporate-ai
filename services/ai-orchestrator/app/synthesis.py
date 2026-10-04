from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

from .models import EvidenceRecord, QuestionResolution, SynthesisClaim, SynthesisResult, Task


_SYSTEM_PROMPT = """Ти си корпоративен AI асистент.
Отговаряй на български.

Използвай само предоставените доказателства за фактически твърдения.
Не измисляй липсващи факти, документи, срокове или условия.
Не приемай различни документи или различни стойности за конфликт без доказан общ контекст.

Върни САМО валиден JSON object, без markdown и без допълнителен текст.

Задължителна структура:
{
  "answer": "string",
  "material_claims": [
    {
      "claim": "string",
      "evidence_ids": ["string"]
    }
  ],
  "resolution": "ANSWERABLE",
  "needs_clarification": false,
  "clarification_question": null,
  "uncertainty": null
}

Правила за material_claims:
- Всеки съществен фактически claim трябва да има поне един evidence_id.
- Използвай само ТОЧНИТЕ стойности от полето EXACT_EVIDENCE_ID.
- Никога не използвай source_id, document_id или друг идентификатор като evidence_id.
- Не измисляй и не съкращавай evidence_id.
- Избери resolution само от: ANSWERABLE, AMBIGUOUS, INSUFFICIENT, CONFLICTED.
- Използвай AMBIGUOUS, когато доказателствата съдържат няколко различни приложими обекта/контекста и въпросът не определя кой е релевантен.
- Използвай INSUFFICIENT, когато няма достатъчно доказателства за надежден отговор.
- Използвай CONFLICTED само когато има действителен конфликт за един и същ обект и контекст.
- Използвай ANSWERABLE, когато въпросът може да бъде надеждно отговорен от предоставените доказателства.
- При AMBIGUOUS използвай needs_clarification=true и попълни clarification_question.
- При INSUFFICIENT или CONFLICTED не измисляй липсваща информация.
- Не превръщай различни документи, договори, версии или контексти автоматично в конфликт.
- Ако въпросът се отнася до един конкретен обект, но доказателствата съдържат няколко различни обекта с различни релевантни стойности, използвай needs_clarification=true.
- Не избирай произволно един от различните обекти само защото има по-висок retrieval score.
"""


class StructuredSynthesisPayload(BaseModel):
    answer: str
    resolution: QuestionResolution = QuestionResolution.ANSWERABLE
    material_claims: list[SynthesisClaim] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    uncertainty: str | None = None


def build_synthesis_messages(task: Task, evidence: list[EvidenceRecord]) -> list[dict[str, str]]:
    evidence_context = "\n\n".join(
        (
            f"EXACT_EVIDENCE_ID: {item.evidence_id}\n"
            f"source_class: {item.source_class.value}\n"
            f"source_id (metadata only, NEVER use as evidence_id): {item.source_id}\n"
            f"location: {item.source_location or 'unknown'}\n"
            f"authority: {item.authority or 'unknown'}\n"
            f"freshness: {item.freshness or 'unknown'}\n"
            f"version: {item.version if item.version is not None else 'unknown'}\n"
            f"claim:\n{item.claim}"
        )
        for item in evidence
    )

    user_prompt = (
        f"Въпрос:\n{task.normalized_question or task.user_request}\n\n"
        "Доказателства:\n"
        f"{evidence_context or '[NO_EVIDENCE]'}\n\n"
        "Дай структуриран отговор според доказателствата."
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def parse_synthesis_result(
    *,
    answer: str,
    evidence: list[EvidenceRecord],
) -> SynthesisResult:
    try:
        payload = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM synthesis returned invalid JSON: {exc}") from exc

    try:
        structured = StructuredSynthesisPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"LLM synthesis JSON does not match schema: {exc}") from exc

    valid_ids = {item.evidence_id for item in evidence}
    invalid_references: list[str] = []

    for material_claim in structured.material_claims:
        for evidence_id in material_claim.evidence_ids:
            if evidence_id not in valid_ids:
                invalid_references.append(evidence_id)

    if invalid_references:
        raise ValueError(
            "LLM synthesis referenced unknown evidence_id(s): "
            + ", ".join(dict.fromkeys(invalid_references))
        )

    if structured.resolution == QuestionResolution.AMBIGUOUS:
        if not structured.needs_clarification:
            raise ValueError(
                "AMBIGUOUS synthesis must set needs_clarification=true"
            )
        if not structured.clarification_question:
            raise ValueError(
                "AMBIGUOUS synthesis requires clarification_question"
            )
    elif structured.needs_clarification:
        raise ValueError(
            "needs_clarification=true is only valid with resolution=AMBIGUOUS"
        )

    if structured.resolution in (
        QuestionResolution.ANSWERABLE,
        QuestionResolution.CONFLICTED,
    ):
        flattened_ids = list(
            dict.fromkeys(
                evidence_id
                for material_claim in structured.material_claims
                for evidence_id in material_claim.evidence_ids
            )
        )
    else:
        flattened_ids = []

    return SynthesisResult(
        answer=structured.answer,
        resolution=structured.resolution,
        material_claims=structured.material_claims,
        evidence_ids=flattened_ids,
        needs_clarification=structured.needs_clarification,
        clarification_question=structured.clarification_question,
        uncertainty=structured.uncertainty,
    )
