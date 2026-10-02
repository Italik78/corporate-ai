import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import (
    VERSION,
    heuristic_route,
    latest_user_message,
    metadata_from_rag,
    source_context,
    valid_source_citations,
    routing_context,
    authorize_document_request,
)


def test_version():
    assert VERSION == "0.3.3"


def test_internal_question_routes_to_rag():
    assert heuristic_route("Какъв е размерът на дневните командировъчни?") == "rag"


def test_general_question_is_not_forced_by_heuristic():
    assert heuristic_route("Как работи Docker контейнер?") is None


def test_latest_user_message_ignores_assistant():
    messages = [
        {"role": "user", "content": "първи въпрос"},
        {"role": "assistant", "content": "отговор"},
        {"role": "user", "content": "втори въпрос"},
    ]
    assert latest_user_message(messages) == "втори въпрос"


def test_source_context_contains_provenance():
    context = source_context([{
        "document_id": "doc-1",
        "source_file": "policy.md",
        "page": 3,
        "score": 0.81,
        "content": "Дневните са 40 EUR.",
    }])
    assert "[SOURCE 1]" in context
    assert "document_id: doc-1" in context
    assert "source_file: policy.md" in context
    assert "page: 3" in context
    assert "Дневните са 40 EUR." in context


def test_metadata_preserves_evidence():
    result = {
        "grounded": True,
        "answer_status": "SUPPORTED",
        "evidence_status": "SUPPORTED",
        "evidence_claims": [{"type": "supported"}],
        "evidence_reason": "ok",
        "sources": [{"document_id": "doc-1"}],
    }
    metadata = metadata_from_rag(result, "deterministic_domain_match")
    assert metadata["gateway_version"] == "0.3.3"
    assert metadata["route"] == "rag"
    assert metadata["grounded"] is True
    assert metadata["evidence_status"] == "SUPPORTED"
    assert metadata["sources"][0]["document_id"] == "doc-1"


def test_citation_validation_rejects_missing_citations():
    assert not valid_source_citations("Отговор без източник.", 2)


def test_citation_validation_rejects_unknown_source():
    assert not valid_source_citations("Твърдение [3].", 2)


def test_citation_validation_accepts_known_source():
    assert valid_source_citations("Твърдение [1].", 2)


def test_routing_context_uses_user_turns_only():
    messages = [
        type("M", (), {"role": "user", "content": "Каква е нашата политика за отпуските?"})(),
        type("M", (), {"role": "assistant", "content": "Измислен асистентски отговор."})(),
        type("M", (), {"role": "user", "content": "А при нас как е?"})(),
    ]
    context = routing_context(messages, "А при нас как е?")
    assert "нашата политика" in context
    assert "А при нас как е?" in context
    assert "Измислен асистентски отговор" not in context

def test_retrieval_rewrite_prompt_contains_conversation_and_current_question():
    from app.main import retrieval_rewrite_prompt

    messages = [
        type("M", (), {"role": "user", "content": "Какви са основните функции на отдел ИКТС?"})(),
        type("M", (), {"role": "assistant", "content": "Това е предишен отговор."})(),
        type("M", (), {"role": "user", "content": "Тези функции следва ли да се допълнят?"})(),
    ]

    prompt = retrieval_rewrite_prompt(messages)

    assert "Какви са основните функции на отдел ИКТС?" in prompt
    assert "Тези функции следва ли да се допълнят?" in prompt
    assert "предишен отговор" in prompt
    assert "не добавяй факти" in prompt.lower()


def test_document_api_key_is_optional_by_default(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "")
    authorize_document_request(None)


def test_document_api_key_rejects_invalid_key(monkeypatch):
    import pytest
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")
    with pytest.raises(main.HTTPException) as exc:
        authorize_document_request("wrong")
    assert exc.value.status_code == 401


def test_document_api_key_accepts_valid_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")
    authorize_document_request("secret")


def test_document_loader_requires_configuration(monkeypatch):
    import pytest
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "")
    with pytest.raises(main.HTTPException) as exc:
        main.authorize_document_loader(None)
    assert exc.value.status_code == 503
    assert exc.value.detail == "DOCUMENT_LOADER_NOT_CONFIGURED"


def test_document_loader_rejects_invalid_bearer(monkeypatch):
    import pytest
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")
    with pytest.raises(main.HTTPException) as exc:
        main.authorize_document_loader("Bearer wrong")
    assert exc.value.status_code == 401
    assert exc.value.detail == "INVALID_DOCUMENT_LOADER_API_KEY"


def test_document_loader_accepts_valid_bearer(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")
    main.authorize_document_loader("Bearer secret")


def test_process_returns_normalized_document(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "ingestion_id": "ing-001",
                "document": {
                    "document_id": "doc-001",
                    "source_file": "test.txt",
                    "media_type": "text/plain",
                    "content_hash": "abc123",
                    "metadata": {"source_system": "open-webui"},
                    "blocks": [
                        {"content": "Първи блок."},
                        {"content": "Втори блок."},
                    ],
                },
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.put(
        "/process",
        content=b"test content",
        headers={
            "Authorization": "Bearer secret",
            "X-Filename": "test.txt",
            "Content-Type": "text/plain",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_content"] == "Първи блок.\n\nВтори блок."
    assert payload["metadata"]["ingestion_id"] == "ing-001"
    assert payload["metadata"]["document_id"] == "doc-001"
    assert payload["metadata"]["content_hash"] == "abc123"
    assert payload["metadata"]["source_system"] == "open-webui"


def test_process_rejects_empty_normalized_document(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "secret")

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "ingestion_id": "ing-empty",
                "document": {
                    "document_id": "doc-empty",
                    "blocks": [],
                    "metadata": {},
                },
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.put(
        "/process",
        content=b"test content",
        headers={
            "Authorization": "Bearer secret",
            "X-Filename": "test.txt",
            "Content-Type": "text/plain",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "EMPTY_NORMALIZED_DOCUMENT"


def test_tool_api_key_valid(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    assert main.authorize_tool_request("Bearer test-secret") is None


def test_tool_api_key_missing(monkeypatch):
    import app.main as main
    from fastapi import HTTPException

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")

    with pytest.raises(HTTPException) as exc:
        main.authorize_tool_request(None)

    assert exc.value.status_code == 401
    assert exc.value.detail == "INVALID_TOOL_API_KEY"


def test_tool_api_key_not_configured(monkeypatch):
    import app.main as main
    from fastapi import HTTPException

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "")

    with pytest.raises(HTTPException) as exc:
        main.authorize_tool_request("Bearer test-secret")

    assert exc.value.status_code == 503
    assert exc.value.detail == "TOOL_API_NOT_CONFIGURED"


def test_web_search_returns_normalized_web_evidence(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")

    class FakeResponse:
        content = b'{"results": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "title": "OpenAI",
                        "url": "https://openai.com/",
                        "content": "Artificial intelligence research and products.",
                        "publishedDate": "2026-09-30",
                        "score": 7.5,
                    }
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_search",
        json={"query": "OpenAI", "count": 3},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["source_class"] == "WEB"
    assert payload["retrieval_status"] == "FOUND"
    assert len(payload["evidence"]) == 1

    evidence = payload["evidence"][0]
    assert evidence["query"] == "OpenAI"
    assert evidence["title"] == "OpenAI"
    assert evidence["url"] == "https://openai.com/"
    assert evidence["domain"] == "openai.com"
    assert evidence["snippet"] == "Artificial intelligence research and products."
    assert evidence["content"] == "Artificial intelligence research and products."
    assert evidence["published_at"] == "2026-09-30"
    assert evidence["retrieval_method"] == "searxng_search"
    assert evidence["source_rank"] == 1
    assert evidence["ranking_score"] == 7.5
    assert evidence["access_scope"] == "PUBLIC"
    assert len(evidence["content_hash"]) == 64
    assert evidence["fetched_at"].endswith("Z")


def test_web_search_blocks_configured_domain(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", {"blocked.example"})

    class FakeResponse:
        content = b'{"results": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "title": "Blocked",
                        "url": "https://blocked.example/page",
                        "content": "Should not become evidence.",
                    }
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_search",
        json={"query": "blocked"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_status"] == "NO_RESULTS"
    assert payload["evidence"] == []


def test_web_search_timeout(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            raise main.httpx.TimeoutException("timeout")

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_search",
        json={"query": "OpenAI"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "WEB_SEARCH_TIMEOUT"


def test_web_fetch_blocks_loopback_ip(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    allowed, domain = main._web_fetch_url_allowed("http://127.0.0.1:8080/")
    assert allowed is False
    assert domain == "127.0.0.1"


def test_web_fetch_blocks_private_ip(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    allowed, domain = main._web_fetch_url_allowed("http://10.0.0.10/")
    assert allowed is False
    assert domain == "10.0.0.10"


def test_web_fetch_blocks_configured_domain(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", {"blocked.example"})
    allowed, domain = main._web_fetch_url_allowed("https://blocked.example/page")
    assert allowed is False
    assert domain == "blocked.example"


def test_web_fetch_allows_public_domain(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    allowed, domain = main._web_fetch_url_allowed("https://example.com/page")
    assert allowed is True
    assert domain == "example.com"


def test_web_fetch_returns_web_evidence(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    class FakeResponse:
        status_code = 200
        headers = {
            "content-type": "text/html; charset=utf-8",
            "content-length": "18",
        }

        @property
        def is_redirect(self):
            return False

        @property
        def is_permanent_redirect(self):
            return False

        def raise_for_status(self):
            pass

        async def aiter_bytes(self):
            yield b"<html>hello</html>"

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *args):
            pass

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return FakeStreamContext()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/page"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    evidence = payload["evidence"][0]

    assert payload["source_class"] == "WEB"
    assert payload["retrieval_status"] == "FOUND"
    assert evidence["url"] == "https://example.com/page"
    assert evidence["domain"] == "example.com"
    assert evidence["content"] == "hello"
    assert evidence["retrieval_method"] == "http_fetch"
    assert evidence["content_type"] == "text/html"
    assert evidence["untrusted_content"] is True
    assert len(evidence["content_hash"]) == 64


def test_web_fetch_sanitizes_html_content():
    import app.main as main

    raw = b"""
    <html>
      <head><style>body { color: red; }</style><script>alert("x")</script></head>
      <body>
        <h1>Important title</h1>
        <p>Useful <b>content</b>.</p>
        <iframe>evil frame</iframe>
      </body>
    </html>
    """

    result = main._sanitize_web_content(raw, "text/html")

    assert result == "Important title Useful content."
    assert "alert" not in result
    assert "color: red" not in result
    assert "evil frame" not in result


def test_web_fetch_rejects_content_type(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/octet-stream"}

        @property
        def is_redirect(self):
            return False

        @property
        def is_permanent_redirect(self):
            return False

        def raise_for_status(self):
            pass

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *args):
            pass

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return FakeStreamContext()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/file"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "WEB_FETCH_CONTENT_TYPE_NOT_ALLOWED"


def test_web_fetch_enforces_response_size(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(main, "WEB_SEARCH_MAX_RESPONSE_SIZE", 10)
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/html"}

        @property
        def is_redirect(self):
            return False

        @property
        def is_permanent_redirect(self):
            return False

        def raise_for_status(self):
            pass

        async def aiter_bytes(self):
            yield b"this is definitely too large"

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *args):
            pass

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return FakeStreamContext()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/large"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "WEB_FETCH_RESPONSE_TOO_LARGE"


def test_web_fetch_timeout(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            raise main.httpx.TimeoutException("timeout")

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/page"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "WEB_FETCH_TIMEOUT"


def test_web_fetch_blocks_redirect_to_private_ip(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    class FakeResponse:
        status_code = 302
        headers = {"location": "http://127.0.0.1:8080/admin"}

        @property
        def is_redirect(self):
            return True

        @property
        def is_permanent_redirect(self):
            return False

        def raise_for_status(self):
            pass

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *args):
            pass

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return FakeStreamContext()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/redirect"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "WEB_FETCH_URL_NOT_ALLOWED"


def test_web_fetch_allows_safe_redirect(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "GATEWAY_API_KEY", "test-secret")
    monkeypatch.setattr(main, "WEB_SEARCH_BLOCKED_DOMAINS", set())
    monkeypatch.setattr(main, "WEB_SEARCH_ALLOWED_DOMAINS", {"example.com"})
    monkeypatch.setattr(
        main.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
        ],
    )

    responses = [
        (302, {"location": "https://example.com/final"}, None),
        (200, {"content-type": "text/html"}, b"<html>final</html>"),
    ]

    class FakeResponse:
        def __init__(self, item):
            self.status_code, self.headers, self.body = item

        @property
        def is_redirect(self):
            return self.status_code in {301, 302, 303, 307, 308}

        @property
        def is_permanent_redirect(self):
            return self.status_code in {301, 308}

        def raise_for_status(self):
            pass

        async def aiter_bytes(self):
            if self.body is not None:
                yield self.body

    class FakeStreamContext:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, *args):
            pass

    class FakeAsyncClient:
        index = 0

        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            response = FakeResponse(responses[FakeAsyncClient.index])
            FakeAsyncClient.index += 1
            return FakeStreamContext(response)

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(main.app)
    response = client.post(
        "/v1/tools/web_fetch",
        json={"url": "https://example.com/redirect"},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    evidence = response.json()["evidence"][0]
    assert evidence["url"] == "https://example.com/final"
    assert evidence["content"] == "final"
    assert evidence["redirects"] == 1


def test_current_time_context_uses_configured_timezone():
    from app.main import current_time_context

    context = current_time_context()

    assert "CORPORATE_AI_CURRENT_TIME" in context
    assert "Timezone: Europe/Sofia" in context
    assert "Current local date:" in context
    assert "Current local time:" in context
    assert "Weekday:" in context
    assert "Current UTC timestamp:" in context
    assert "Source: authoritative system clock" in context


def test_current_time_context_has_valid_date_and_time():
    from datetime import datetime
    import re
    from app.main import current_time_context

    context = current_time_context()

    date_match = re.search(r"Current local date: (\d{4}-\d{2}-\d{2})", context)
    time_match = re.search(r"Current local time: (\d{2}:\d{2}:\d{2})", context)
    utc_match = re.search(r"Current UTC timestamp: (.+)", context)

    assert date_match
    assert time_match
    assert utc_match

    datetime.strptime(date_match.group(1), "%Y-%m-%d")
    datetime.strptime(time_match.group(1), "%H:%M:%S")
    datetime.fromisoformat(utc_match.group(1))


def test_current_time_context_is_injected_only_once():
    from app.main import with_current_time_context

    messages = [{"role": "user", "content": "Колко е часът?"}]

    first = with_current_time_context(messages)
    second = with_current_time_context(first)

    assert len(first) == 2
    assert len(second) == 2
    assert second[0]["content"] == first[0]["content"]


def test_current_time_context_moves_all_system_messages_to_front():
    from app.main import with_current_time_context

    messages = [
        {"role": "user", "content": "Първи въпрос"},
        {"role": "system", "content": "Open WebUI system prompt"},
        {"role": "assistant", "content": "Предишен отговор"},
        {"role": "user", "content": "Втори въпрос"},
    ]

    result = with_current_time_context(messages)

    assert [message["role"] for message in result] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert "Open WebUI system prompt" in result[0]["content"]
    assert "[CORPORATE_AI_CURRENT_TIME]" in result[0]["content"]
    assert result[0]["content"].startswith("[CORPORATE_AI_CURRENT_TIME]")
    assert [message["content"] for message in result[1:]] == [
        "Първи въпрос",
        "Предишен отговор",
        "Втори въпрос",
    ]
