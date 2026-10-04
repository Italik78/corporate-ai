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
        headers={},
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
        headers={},
    )


def test_web_search_uses_configured_gateway_service_key(monkeypatch):
    monkeypatch.setenv("GATEWAY_TOOL_API_KEY", "test-key")
    client = _mock_client(_mock_response({"evidence": []}))
    with patch("app.web_search.httpx.AsyncClient", return_value=client):
        capability = WebSearchCapability(base_url="http://gateway:8080")
        asyncio.run(capability.execute(CapabilityRequest(
            capability=CapabilityType.WEB_SEARCH,
            input={"query": "test"},
        )))
    assert client.post.await_args.kwargs["headers"] == {"Authorization": "Bearer test-key"}


def test_explicit_official_query_filters_to_server_mapped_domain(monkeypatch):
    monkeypatch.setenv(
        "CORPORATE_AI_OFFICIAL_DOMAIN_MAP",
        '{"апис":["apis.bg"]}',
    )
    response = _mock_response({"retrieval_status": "FOUND", "evidence": [
        {"url": "https://www.apis.bg/bg/ceni", "content": "official"},
        {"url": "https://web.apis.bg/prices", "content": "official subdomain"},
        {"url": "https://abo.cent.bg/apis", "content": "third party"},
        {"url": "https://notapis.bg/fake", "content": "lookalike"},
    ]})
    client = _mock_client(response)
    with patch("app.web_search.httpx.AsyncClient", return_value=client):
        result = asyncio.run(WebSearchCapability(base_url="http://gateway:8080").execute(
            CapabilityRequest(
                capability=CapabilityType.WEB_SEARCH,
                input={"query": "Актуални цени от официалния сайт на АПИС"},
            )
        ))
    assert result.success is True
    assert [item["url"] for item in result.data["evidence"]] == [
        "https://www.apis.bg/bg/ceni",
        "https://web.apis.bg/prices",
    ]
    assert client.post.await_args.kwargs["json"]["query"].endswith("site:apis.bg")


def test_official_query_without_server_mapping_returns_no_evidence(monkeypatch):
    monkeypatch.setenv("CORPORATE_AI_OFFICIAL_DOMAIN_MAP", '{"apis":["apis.bg"]}')
    client = _mock_client(_mock_response({"retrieval_status": "FOUND", "evidence": [
        {"url": "https://python.org/downloads/", "content": "result"},
    ]}))
    with patch("app.web_search.httpx.AsyncClient", return_value=client):
        result = asyncio.run(WebSearchCapability(base_url="http://gateway:8080").execute(
            CapabilityRequest(
                capability=CapabilityType.WEB_SEARCH,
                input={"query": "Latest official Python stable version"},
            )
        ))
    assert result.success is True
    assert result.data["evidence"] == []
    assert result.data["retrieval_status"] == "NO_OFFICIAL_DOMAIN_MAPPING"
    client.post.assert_not_awaited()


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
