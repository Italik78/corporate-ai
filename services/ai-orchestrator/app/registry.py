from __future__ import annotations

from .capabilities import Capability
from .corporate_retrieval import CorporateRetrievalCapability
from .llm_reasoning import LLMReasoningCapability
from .structured_query import StructuredQueryCapability
from .web_fetch import WebFetchCapability
from .web_search import WebSearchCapability
from .models import CapabilityType


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[CapabilityType, Capability] = {
            CapabilityType.CORPORATE_RETRIEVAL: CorporateRetrievalCapability(),
            CapabilityType.STRUCTURED_QUERY: StructuredQueryCapability(),
            CapabilityType.WEB_SEARCH: WebSearchCapability(),
            CapabilityType.WEB_FETCH: WebFetchCapability(),
            CapabilityType.LLM_REASONING: LLMReasoningCapability(),
            CapabilityType.GENERAL_RESPONSE: LLMReasoningCapability(),
        }

    def get(self, capability_type: CapabilityType) -> Capability:
        capability = self._capabilities.get(capability_type)
        if capability is None:
            raise KeyError(f"capability not registered: {capability_type}")
        return capability
