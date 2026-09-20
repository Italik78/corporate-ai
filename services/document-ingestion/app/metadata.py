from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import settings
from .models import DocumentMetadata, DocumentVersionResponse, LifecycleStatus


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS document_versions (
    document_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    source_file TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    source_system TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    classification TEXT NOT NULL,
    language TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    document_date DATE,
    effective_from DATE,
    effective_to DATE,
    lifecycle_status TEXT NOT NULL,
    parent_document_id TEXT,
    supersedes TEXT,
    superseded_by TEXT,
    project_id TEXT,
    access_scope TEXT NOT NULL DEFAULT 'INTERNAL',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (document_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_document_versions_current
    ON document_versions(document_id)
    WHERE lifecycle_status = 'CURRENT';

CREATE INDEX IF NOT EXISTS ix_document_versions_hash
    ON document_versions(content_hash);

CREATE INDEX IF NOT EXISTS ix_document_versions_project
    ON document_versions(project_id);

CREATE INDEX IF NOT EXISTS ix_document_versions_effective
    ON document_versions(document_id, effective_from, effective_to);
"""


class MetadataError(RuntimeError):
    pass


class DuplicateDocumentError(MetadataError):
    pass


class VersionConflictError(MetadataError):
    pass


async def initialize_metadata() -> None:
    async with await psycopg.AsyncConnection.connect(settings.metadata_database_url) as conn:
        for statement in SCHEMA_SQL.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(statement)


async def health() -> bool:
    try:
        async with await psycopg.AsyncConnection.connect(settings.metadata_database_url) as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _row_to_model(row: dict[str, Any]) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        document_id=row["document_id"],
        version=row["version"],
        source_file=row["source_file"],
        content_hash=row["content_hash"],
        source_system=row["source_system"],
        title=row["title"],
        author=row["author"],
        classification=row["classification"],
        language=row["language"],
        document_date=row["document_date"].isoformat() if row["document_date"] else None,
        effective_from=row["effective_from"].isoformat() if row["effective_from"] else None,
        effective_to=row["effective_to"].isoformat() if row["effective_to"] else None,
        lifecycle_status=LifecycleStatus(row["lifecycle_status"]),
        parent_document_id=row["parent_document_id"],
        supersedes=row["supersedes"],
        superseded_by=row["superseded_by"],
        project_id=row["project_id"],
        access_scope=row["access_scope"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


async def register_version(
    metadata: DocumentMetadata,
    source_file: str,
    content_hash: str,
) -> DocumentMetadata:
    async with await psycopg.AsyncConnection.connect(settings.metadata_database_url) as conn:
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (metadata.document_id,),
            )

            cur = await conn.execute(
                """
                SELECT version
                FROM document_versions
                WHERE document_id = %s AND content_hash = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (metadata.document_id, content_hash),
            )
            duplicate = await cur.fetchone()
            if duplicate:
                raise DuplicateDocumentError(
                    f"DOCUMENT_ALREADY_INGESTED:{metadata.document_id}:v{duplicate[0]}"
                )

            cur = await conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM document_versions WHERE document_id = %s",
                (metadata.document_id,),
            )
            max_version = (await cur.fetchone())[0]
            version = metadata.version

            if version <= max_version:
                if version == 1 and max_version > 0:
                    version = max_version + 1
                else:
                    raise VersionConflictError(
                        f"VERSION_ALREADY_EXISTS:{metadata.document_id}:v{version}"
                    )

            cur = await conn.execute(
                """
                SELECT version
                FROM document_versions
                WHERE document_id = %s AND lifecycle_status = 'CURRENT'
                LIMIT 1
                """,
                (metadata.document_id,),
            )
            previous = await cur.fetchone()
            previous_version = previous[0] if previous else None
            supersedes = (
                f"{metadata.document_id}:v{previous_version}"
                if previous_version
                else metadata.supersedes
            )

            await conn.execute(
                """
                INSERT INTO document_versions (
                    document_id, version, source_file, content_hash,
                    source_system, title, author, classification, language,
                    tags, document_date, effective_from, effective_to,
                    lifecycle_status, parent_document_id, supersedes,
                    superseded_by, project_id, access_scope,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s, %s, %s, 'INGESTING', %s, %s,
                    NULL, %s, %s, %s, %s
                )
                """,
                (
                    metadata.document_id,
                    version,
                    source_file,
                    content_hash,
                    metadata.source_system,
                    metadata.title,
                    metadata.author,
                    metadata.classification,
                    metadata.language,
                    json.dumps(metadata.tags, ensure_ascii=False),
                    metadata.document_date,
                    metadata.effective_from,
                    metadata.effective_to,
                    metadata.parent_document_id,
                    supersedes,
                    metadata.project_id,
                    metadata.access_scope,
                    metadata.created_at,
                    metadata.updated_at,
                ),
            )

    return metadata.model_copy(
        update={
            "version": version,
            "lifecycle_status": LifecycleStatus.INGESTING,
            "supersedes": supersedes,
        }
    )


async def finalize_version(document_id: str, version: int) -> DocumentMetadata:
    async with await psycopg.AsyncConnection.connect(settings.metadata_database_url) as conn:
        async with conn.transaction():
            cur = await conn.execute(
                """
                SELECT *
                FROM document_versions
                WHERE document_id = %s AND version = %s
                FOR UPDATE
                """,
                (document_id, version),
            )
            current = await cur.fetchone()
            if not current:
                raise MetadataError("DOCUMENT_VERSION_NOT_FOUND")

            cur = await conn.execute(
                """
                SELECT version
                FROM document_versions
                WHERE document_id = %s
                  AND lifecycle_status = 'CURRENT'
                  AND version <> %s
                FOR UPDATE
                """,
                (document_id, version),
            )
            old_versions = await cur.fetchall()

            for (old_version,) in old_versions:
                await conn.execute(
                    """
                    UPDATE document_versions
                    SET lifecycle_status = 'SUPERSEDED',
                        superseded_by = %s,
                        updated_at = NOW()
                    WHERE document_id = %s AND version = %s
                    """,
                    (f"{document_id}:v{version}", document_id, old_version),
                )

            await conn.execute(
                """
                UPDATE document_versions
                SET lifecycle_status = 'CURRENT', updated_at = NOW()
                WHERE document_id = %s AND version = %s
                """,
                (document_id, version),
            )

            cur = await conn.execute(
                """
                SELECT *
                FROM document_versions
                WHERE document_id = %s AND version = %s
                """,
                (document_id, version),
            )
            row = await cur.fetchone()
            columns = [desc.name for desc in cur.description]
            data = dict(zip(columns, row))

    return DocumentMetadata(
        document_id=data["document_id"],
        source_system=data["source_system"],
        title=data["title"],
        author=data["author"],
        classification=data["classification"],
        created_at=data["created_at"].isoformat(),
        updated_at=data["updated_at"].isoformat(),
        tags=data["tags"] or [],
        language=data["language"],
        version=data["version"],
        document_date=data["document_date"].isoformat() if data["document_date"] else None,
        effective_from=data["effective_from"].isoformat() if data["effective_from"] else None,
        effective_to=data["effective_to"].isoformat() if data["effective_to"] else None,
        lifecycle_status=LifecycleStatus(data["lifecycle_status"]),
        parent_document_id=data["parent_document_id"],
        supersedes=data["supersedes"],
        project_id=data["project_id"],
        access_scope=data["access_scope"],
    )


async def fail_version(document_id: str, version: int) -> None:
    async with await psycopg.AsyncConnection.connect(settings.metadata_database_url) as conn:
        await conn.execute(
            """
            UPDATE document_versions
            SET lifecycle_status = 'ARCHIVED', updated_at = NOW()
            WHERE document_id = %s AND version = %s AND lifecycle_status = 'INGESTING'
            """,
            (document_id, version),
        )


async def list_versions(document_id: str) -> list[DocumentVersionResponse]:
    async with await psycopg.AsyncConnection.connect(
        settings.metadata_database_url, row_factory=dict_row
    ) as conn:
        cur = await conn.execute(
            """
            SELECT *
            FROM document_versions
            WHERE document_id = %s
            ORDER BY version DESC
            """,
            (document_id,),
        )
        rows = await cur.fetchall()
    return [_row_to_model(row) for row in rows]


async def get_version(document_id: str, version: int) -> DocumentVersionResponse | None:
    async with await psycopg.AsyncConnection.connect(
        settings.metadata_database_url, row_factory=dict_row
    ) as conn:
        cur = await conn.execute(
            """
            SELECT *
            FROM document_versions
            WHERE document_id = %s AND version = %s
            """,
            (document_id, version),
        )
        row = await cur.fetchone()
    return _row_to_model(row) if row else None
