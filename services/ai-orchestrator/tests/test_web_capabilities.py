import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.capabilities import CapabilityRequest
from app.models import CapabilityType
from app.web_fetch import WebFetchCapability
from app.web_search import WebSearchCapability


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _mock_client(response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=response)
    return client


def test_web_search_calls_gateway_tool():
    response = _mock_response(
        {
            "query": "test query",
            "retrieval_status": "FOUND",
            "source_class": "WEB",
            "evidence": [{"url": "https://example.com"}],
        }
    )
    client = _mock_client(response)

    with patch(
        "app.web_search.httpx.AsyncClient",
        return_value=client,
    ):
        capability = WebSearchCapability(
            base_url="http://gateway:8080",
        )
        result = asyncio.run(
            capability.execute(
                CapabilityRequest(
                    capability=CapabilityType.WEB_SEARCH,
                    input={"query": "test query"},
                )
            )
        )

    assert result.success is True
    assert result.data["retrieval_status"] == "FOUND"
    client.post.assert_awaited_once_with(
        "http://gateway:8080/v1/tools/web_search",
        json={
            "query": "test query",
            "count": 5,
            "language": "all",
        },
    )


def test_web_fetch_calls_gateway_tool():
    response = _mock_response(
        {
            "retrieval_status": "FOUND",
            "source_class": "WEB",
            "evidence": [
                {
                    "url": "https://example.com/article",
                    "content": "Fetched content.",
                }
            ],
        }
    )
    client = _mock_client(response)

    with patch(
        "app.web_fetch.httpx.AsyncClient",
        return_value=client,
    ):
        capability = WebFetchCapability(
            base_url="http://gateway:8080",
        )
        result = asyncio.run(
            capability.execute(
                CapabilityRequest(
                    capability=CapabilityType.WEB_FETCH,
                    input={"url": "https://example.com/article"},
                )
            )
        )

    assert result.success is True
    assert result.data["retrieval_status"] == "FOUND"
    client.post.assert_awaited_once_with(
        "http://gateway:8080/v1/tools/web_fetch",
        json={"url": "https://example.com/article"},
    )


def test_web_search_rejects_missing_query():
    capability = WebSearchCapability(
        base_url="http://gateway:8080",
    )

    result = asyncio.run(
        capability.execute(
            CapabilityRequest(
                capability=CapabilityType.WEB_SEARCH,
                input={},
            )
        )
    )

    assert result.success is False
    assert result.error == "query is required"


def test_web_fetch_rejects_missing_url():
    capability = WebFetchCapability(
        base_url="http://gateway:8080",
    )

    result = asyncio.run(
        capability.execute(
            CapabilityRequest(
                capability=CapabilityType.WEB_FETCH,
                input={},
            )
        )
    )

    assert result.success is False
    assert result.error == "url is required"
