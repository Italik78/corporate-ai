import asyncio
import hashlib
from pathlib import Path

import pytest

from app import recovery
from app.models import DocumentVersionResponse, LifecycleStatus


def _version(source: bytes) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        document_id="recover-001",
        version=2,
        source_file="recovery.txt",
        content_hash=hashlib.sha256(source).hexdigest(),
        canonical_storage_key="documents/recover-001/original/2/recovery.txt",
        source_system="upload",
        title="recovery",
        classification="INTERNAL",
        language="bg",
        lifecycle_status=LifecycleStatus.INGESTING,
        supersedes="recover-001:v1",
        access_scope="INTERNAL",
        created_at="2026-10-01T00:00:00+00:00",
        updated_at="2026-10-01T00:00:00+00:00",
    )


def test_recovery_replays_partial_index_with_stable_chunk_ids(monkeypatch):
    source = ("corporate recovery evidence " * 100).encode()
    metadata = _version(source)
    events = []

    class FakeRepository:
        async def get_version(self, document_id, version):
            assert (document_id, version) == ("recover-001", 2)
            return metadata

        async def copy_validated_canonical_source(self, document_id, version, target):
            assert (document_id, version) == ("recover-001", 2)
            Path(target).write_bytes(source)
            return metadata

        async def finalize_version(self, document_id, version):
            assert (document_id, version) == ("recover-001", 2)
            events.append("pg_finalize")
            return metadata.model_copy(
                update={"lifecycle_status": LifecycleStatus.CURRENT}
            )

    class FakeKnowledgeClient:
        def __init__(self):
            self.seen = []
            self.failed_once = False
            self.points = {}
            self.lifecycle = []

        async def ingest(self, chunk):
            assert chunk.classification == "INTERNAL"
            assert chunk.canonical_source_verified is True
            assert chunk.canonical_storage_key == metadata.canonical_storage_key
            self.seen.append(chunk.chunk_id)
            if chunk.chunk_id.endswith("00002") and not self.failed_once:
                self.failed_once = True
                raise RuntimeError("simulated mid-batch outage")
            self.points[chunk.chunk_id] = chunk.content

        async def set_lifecycle_status(self, **kwargs):
            self.lifecycle.append(kwargs)
            events.append(f"ke_lifecycle:{kwargs['document_id']}:v{kwargs['version']}:{kwargs['lifecycle_status']}")

    client = FakeKnowledgeClient()
    job_updates = []

    async def update_jobs(*args, **kwargs):
        job_updates.append((args, kwargs))

    monkeypatch.setattr(recovery, "repository", FakeRepository())
    monkeypatch.setattr(recovery, "KnowledgeEngineClient", lambda: client)
    monkeypatch.setattr(recovery, "update_ingestion_jobs_for_version", update_jobs)

    with pytest.raises(RuntimeError, match="simulated mid-batch outage"):
        asyncio.run(recovery.recover_ingesting_version("recover-001", 2))
    assert job_updates[0][1]["status"] == "RECOVERING"

    result = asyncio.run(recovery.recover_ingesting_version("recover-001", 2))

    assert result["status"] == "READY"
    assert result["lifecycle_status"] == "CURRENT"
    assert result["chunk_count"] >= 1
    assert len(client.points) == result["chunk_count"]
    assert client.seen.count("recover-001:v2:chunk:00001") == 2
    assert job_updates[-1][1]["status"] == "READY"
    assert len(client.lifecycle) == 2  # recovered version and superseded predecessor
    assert events.index("ke_lifecycle:recover-001:v1:SUPERSEDED") < events.index("pg_finalize")
    assert events.index("pg_finalize") < events.index("ke_lifecycle:recover-001:v2:CURRENT")
