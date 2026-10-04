from __future__ import annotations

import os
from typing import Any

import httpx

from .capabilities import Capability, CapabilityRequest, CapabilityResult
from .models import CapabilityType


class LLMReasoningCapability(Capability):
    capability_type = CapabilityType.LLM_REASONING

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "QWEN_BASE_URL",
                "http://corporate-ai-qwen36:8000/v1",
            )
        ).rstrip("/")
        self.model = model or os.getenv("QWEN_MODEL", "qwen36")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("TIMEOUT_SECONDS", "120")
        )

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        messages = request.input.get("messages")

        if not isinstance(messages, list) or not messages:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="messages are required",
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.input.get("temperature", 0.0),
            "max_tokens": request.input.get("max_tokens", 1000),
        }

        response_format = request.input.get("response_format")
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error=f"LLM reasoning failed: {exc}",
            )

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid LLM response: choices is empty",
            )

        message = choices[0].get("message")
        if not isinstance(message, dict):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid LLM response: message is missing",
            )

        content = message.get("content")
        if not isinstance(content, str):
            return CapabilityResult(
                capability=self.capability_type,
                success=False,
                error="invalid LLM response: content is missing",
            )

        return CapabilityResult(
            capability=self.capability_type,
            success=True,
            data={
                "content": content,
                "model": data.get("model", self.model),
                "usage": data.get("usage"),
                "finish_reason": choices[0].get("finish_reason"),
            },
        )
