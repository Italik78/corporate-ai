from __future__ import annotations

import os
from typing import Any

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType
from .retrieval_strategy import RetrievalStrategy, diversify_candidates


class CorporateRetrievalCapability(Capability):
    capability_type = CapabilityType.CORPORATE_RETRIEVAL

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "KNOWLEDGE_ENGINE_URL",
                "http://corporate-ai-knowledge-engine-0.3.1-test:8090",
            )
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("TIMEOUT_SECONDS", "120")
        )

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        query = request.input.get("query")
        if not isinstance(query, str) or not query.strip():
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="query is required",
            )

        payload: dict[str, Any] = {
            "query": query.strip(),
            "top_k": min(
                int(request.input.get("candidate_limit", 5)),
                20,
            ),
            "score_threshold": request.input.get("score_threshold", 0.45),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"corporate retrieval failed: {exc}",
            )

        results = data.get("results")
        if not isinstance(results, list):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid knowledge engine response: results is not a list",
            )

        normalized: list[dict[str, Any]] = []
        evidence_ids: list[str] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            evidence_id = str(
                item.get("chunk_id")
                or f"{item.get('document_id')}:{item.get('version')}:{item.get('page')}"
            )

            normalized.append(
                {
                    "evidence_id": evidence_id,
                    "source_class": "CORPORATE",
                    "source_id": str(item.get("document_id", "")),
                    "source_location": item.get("source_file"),
                    "claim": item.get("content", ""),
                    "access_scope": item.get("access_scope"),
                    "version": item.get("version"),
                    "effective_from": item.get("effective_from"),
                    "effective_to": item.get("effective_to"),
                    "retrieval_score": item.get("score"),
                    "confidence": item.get("confidence"),
                    "lifecycle_status": item.get("lifecycle_status"),
                    "page": item.get("page"),
                    "chunk_id": item.get("chunk_id"),
                }
            )
            evidence_ids.append(evidence_id)

        strategy = RetrievalStrategy(
            candidate_limit=int(
                request.input.get("candidate_limit", 50)
            ),
            max_documents=int(
                request.input.get("max_documents", 20)
            ),
            max_chunks_per_document=int(
                request.input.get("max_chunks_per_document", 2)
            ),
            score_threshold=float(
                request.input.get("score_threshold", 0.45)
            ),
        )

        selected = diversify_candidates(
            normalized,
            max_documents=strategy.max_documents,
            max_chunks_per_document=strategy.max_chunks_per_document,
        )

        selected_evidence_ids = [
            str(item["evidence_id"])
            for item in selected
            if item.get("evidence_id")
        ]

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "query": data.get("query", query.strip()),
                "results": selected,
                "raw_result_count": len(results),
                "selected_result_count": len(selected),
            },
            evidence_ids=selected_evidence_ids,
        )
