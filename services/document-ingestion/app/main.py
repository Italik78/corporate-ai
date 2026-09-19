from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from .config import settings
from .models import StatusResponse
from .pipeline import ingest_document, get_job

app=FastAPI(title="Corporate AI Document Ingestion Service",version=settings.version)

@app.get("/health")
async def health():
    from .knowledge_client import KnowledgeEngineClient
    ke=KnowledgeEngineClient()
    return {"status":"ok","service":settings.service_name,"version":settings.version,
            "knowledge_engine":await ke.health()}

@app.post("/v1/documents/ingest")
async def ingest(file: UploadFile=File(...), document_id: str|None=Form(default=None), source_system: str=Form(default="upload")):
    data=await file.read()
    result=await ingest_document(file.filename or "",data,document_id,source_system)
    if result.status.value.startswith("FAILED"):
        raise HTTPException(status_code=422,detail=result.model_dump())
    return result

@app.get("/v1/documents/{ingestion_id}/status",response_model=StatusResponse)
async def status(ingestion_id: str):
    job=get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404,detail="INGESTION_NOT_FOUND")
    return StatusResponse(ingestion_id=ingestion_id,**job)

@app.get("/v1/documents/{ingestion_id}")
async def details(ingestion_id: str):
    job=get_job(ingestion_id)
    if not job:
        raise HTTPException(status_code=404,detail="INGESTION_NOT_FOUND")
    return {"ingestion_id":ingestion_id,**job}
