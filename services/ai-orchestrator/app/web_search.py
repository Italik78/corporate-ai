from __future__ import annotations

import os
from typing import Any

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType


class WebSearchCapability(Capability):
    capability_type = CapabilityType.WEB_SEARCH

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "GATEWAY_URL",
                "http://corporate-ai-gateway-0.3.3:8080",
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
            "count": int(request.input.get("count", 5)),
            "language": str(request.input.get("language", "all")),
        }

        time_range = request.input.get("time_range")
        if time_range is not None:
            payload["time_range"] = str(time_range)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/tools/web_search",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"web search failed: {exc}",
            )

        if not isinstance(data, dict):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid web search response: expected object",
            )

        evidence = data.get("evidence")
        if not isinstance(evidence, list):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid web search response: evidence is not a list",
            )

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "query": data.get("query", query.strip()),
                "retrieval_status": data.get("retrieval_status"),
                "source_class": data.get("source_class", "WEB"),
                "evidence": evidence,
            },
        )
