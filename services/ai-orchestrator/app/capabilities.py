from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from .models import CapabilityType


class CapabilityRequest(BaseModel):
    capability: CapabilityType
    input: dict[str, Any] = Field(default_factory=dict)


class CapabilityResult(BaseModel):
    capability: CapabilityType
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class Capability(ABC):
    capability_type: CapabilityType

    @abstractmethod
    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        raise NotImplementedError
