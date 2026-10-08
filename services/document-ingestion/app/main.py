import secrets

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile

from .auth import ServicePrincipal, service_auth
from .config import settings
from .metadata import (
    find_current_versions,
    find_current_versions_by_source_file,
    get_version,
    health as metadata_health,
    initialize_metadata,
    list_versions,
    update_ingestion_jobs_for_version,
)
from .document_reference import DocumentReferenceStatus, resolve_document_reference
from .models import (
    DocumentProcessResponse,
    DocumentStatus,
    StatusResponse,
    StructuredQueryRequest,
    StructuredQueryResponse,
)
from .structured_query import StructuredQueryError, extract_xls_rows, query_xls_rows_with_count
from .pipeline import get_job, ingest_document
from .recovery import recover_ingesting_version
from .repository import RepositoryError, repository

app = FastAPI(title="Corporate AI Document Ingestion Service", version=settings.version)


def _authorize_recovery(supplied_token: str | None) -> None:
    configured = settings.recovery_token
    if not configured:
        raise HTTPException(status_code=503, detail="RECOVERY_NOT_CONFIGURED")
    if not supplied_token or not secrets.compare_digest(supplied_token, configured):
        raise HTTPException(status_code=401, detail="INVALID_RECOVERY_CREDENTIAL")


@app.on_event("startup")
async def startup() -> None:
    await initialize_metadata()


@app.get("/health")
async def health():
    from .knowledge_client import KnowledgeEngineClient

    ke = KnowledgeEngineClient()
    ke_ok = await ke.health()
    db_ok = await metadata_health()
    return {
        "status": "ok" if db_ok and ke_ok else "degraded",
        "service": settings.service_name,
        "version": settings.version,
        "knowledge_engine": ke_ok,
        "metadata_database": db_ok,
    }


@app.post("/v1/documents/ingest")
async def ingest(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    source_system: str = Form(default="upload"),
    source_reference: str | None = Form(default=None),
    version: int | None = Form(default=None),
    document_date: str | None = Form(default=None),
    effective_from: str | None = Form(default=None),
    effective_to: str | None = Form(default=None),
    project_id: str | None = Form(default=None),
    access_scope: str = Form(default="INTERNAL"),
    author: str | None = Form(default=None),
    classification: str = Form(default="INTERNAL"),
    tags: str | None = Form(default=None),
):
    tag_values = [x.strip() for x in (tags or "").split(",") if x.strip()]
    result = await ingest_document(
        filename=file.filename or "",
        data=None,
        document_id=document_id,
        source_system=source_system,
        source_reference=source_reference,
        version=version,
        document_date=document_date,
        effective_from=effective_from,
        effective_to=effective_to,
        project_id=project_id,
        access_scope=access_scope,
        author=author,
        classification=classification,
        tags=tag_values,
        upload=file,
    )
    if result.status.value.startswith("FAILED"):
        raise HTTPException(status_code=422, detail=result.model_dump())
    return result


@app.post("/v1/documents/process")
async def process_document(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    source_system: str = Form(default="open-webui"),
    source_reference: str | None = Form(default=None),
    version: int | None = Form(default=None),
    document_date: str | None = Form(default=None),
    effective_from: str | None = Form(default=None),
    effective_to: str | None = Form(default=None),
    project_id: str | None = Form(default=None),
    access_scope: str = Form(default="INTERNAL"),
    author: str | None = Form(default=None),
    classification: str = Form(default="INTERNAL"),
    tags: str | None = Form(default=None),
):
    tag_values = [x.strip() for x in (tags or "").split(",") if x.strip()]
    result = await ingest_document(
        filename=file.filename or "",
        data=None,
        document_id=document_id,
        source_system=source_system,
        source_reference=source_reference,
        version=version,
        document_date=document_date,
        effective_from=effective_from,
        effective_to=effective_to,
        project_id=project_id,
        access_scope=access_scope,
        author=author,
        classification=classification,
        tags=tag_values,
        upload=file,
        return_document=True,
    )
    if not isinstance(result, DocumentProcessResponse):
        raise HTTPException(status_code=422, detail="DOCUMENT_PROCESSING_FAILED")
    return result.model_dump()


@app.post("/v1/integrations/paperless/webhook")
async def paperless_webhook(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    document_date: str | None = Query(default=None),
    author: str | None = Query(default=None),
    classification: str = Query(default="INTERNAL"),
    access_scope: str = Query(default="INTERNAL"),
    tags: str | None = Query(default=None),
    x_corporate_ai_webhook: str | None = Header(default=None),
):
    configured_secret = settings.paperless_webhook_secret

    if not configured_secret:
        raise HTTPException(status_code=503, detail="PAPERLESS_WEBHOOK_NOT_CONFIGURED")

    if not x_corporate_ai_webhook or not secrets.compare_digest(
        x_corporate_ai_webhook,
        configured_secret,
    ):
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_SECRET")

    if not document_id:
        raise HTTPException(status_code=400, detail="PAPERLESS_DOCUMENT_ID_REQUIRED")

    tag_values = [x.strip() for x in (tags or "").split(",") if x.strip()]

    result = await ingest_document(
        filename=file.filename or "",
        data=None,
        document_id=f"paperless:{document_id}",
        source_system="paperless",
        source_reference=f"paperless:{document_id}",
        version=None,
        document_date=document_date,
        access_scope=access_scope,
        author=author,
        classification=classification,
        tags=tag_values,
        upload=file,
    )

    if result.status.value.startswith("FAILED"):
        raise HTTPException(status_code=422, detail=result.model_dump())

    return result


@app.post(
    "/v1/documents/structured-query",
    response_model=StructuredQueryResponse,
)
async def structured_query(
    request: StructuredQueryRequest,
    principal: ServicePrincipal = Depends(service_auth("structured_read")),
):
    if request.source_file is not None and (
        request.document_id is not None or request.version is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="DOCUMENT_REFERENCE_AMBIGUOUS",
        )

    if request.source_file is not None:
        matches = await find_current_versions_by_source_file(request.source_file)

        if not matches:
            raise HTTPException(
                status_code=404,
                detail="DOCUMENT_SOURCE_FILE_NOT_FOUND",
            )

        if len(matches) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "DOCUMENT_SOURCE_FILE_AMBIGUOUS",
                    "source_file": request.source_file,
                    "matches": [match.model_dump() for match in matches],
                },
            )

        metadata = matches[0]
    else:
        if request.document_id is None or request.version is None:
            raise HTTPException(
                status_code=422,
                detail="DOCUMENT_VERSION_REFERENCE_REQUIRED",
            )

        metadata = await get_version(request.document_id, request.version)

        if metadata is None:
            raise HTTPException(
                status_code=404,
                detail="DOCUMENT_VERSION_NOT_FOUND",
            )

    if metadata.lifecycle_status.value != "CURRENT":
        raise HTTPException(
            status_code=403,
            detail="STRUCTURED_QUERY_REQUIRES_CURRENT_VERSION",
        )

    if metadata.access_scope not in principal.access_scopes:
        raise HTTPException(
            status_code=403,
            detail="STRUCTURED_QUERY_ACCESS_SCOPE_DENIED",
        )

    if metadata.classification not in principal.classifications:
        raise HTTPException(
            status_code=403,
            detail="STRUCTURED_QUERY_CLASSIFICATION_DENIED",
        )

    if (
        metadata.project_id is not None
        and "*" not in principal.project_ids
        and metadata.project_id not in principal.project_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="STRUCTURED_QUERY_PROJECT_DENIED",
        )

    try:
        validated_metadata, data = (
            await repository.read_validated_canonical_source(
                metadata.document_id,
                metadata.version,
            )
        )
        rows = extract_xls_rows(validated_metadata.source_file, data)
        result, total_matches = query_xls_rows_with_count(
            rows,
            sheet=request.sheet,
            filters=request.filters,
            columns=request.columns,
            limit=request.limit,
        )
    except StructuredQueryError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except RepositoryError as exc:
        if str(exc) == "DOCUMENT_VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail="DOCUMENT_VERSION_NOT_FOUND",
            ) from exc

        raise HTTPException(
            status_code=503,
            detail="CANONICAL_SOURCE_UNAVAILABLE",
        ) from exc

    return StructuredQueryResponse(
        document_id=validated_metadata.document_id,
        version=validated_metadata.version,
        source_file=validated_metadata.source_file,
        content_hash=validated_metadata.content_hash,
        sheet=request.sheet,
        total_matches=total_matches,
        rows=result,
    )


@app.get("/v1/documents/resolve-by-source-file")
async def resolve_by_source_file(
    source_file: str,
    principal: ServicePrincipal = Depends(service_auth("structured_read")),
):
    documents = await find_current_versions()
    documents = [
        document
        for document in documents
        if document.access_scope in principal.access_scopes
        and document.classification in principal.classifications
        and (
            document.project_id is None
            or "*" in principal.project_ids
            or document.project_id in principal.project_ids
        )
    ]

    resolution = resolve_document_reference(source_file, documents)

    if resolution.status == DocumentReferenceStatus.NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail="DOCUMENT_SOURCE_FILE_NOT_FOUND",
        )

    if resolution.status == DocumentReferenceStatus.AMBIGUOUS:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DOCUMENT_SOURCE_FILE_AMBIGUOUS",
                "source_file": source_file,
                "matches": [
                    match.model_dump()
                    for match in resolution.matches
                ],
            },
        )

    return resolution.document


@app.get("/v1/documents/{document_id}/versions")
async def versions(document_id: str):
    return {"document_id": document_id, "versions": await list_versions(document_id)}


@app.get("/v1/documents/{document_id}/versions/{version}")
async def version_details(document_id: str, version: int):
    result = await get_version(document_id, version)
    if not result:
        raise HTTPException(status_code=404, detail="DOCUMENT_VERSION_NOT_FOUND")
    return result


@app.get("/v1/documents/{ingestion_id}/status", response_model=StatusResponse)
async def status(ingestion_id: str):
    job = await get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404, detail="INGEST_NOT_FOUND")
    return StatusResponse(**job)


@app.get("/v1/documents/{ingestion_id}")
async def details(ingestion_id: str):
    job = await get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404, detail="INGEST_NOT_FOUND")
    return {"ingestion_id": ingestion_id, **job}


@app.get("/v1/admin/reconciliation/documents/{document_id}/versions/{version}")
async def reconcile_version(
    document_id: str,
    version: int,
    x_corporate_ai_recovery: str | None = Header(default=None),
):
    _authorize_recovery(x_corporate_ai_recovery)
    try:
        result = await repository.inspect_version_integrity(document_id, version)
    except RepositoryError as exc:
        if str(exc) == "DOCUMENT_VERSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="DOCUMENT_VERSION_NOT_FOUND") from exc
        raise HTTPException(status_code=502, detail="RECONCILIATION_FAILED") from exc
    return {
        "document_id": result.document_id,
        "version": result.version,
        "lifecycle_status": result.lifecycle_status,
        "state": result.state.value,
        "reason": result.reason,
        "canonical_storage_key": result.canonical_storage_key,
        "candidate_storage_key": result.candidate_storage_key,
    }


@app.post("/v1/admin/reconciliation/documents/{document_id}/versions/{version}/repair-key")
async def repair_canonical_key(
    document_id: str,
    version: int,
    x_corporate_ai_recovery: str | None = Header(default=None),
):
    _authorize_recovery(x_corporate_ai_recovery)
    try:
        result = await repository.repair_missing_canonical_key(document_id, version)
    except RepositoryError as exc:
        if str(exc) == "DOCUMENT_VERSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="DOCUMENT_VERSION_NOT_FOUND") from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "document_id": result.document_id,
        "version": result.version,
        "state": result.state.value,
        "reason": result.reason,
        "canonical_storage_key": result.canonical_storage_key,
    }


@app.post("/v1/admin/recovery/documents/{document_id}/versions/{version}")
async def recover_version(
    document_id: str,
    version: int,
    x_corporate_ai_recovery: str | None = Header(default=None),
):
    _authorize_recovery(x_corporate_ai_recovery)
    try:
        return await recover_ingesting_version(document_id, version)
    except RepositoryError as exc:
        if str(exc) == "DOCUMENT_VERSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="DOCUMENT_VERSION_NOT_FOUND") from exc
        try:
            await update_ingestion_jobs_for_version(
                document_id,
                version,
                status=DocumentStatus.FAILED_INDEXING.value,
                error_code="RECOVERY_SOURCE_INVALID",
                error=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        try:
            await update_ingestion_jobs_for_version(
                document_id,
                version,
                status=DocumentStatus.FAILED_INDEXING.value,
                error_code="RECOVERY_FAILED",
                error=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="RECOVERY_FAILED") from exc
