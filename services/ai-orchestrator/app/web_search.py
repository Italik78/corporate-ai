from __future__ import annotations

import os
import json
from typing import Any
from urllib.parse import urlparse

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType


_OFFICIAL_CUES = (
    "official", "официален", "официална", "официалния", "официалното", "официални",
)


def _official_domain_allowlist(query: str) -> set[str] | None:
    normalized = query.casefold()
    if not any(cue in normalized for cue in _OFFICIAL_CUES):
        return None
    try:
        mapping = json.loads(os.getenv("CORPORATE_AI_OFFICIAL_DOMAIN_MAP", "{}"))
    except json.JSONDecodeError:
        return set()
    if not isinstance(mapping, dict):
        return set()
    domains: set[str] = set()
    for alias, configured_domains in mapping.items():
        if not isinstance(alias, str) or alias.casefold() not in normalized:
            continue
        values = configured_domains if isinstance(configured_domains, list) else []
        domains.update(
            value.strip().lower().lstrip(".")
            for value in values
            if isinstance(value, str) and value.strip()
        )
    return domains


def _host_matches_domain(hostname: str, allowed: str) -> bool:
    host = hostname.lower().rstrip(".")
    domain = allowed.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def _evidence_matches_official_domains(item: Any, domains: set[str]) -> bool:
    if not isinstance(item, dict) or not isinstance(item.get("url"), str):
        return False
    try:
        hostname = urlparse(item["url"]).hostname or ""
    except ValueError:
        return False
    return any(_host_matches_domain(hostname, domain) for domain in domains)


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
        self.gateway_api_key = os.getenv("GATEWAY_TOOL_API_KEY", "").strip()

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        query = request.input.get("query")
        if not isinstance(query, str) or not query.strip():
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="query is required",
            )

        official_domains = _official_domain_allowlist(query)
        if official_domains is not None and not official_domains:
            return CapabilityResult(
                capability=self.capability_type,
                success=True,
                data={
                    "query": query.strip(),
                    "retrieval_status": "NO_OFFICIAL_DOMAIN_MAPPING",
                    "source_class": "WEB",
                    "evidence": [],
                },
            )

        search_query = query.strip()
        if official_domains:
            search_query += " " + " OR ".join(
                f"site:{domain}" for domain in sorted(official_domains)
            )
        payload: dict[str, Any] = {
            "query": search_query,
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
                    headers={"Authorization": f"Bearer {self.gateway_api_key}"} if self.gateway_api_key else {},
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

        if official_domains is not None:
            evidence = [
                item for item in evidence
                if _evidence_matches_official_domains(item, official_domains)
            ]

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "query": query.strip(),
                "retrieval_status": (
                    data.get("retrieval_status")
                    if official_domains is None or evidence
                    else "NO_OFFICIAL_DOMAIN_MATCH"
                ),
                "source_class": data.get("source_class", "WEB"),
                "evidence": evidence,
            },
        )
