from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .config import settings
from .metadata import (
    get_version,
    health as metadata_health,
    initialize_metadata,
    list_versions,
)
from .models import StatusResponse
from .pipeline import get_job, ingest_document

app = FastAPI(title="Corporate AI Document Ingestion Service", version=settings.version)


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
    data = await file.read()
    tag_values = [x.strip() for x in (tags or "").split(",") if x.strip()]
    result = await ingest_document(
        file.filename or "",
        data,
        document_id,
        source_system,
        version,
        document_date,
        effective_from,
        effective_to,
        project_id,
        access_scope,
        author,
        classification,
        tag_values,
    )
    if result.status.value.startswith("FAILED"):
        raise HTTPException(status_code=422, detail=result.model_dump())
    return result


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
    job = get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404, detail="INGEST_NOT_FOUND")
    return StatusResponse(ingestion_id=ingestion_id, **job)


@app.get("/v1/documents/{ingestion_id}")
async def details(ingestion_id: str):
    job = get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404, detail="INGEST_NOT_FOUND")
    return {"ingestion_id": ingestion_id, **job}
