import asyncio

import pytest

from app import repository as repository_module
from app.models import DocumentMetadata, LifecycleStatus


def _metadata(document_id: str = "repo-test-001") -> DocumentMetadata:
    return DocumentMetadata(
        document_id=document_id,
        title="Repository contract test",
        created_at="2026-09-23T00:00:00+00:00",
        updated_at="2026-09-23T00:00:00+00:00",
    )


def test_postgres_repository_delegates_register_version(monkeypatch):
    expected = _metadata()
    calls = {}

    async def fake_register(metadata, source_file, content_hash):
        calls["args"] = (metadata, source_file, content_hash)
        return expected

    monkeypatch.setattr(repository_module, "register_version", fake_register)

    result = asyncio.run(
        repository_module.PostgresRepository().register_version(
            _metadata(), "/tmp/source.pdf", "sha256:test"
        )
    )

    assert result is expected
    assert calls["args"][1:] == ("/tmp/source.pdf", "sha256:test")


def test_postgres_repository_preserves_duplicate_error(monkeypatch):
    async def fake_register(*args):
        raise repository_module.DuplicateDocumentError("duplicate")

    monkeypatch.setattr(repository_module, "register_version", fake_register)

    with pytest.raises(repository_module.DuplicateDocumentError, match="duplicate"):
        asyncio.run(
            repository_module.PostgresRepository().register_version(
                _metadata(), "/tmp/source.pdf", "sha256:test"
            )
        )


def test_postgres_repository_maps_metadata_error(monkeypatch):
    async def fake_register(*args):
        raise repository_module.MetadataError("database failure")

    monkeypatch.setattr(repository_module, "register_version", fake_register)

    with pytest.raises(repository_module.RepositoryError, match="database failure"):
        asyncio.run(
            repository_module.PostgresRepository().register_version(
                _metadata(), "/tmp/source.pdf", "sha256:test"
            )
        )


def test_postgres_repository_delegates_lifecycle_operations(monkeypatch):
    expected = _metadata()
    calls = []

    async def fake_finalize(document_id, version):
        calls.append(("finalize", document_id, version))
        return expected

    async def fake_fail(document_id, version):
        calls.append(("fail", document_id, version))

    async def fake_list(document_id):
        calls.append(("list", document_id))
        return []

    async def fake_get(document_id, version):
        calls.append(("get", document_id, version))
        return None

    monkeypatch.setattr(repository_module, "finalize_version", fake_finalize)
    monkeypatch.setattr(repository_module, "fail_version", fake_fail)
    monkeypatch.setattr(repository_module, "list_versions", fake_list)
    monkeypatch.setattr(repository_module, "get_version", fake_get)

    repo = repository_module.PostgresRepository()

    assert asyncio.run(repo.finalize_version("repo-test-001", 2)) is expected
    assert asyncio.run(repo.fail_version("repo-test-001", 2)) is None
    assert asyncio.run(repo.list_versions("repo-test-001")) == []
    assert asyncio.run(repo.get_version("repo-test-001", 2)) is None

    assert calls == [
        ("finalize", "repo-test-001", 2),
        ("fail", "repo-test-001", 2),
        ("list", "repo-test-001"),
        ("get", "repo-test-001", 2),
    ]


def test_postgres_repository_maps_lifecycle_metadata_errors(monkeypatch):
    async def fake_finalize(*args):
        raise repository_module.MetadataError("lifecycle failure")

    monkeypatch.setattr(repository_module, "finalize_version", fake_finalize)

    with pytest.raises(repository_module.RepositoryError, match="lifecycle failure"):
        asyncio.run(
            repository_module.PostgresRepository().finalize_version(
                "repo-test-001", 1
            )
        )


def test_repository_contract_exposes_lifecycle_status_model():
    metadata = _metadata()
    assert metadata.lifecycle_status is LifecycleStatus.INGESTING
