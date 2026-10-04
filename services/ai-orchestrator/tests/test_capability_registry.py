from app.models import CapabilityType
from app.registry import CapabilityRegistry
from app.web_fetch import WebFetchCapability
from app.web_search import WebSearchCapability


def test_registry_contains_web_capabilities():
    registry = CapabilityRegistry()

    assert isinstance(
        registry.get(CapabilityType.WEB_SEARCH),
        WebSearchCapability,
    )
    assert isinstance(
        registry.get(CapabilityType.WEB_FETCH),
        WebFetchCapability,
    )
