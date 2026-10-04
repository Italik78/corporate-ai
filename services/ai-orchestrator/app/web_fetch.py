from __future__ import annotations

import os
from typing import Any

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType


class WebFetchCapability(Capability):
    capability_type = CapabilityType.WEB_FETCH

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
        url = request.input.get("url")
        if not isinstance(url, str) or not url.strip():
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="url is required",
            )

        payload: dict[str, Any] = {
            "url": url.strip(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/tools/web_fetch",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"web fetch failed: {exc}",
            )

        if not isinstance(data, dict):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid web fetch response: expected object",
            )

        evidence = data.get("evidence")
        if not isinstance(evidence, list):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid web fetch response: evidence is not a list",
            )

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "source_class": data.get("source_class", "WEB"),
                "retrieval_status": data.get("retrieval_status"),
                "evidence": evidence,
            },
        )
