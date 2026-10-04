import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import authenticate_service
from app.main import app
from app.qdrant import QdrantStore


def credential_config(**overrides):
    entry = {
        "token": "test-secret",
        "permissions": ["search", "query", "ingest", "lifecycle", "repository_read"],
        "access_scopes": ["INTERNAL"],
        "classifications": ["INTERNAL"],
        "project_ids": ["project-a"],
    }
    entry.update(overrides)
    return {"orchestrator": entry}


def test_service_auth_fails_closed_when_configuration_missing(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS", raising=False)
    with pytest.raises(HTTPException) as exc:
        authenticate_service("Bearer test-secret", "search")
    assert exc.value.status_code == 503
    assert exc.value.detail == "SERVICE_AUTH_NOT_CONFIGURED"


def test_service_auth_requires_valid_token_and_permission(monkeypatch):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    with pytest.raises(HTTPException) as unauthenticated:
        authenticate_service(None, "search")
    assert unauthenticated.value.status_code == 401

    with pytest.raises(HTTPException) as denied:
        authenticate_service("Bearer test-secret", "admin")
    assert denied.value.status_code == 403

    principal = authenticate_service("Bearer test-secret", "search")
    assert principal.service == "orchestrator"
    assert principal.access_scopes == ("INTERNAL",)


def test_invalid_or_empty_retrieval_policy_is_not_accepted(monkeypatch):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config(access_scopes=[])),
    )
    with pytest.raises(HTTPException) as exc:
        authenticate_service("Bearer test-secret", "search")
    assert exc.value.status_code == 401


def test_search_endpoint_requires_internal_service_auth(monkeypatch):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "test"})
    assert response.status_code == 401


def test_search_defaults_to_current_and_enforces_scope_classification_project(
    monkeypatch,
):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    from app import main

    captured = {}

    async def embed(_query):
        return [0.1]

    def search(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(main.embedding, "embed", embed)
    monkeypatch.setattr(main.qdrant, "search", search)
    response = TestClient(app).post(
        "/v1/search",
        headers={"Authorization": "Bearer test-secret"},
        json={"query": "test"},
    )

    assert response.status_code == 200
    assert captured["lifecycle_status"] == "CURRENT"
    assert captured["access_scopes"] == ("INTERNAL",)
    assert captured["classifications"] == ("INTERNAL",)
    assert captured["project_ids"] == ("project-a",)


def test_search_rejects_historical_and_ingesting_without_historical_permission(
    monkeypatch,
):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-secret"}
    archived = client.post(
        "/v1/search",
        headers=headers,
        json={"query": "test", "lifecycle_status": "ARCHIVED"},
    )
    ingesting = client.post(
        "/v1/search",
        headers=headers,
        json={"query": "test", "lifecycle_status": "INGESTING"},
    )
    assert archived.status_code == 403
    assert archived.json()["detail"] == "HISTORICAL_READ_NOT_AUTHORIZED"
    assert ingesting.status_code == 403
    assert ingesting.json()["detail"] == "INGESTING_NOT_RETRIEVABLE"


def test_qdrant_search_always_builds_authorization_filters():
    class FakeClient:
        def query_points(self, **kwargs):
            self.kwargs = kwargs
            return type("Result", (), {"points": []})()

    store = QdrantStore.__new__(QdrantStore)
    store.collection = "corporate_knowledge"
    store.client = FakeClient()
    store.search(
        vector=[0.1],
        limit=5,
        score_threshold=0.4,
        access_scopes=("INTERNAL",),
        classifications=("INTERNAL",),
        project_ids=("project-a",),
    )
    query_filter = store.client.kwargs["query_filter"].model_dump(exclude_none=True)
    filters = {item["key"]: item for item in query_filter["must"]}
    assert filters["lifecycle_status"]["match"]["value"] == "CURRENT"
    assert filters["access_scope"]["match"]["any"] == ["INTERNAL"]
    assert filters["classification"]["match"]["any"] == ["INTERNAL"]
    assert filters["canonical_source_verified"]["match"]["value"] is True
    assert filters["project_id"]["match"]["any"] == ["project-a"]


def test_document_chunk_scroll_excludes_legacy_unverified_points():
    class FakeClient:
        def scroll(self, **kwargs):
            self.kwargs = kwargs
            return [], None

    store = QdrantStore.__new__(QdrantStore)
    store.collection = "corporate_knowledge"
    store.client = FakeClient()
    assert store.get_document_chunks(
        "doc-1",
        1,
        access_scopes=("INTERNAL",),
        classifications=("INTERNAL",),
        project_ids=("project-a",),
    ) == []
    conditions = store.client.kwargs["scroll_filter"].must
    markers = [
        condition for condition in conditions
        if condition.key == "canonical_source_verified"
    ]
    assert len(markers) == 1
    assert markers[0].match.value is True


def test_ingest_rejects_missing_or_false_canonical_verification(monkeypatch):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-secret"}
    base = {
        "document_id": "doc-1",
        "source_file": "sample.txt",
        "content": "content",
    }
    missing = client.post("/v1/ingest", headers=headers, json=base)
    false_marker = client.post(
        "/v1/ingest",
        headers=headers,
        json={**base, "canonical_source_verified": False},
    )
    assert missing.status_code == 422
    assert false_marker.status_code == 403
    assert false_marker.json()["detail"] == "CANONICAL_SOURCE_NOT_VERIFIED"


def test_ingest_persists_verified_marker(monkeypatch):
    monkeypatch.setenv(
        "KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS",
        json.dumps(credential_config()),
    )
    from app import main

    captured = {}

    async def embed(_content):
        return [0.1]

    def upsert(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main.embedding, "embed", embed)
    monkeypatch.setattr(main.qdrant, "upsert", upsert)
    response = TestClient(app).post(
        "/v1/ingest",
        headers={"Authorization": "Bearer test-secret"},
        json={
            "document_id": "doc-1",
            "source_file": "sample.txt",
            "content": "content",
            "canonical_source_verified": True,
        },
    )
    assert response.status_code == 200
    assert captured["payload"]["canonical_source_verified"] is True


def test_qdrant_search_refuses_missing_authorization_filters():
    store = QdrantStore.__new__(QdrantStore)
    store.collection = "corporate_knowledge"
    with pytest.raises(ValueError, match="authorization filters are required"):
        store.search(vector=[0.1], limit=5, score_threshold=0.4)
