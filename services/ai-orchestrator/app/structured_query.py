from __future__ import annotations

import os
from typing import Any

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType


class StructuredQueryCapability(Capability):
    capability_type = CapabilityType.STRUCTURED_QUERY

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "DOCUMENT_INGESTION_URL",
                "http://corporate-ai-document-ingestion:8095",
            )
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("TIMEOUT_SECONDS", "120")
        )
        self.service_token = os.getenv(
            "KNOWLEDGE_ENGINE_SERVICE_TOKEN", ""
        ).strip()

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        payload: dict[str, Any] = dict(request.input)

        if not payload:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="structured query input is required",
            )

        if "source_file" not in payload and not (
            payload.get("document_id") and payload.get("version")
        ):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="exact document reference is required",
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    f"{self.base_url}/v1/documents/structured-query",
                    json=payload,
                    headers=(
                        {"Authorization": f"Bearer {self.service_token}"}
                        if self.service_token
                        else {}
                    ),
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text[:500]

            if (
                status == 409
                and isinstance(detail, dict)
                and detail.get("code") == "DOCUMENT_SOURCE_FILE_AMBIGUOUS"
            ):
                return CapabilityResult(
                    capability=self.capability_type,
                    success=False,
                    data={
                        "clarification_required": True,
                        "code": detail["code"],
                        "source_file": detail.get("source_file"),
                        "matches": detail.get("matches", []),
                    },
                    error=(
                        "structured query source file is ambiguous: "
                        f"{detail.get('source_file', '')}"
                    ),
                )

            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"structured query failed ({status}): {detail}",
            )

        except (httpx.HTTPError, ValueError) as exc:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"structured query failed: {exc}",
            )

        if not isinstance(data, dict):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid structured query response",
            )

        rows = data.get("rows")
        if not isinstance(rows, list):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid structured query response: rows is not a list",
            )

        document_id = str(data.get("document_id", ""))
        version = data.get("version")
        source_file = str(data.get("source_file", ""))

        if not document_id or not isinstance(version, int) or not source_file:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid structured query response metadata",
            )

        normalized_rows: list[dict[str, Any]] = []
        evidence_ids: list[str] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            sheet = row.get("sheet")
            sheet_index = row.get("sheet_index")
            row_index = row.get("row_index")
            cells = row.get("cells")

            if (
                not isinstance(sheet, str)
                or not isinstance(sheet_index, int)
                or not isinstance(row_index, int)
                or not isinstance(cells, dict)
            ):
                continue

            evidence_id = (
                f"structured:{document_id}:{version}:"
                f"{sheet_index}:{row_index}"
            )

            claim = "; ".join(
                f"{key}={value}"
                for key, value in cells.items()
            )

            normalized_rows.append(
                {
                    "evidence_id": evidence_id,
                    "source_class": "CORPORATE",
                    "source_id": document_id,
                    "source_location": (
                        f"{source_file}"
                        f"#sheet={sheet}"
                        f"&sheet_index={sheet_index}"
                        f"&row={row_index}"
                    ),
                    "claim": claim,
                    "version": version,
                    "content_hash": data.get("content_hash"),
                    "access_scope": "INTERNAL",
                    "structured_row": {
                        "sheet": sheet,
                        "sheet_index": sheet_index,
                        "row_index": row_index,
                        "cells": cells,
                    },
                }
            )
            evidence_ids.append(evidence_id)

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "document_id": document_id,
                "version": version,
                "source_file": source_file,
                "content_hash": data.get("content_hash"),
                "sheet": data.get("sheet"),
                "total_matches": data.get("total_matches", len(rows)),
                "rows": normalized_rows,
            },
            evidence_ids=evidence_ids,
        )
