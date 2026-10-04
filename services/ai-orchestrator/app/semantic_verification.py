from __future__ import annotations

import json
from enum import Enum

from .budgets import BudgetController
from .capabilities import CapabilityRequest
from .models import CapabilityType, EvidenceRecord, SynthesisClaim, Task


class SemanticVerificationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"


class SemanticVerificationResult:
    def __init__(
        self,
        *,
        status: SemanticVerificationStatus,
        reason: str,
    ) -> None:
        self.status = status
        self.reason = reason


def build_semantic_verification_messages(
    task: Task,
    claim: SynthesisClaim,
    evidence: list[EvidenceRecord],
) -> list[dict[str, str]]:
    cited_ids = set(claim.evidence_ids)
    evidence_blocks = []

    for item in evidence:
        if item.evidence_id not in cited_ids:
            continue

        evidence_blocks.append(
            "\n".join(
                [
                    f"EXACT_EVIDENCE_ID: {item.evidence_id}",
                    f"source_class: {item.source_class.value}",
                    f"source_id: {item.source_id}",
                    f"source_location: {item.source_location or ''}",
                    f"authority: {item.authority or ''}",
                    f"version: {item.version or ''}",
                    f"freshness: {item.freshness or ''}",
                    f"claim: {item.claim}",
                ]
            )
        )

    context = "\n\n".join(evidence_blocks)

    system_prompt = """Ти си строг semantic evidence verifier за корпоративен AI.

Провери дали конкретният CLAIM е логически подкрепен от предоставеното EVIDENCE.

Не използвай външни знания.
Не приемай, че сходни думи означават еднакъв факт.
Разграничавай:
- време за реакция от време за разрешаване;
- различни обекти, договори, услуги и системи;
- различни версии;
- различни условия и обхвати;
- общо твърдение от твърдение с конкретно условие.

Върни САМО валиден JSON object:

{
  "status": "SUPPORTED",
  "reason": "string"
}

status може да бъде само:
- SUPPORTED — evidence директно и достатъчно подкрепя claim-а;
- CONTRADICTED — evidence съдържа факт, който противоречи на claim-а;
- INSUFFICIENT — evidence не е достатъчно, за да се потвърди или опровергае claim-а.

При неяснота използвай INSUFFICIENT.
Не избирай по-висок retrieval score.
Не добавяй нови факти.
"""

    user_prompt = "\n".join(
        [
            f"QUESTION: {task.normalized_question or task.user_request}",
            "",
            f"CLAIM: {claim.claim}",
            "",
            "EVIDENCE:",
            context,
        ]
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def parse_semantic_verification_result(
    content: str,
) -> SemanticVerificationResult:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Semantic verification returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Semantic verification result must be a JSON object")

    status = data.get("status")
    reason = data.get("reason")

    if status not in {
        SemanticVerificationStatus.SUPPORTED.value,
        SemanticVerificationStatus.CONTRADICTED.value,
        SemanticVerificationStatus.INSUFFICIENT.value,
    }:
        raise ValueError("Semantic verification returned invalid status")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Semantic verification reason is required")

    return SemanticVerificationResult(
        status=SemanticVerificationStatus(status),
        reason=reason.strip(),
    )


async def verify_claim_semantically(
    *,
    task: Task,
    claim: SynthesisClaim,
    evidence: list[EvidenceRecord],
    budget: BudgetController,
    registry,
) -> SemanticVerificationResult:
    evidence_by_id = {
        item.evidence_id: item
        for item in evidence
    }

    selected_evidence = [
        evidence_by_id[evidence_id]
        for evidence_id in claim.evidence_ids
        if evidence_id in evidence_by_id
    ]

    if not selected_evidence:
        return SemanticVerificationResult(
            status=SemanticVerificationStatus.INSUFFICIENT,
            reason="Claim has no valid cited evidence.",
        )

    budget.consume_verification_round()
    budget.consume_capability_call()

    result = await registry.get(
        CapabilityType.LLM_REASONING
    ).execute(
        CapabilityRequest(
            capability=CapabilityType.LLM_REASONING,
            input={
                "messages": build_semantic_verification_messages(
                    task,
                    claim,
                    selected_evidence,
                ),
                "temperature": 0.0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
        )
    )

    if not result.success:
        raise RuntimeError(
            result.error or "Semantic verification failed"
        )

    content = result.data.get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Semantic verification returned empty content"
        )

    return parse_semantic_verification_result(content)


async def verify_claims_semantically(
    *,
    task: Task,
    claims: list[SynthesisClaim],
    evidence: list[EvidenceRecord],
    budget: BudgetController,
    registry,
) -> list[SemanticVerificationResult]:
    evidence_by_id = {
        item.evidence_id: item
        for item in evidence
    }

    valid_claims: list[tuple[int, SynthesisClaim, list[EvidenceRecord]]] = []

    for index, claim in enumerate(claims):
        selected_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        ]

        if not selected_evidence:
            continue

        valid_claims.append((index, claim, selected_evidence))

    if not valid_claims:
        return [
            SemanticVerificationResult(
                status=SemanticVerificationStatus.INSUFFICIENT,
                reason="Claim has no valid cited evidence.",
            )
            for _ in claims
        ]

    evidence_blocks: list[str] = []

    for index, claim, selected_evidence in valid_claims:
        claim_evidence = []

        for item in selected_evidence:
            claim_evidence.append(
                "\n".join(
                    [
                        f"EXACT_EVIDENCE_ID: {item.evidence_id}",
                        f"source_class: {item.source_class.value}",
                        f"source_id: {item.source_id}",
                        f"source_location: {item.source_location or ''}",
                        f"authority: {item.authority or ''}",
                        f"version: {item.version or ''}",
                        f"freshness: {item.freshness or ''}",
                        f"claim: {item.claim}",
                    ]
                )
            )

        evidence_blocks.append(
            "\n".join(
                [
                    f"CLAIM_INDEX: {index}",
                    f"CLAIM: {claim.claim}",
                    "CITED_EVIDENCE:",
                    "\n\n".join(claim_evidence),
                ]
            )
        )

    system_prompt = """Ти си строг semantic evidence verifier за корпоративен AI.

Провери всеки CLAIM само срещу неговото CITED_EVIDENCE.

Не използвай външни знания.
Не използвай evidence от друг CLAIM.
Не приемай сходни думи за доказателство за еднакъв факт.
Разграничавай:
- време за реакция от време за разрешаване;
- различни обекти, договори, услуги и системи;
- различни версии;
- различни условия и обхвати;
- общо твърдение от твърдение с конкретно условие.

За всеки CLAIM върни точно един резултат.

Върни САМО валиден JSON object:

{
  "results": [
    {
      "claim_index": 0,
      "status": "SUPPORTED",
      "reason": "string"
    }
  ]
}

status може да бъде само:
- SUPPORTED — cited evidence директно и достатъчно подкрепя claim-а;
- CONTRADICTED — cited evidence съдържа факт, който противоречи на claim-а;
- INSUFFICIENT — cited evidence не е достатъчно, за да се потвърди или опровергае claim-а.

При неяснота използвай INSUFFICIENT.
Не избирай по-висок retrieval score.
Не добавяй нови факти.
Не променяй claim-а.
Не измисляй claim_index.
"""

    user_prompt = "\n".join(
        [
            f"QUESTION: {task.normalized_question or task.user_request}",
            "",
            "\n\n".join(evidence_blocks),
        ]
    )

    budget.consume_verification_round()
    budget.consume_capability_call()

    result = await registry.get(
        CapabilityType.LLM_REASONING
    ).execute(
        CapabilityRequest(
            capability=CapabilityType.LLM_REASONING,
            input={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": max(300, len(valid_claims) * 180),
                "response_format": {"type": "json_object"},
            },
        )
    )

    if not result.success:
        raise RuntimeError(
            result.error or "Semantic verification failed"
        )

    content = result.data.get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Semantic verification returned empty content"
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Semantic verification returned invalid JSON"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Semantic verification result must be a JSON object"
        )

    raw_results = data.get("results")

    if not isinstance(raw_results, list):
        raise ValueError(
            "Semantic verification results must be a list"
        )

    parsed: dict[int, SemanticVerificationResult] = {}

    for item in raw_results:
        if not isinstance(item, dict):
            raise ValueError(
                "Semantic verification result item must be an object"
            )

        claim_index = item.get("claim_index")
        status = item.get("status")
        reason = item.get("reason")

        if not isinstance(claim_index, int):
            raise ValueError(
                "Semantic verification claim_index must be an integer"
            )

        if claim_index < 0 or claim_index >= len(claims):
            raise ValueError(
                "Semantic verification returned unknown claim_index"
            )

        if claim_index in parsed:
            raise ValueError(
                "Semantic verification returned duplicate claim_index"
            )

        if status not in {
            SemanticVerificationStatus.SUPPORTED.value,
            SemanticVerificationStatus.CONTRADICTED.value,
            SemanticVerificationStatus.INSUFFICIENT.value,
        }:
            raise ValueError(
                "Semantic verification returned invalid status"
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "Semantic verification reason is required"
            )

        parsed[claim_index] = SemanticVerificationResult(
            status=SemanticVerificationStatus(status),
            reason=reason.strip(),
        )

    results: list[SemanticVerificationResult] = []

    for index in range(len(claims)):
        item = parsed.get(index)

        if item is None:
            results.append(
                SemanticVerificationResult(
                    status=SemanticVerificationStatus.INSUFFICIENT,
                    reason="Semantic verifier did not return a result for this claim.",
                )
            )
        else:
            results.append(item)

    return results

async def verify_answer_semantically(
    *,
    task: Task,
    answer: str,
    claims: list[SynthesisClaim],
    evidence: list[EvidenceRecord],
    budget: BudgetController,
    registry,
) -> SemanticVerificationResult:
    evidence_by_id = {
        item.evidence_id: item
        for item in evidence
    }

    claim_blocks: list[str] = []

    for index, claim in enumerate(claims):
        selected_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        ]

        if not selected_evidence:
            claim_blocks.append(
                "\n".join(
                    [
                        f"CLAIM_INDEX: {index}",
                        f"CLAIM: {claim.claim}",
                        "CITED_EVIDENCE: [NO_VALID_EVIDENCE]",
                    ]
                )
            )
            continue

        evidence_blocks = []

        for item in selected_evidence:
            evidence_blocks.append(
                "\n".join(
                    [
                        f"EXACT_EVIDENCE_ID: {item.evidence_id}",
                        f"source_class: {item.source_class.value}",
                        f"source_id: {item.source_id}",
                        f"source_location: {item.source_location or ''}",
                        f"authority: {item.authority or ''}",
                        f"version: {item.version or ''}",
                        f"freshness: {item.freshness or ''}",
                        f"claim: {item.claim}",
                    ]
                )
            )

        claim_blocks.append(
            "\n".join(
                [
                    f"CLAIM_INDEX: {index}",
                    f"CLAIM: {claim.claim}",
                    "CITED_EVIDENCE:",
                    "\n\n".join(evidence_blocks),
                ]
            )
        )

    system_prompt = """Ти си строг semantic answer verifier за корпоративен AI.

Провери дали FINAL ANSWER е семантично faithful към предоставените MATERIAL CLAIMS и техните CITED_EVIDENCE.

FINAL ANSWER е това, което потребителят ще получи. Не го пренаписвай.

Провери особено строго:
- числови стойности;
- единици;
- срокове и времеви интервали;
- вида на метриката или действието;
- условия и ограничения;
- обхват;
- конкретен обект, договор, услуга или система;
- разлика между response/reaction time и resolution/fix time;
- разлика между "до X" и "X";
- дали answer приписва на един факт характеристика, която evidence дава на друг факт.

Не използвай външни знания.
Не добавяй липсващи факти.
Не приемай семантична близост за еквивалентност.
Не приемай, че наличието на една и съща числова стойност означава, че твърдението е вярно.
Не използвай evidence от несвързан claim.
Не проверявай дали отговорът е стилистично добър; проверявай неговата фактическа вярност спрямо claims и evidence.

Върни САМО валиден JSON object:

{
  "status": "SUPPORTED",
  "reason": "string"
}

status може да бъде само:
- SUPPORTED — всички съществени фактически твърдения във FINAL ANSWER са точно подкрепени от MATERIAL CLAIMS и тяхното evidence;
- CONTRADICTED — FINAL ANSWER съдържа съществено твърдение, което противоречи на MATERIAL CLAIMS или CITED_EVIDENCE;
- INSUFFICIENT — FINAL ANSWER съдържа съществено твърдение, което не може надеждно да бъде проверено от предоставените claims и evidence.

При всяка неяснота използвай INSUFFICIENT.
Ако дори една съществена фактическа част от FINAL ANSWER променя смисъла на claim/evidence, не използвай SUPPORTED.
"""

    user_prompt = "\n".join(
        [
            f"QUESTION: {task.normalized_question or task.user_request}",
            "",
            "FINAL ANSWER:",
            answer,
            "",
            "MATERIAL CLAIMS AND THEIR CITED EVIDENCE:",
            "\n\n".join(claim_blocks) or "[NO_CLAIMS]",
        ]
    )

    budget.consume_verification_round()
    budget.consume_capability_call()

    result = await registry.get(
        CapabilityType.LLM_REASONING
    ).execute(
        CapabilityRequest(
            capability=CapabilityType.LLM_REASONING,
            input={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
        )
    )

    if not result.success:
        raise RuntimeError(
            result.error or "Semantic answer verification failed"
        )

    content = result.data.get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Semantic answer verification returned empty content"
        )

    return parse_semantic_verification_result(content)
