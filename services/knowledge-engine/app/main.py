import hashlib
import os

from fastapi import FastAPI, HTTPException

from app.claims import ClaimsEngine
from app.embedding import EmbeddingClient
from app.evidence import EvidenceEngine, EvidenceStatus
from app.llm import LLMClient
from app.models import (
    AnswerStatus,
    EvidenceStatus as APIEvidenceStatus,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    RAGQuery,
    RAGResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    Source,
)
from app.partial import PartialAnswerEngine
from app.qdrant import QdrantStore
from app.rag import NO_ANSWER, build_messages, parse_decision

VERSION = "0.3.1"

EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    "http://corporate-ai-embedding-test:8001/v1",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding-4b")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "http://corporate-ai-qwen36:8000/v1",
)
LLM_MODEL = os.getenv("LLM_MODEL", "qwen36")
QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://corporate-ai-qdrant:6333",
)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "corporate_knowledge")

app = FastAPI(title="Corporate AI Knowledge Engine", version=VERSION)

qdrant = QdrantStore(url=QDRANT_URL, collection=COLLECTION_NAME)
embedding = EmbeddingClient(base_url=EMBEDDING_BASE_URL, model=EMBEDDING_MODEL)
llm = LLMClient(base_url=LLM_BASE_URL, model=LLM_MODEL)
evidence = EvidenceEngine()
claims_engine = ClaimsEngine()
partial_engine = PartialAnswerEngine()


@app.get("/health", response_model=HealthResponse)
async def health():
    qdrant_ok = False
    embedding_ok = False
    llm_ok = False

    try:
        qdrant_ok = qdrant.health()
    except Exception:
        pass

    try:
        embedding_ok = await embedding.health()
    except Exception:
        pass

    try:
        llm_ok = await llm.health()
    except Exception:
        pass

    status = "ok" if qdrant_ok and embedding_ok and llm_ok else "degraded"

    return HealthResponse(
        status=status,
        qdrant=qdrant_ok,
        embedding=embedding_ok,
        llm=llm_ok,
        collection=qdrant.collection,
        embedding_model=embedding.model,
        llm_model=llm.model,
        version=VERSION,
    )


@app.post("/v1/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    content = request.content.strip()

    identity = (
        f"{request.document_id}:{request.chunk_id}"
        if request.chunk_id
        else f"{request.document_id}:{request.source_file}:{request.page}:{content}"
    )
    point_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]

    payload = {
        "document_id": request.document_id,
        "source_file": request.source_file,
        "version": request.version,
        "lifecycle_status": request.lifecycle_status,
        "document_date": request.document_date,
        "effective_from": request.effective_from,
        "effective_to": request.effective_to,
        "project_id": request.project_id,
        "access_scope": request.access_scope,
        "page": request.page,
        "page_type": request.page_type,
        "chunk_type": request.chunk_type,
        "chunk_id": request.chunk_id,
        "section": request.section,
        "confidence": request.confidence,
        "content": content,
        "content_hash": hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
    }

    try:
        vector = await embedding.embed(content)
        qdrant.upsert(
            point_id=point_id,
            vector=vector,
            payload=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"component": "knowledge-engine", "error": str(exc)},
        ) from exc

    return IngestResponse(
        status="ok",
        point_id=point_id,
        vector_dimensions=len(vector),
    )


@app.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        query = request.query.strip()
        vector = await embedding.embed(query)
        results = qdrant.search(
            vector=vector,
            limit=request.top_k,
            score_threshold=request.score_threshold,
            document_id=request.document_id,
            version=request.version,
            lifecycle_status=request.lifecycle_status,
        )

        output = []
        for result in results:
            payload = result.payload or {}
            output.append(
                SearchResult(
                    score=float(result.score),
                    document_id=payload.get("document_id"),
                    source_file=payload.get("source_file"),
                    version=payload.get("version"),
                    lifecycle_status=payload.get("lifecycle_status"),
                    document_date=payload.get("document_date"),
                    effective_from=payload.get("effective_from"),
                    effective_to=payload.get("effective_to"),
                    project_id=payload.get("project_id"),
                    access_scope=payload.get("access_scope"),
                    page=payload.get("page"),
                    page_type=payload.get("page_type"),
                    chunk_type=payload.get("chunk_type"),
                    section=payload.get("section"),
                    confidence=payload.get("confidence"),
                    chunk_id=payload.get("chunk_id"),
                    content=payload.get("content", ""),
                )
            )

        return SearchResponse(query=query, results=output)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"component": "knowledge-engine", "error": str(exc)},
        ) from exc


@app.post("/v1/query", response_model=RAGResponse)
async def query(request: RAGQuery):
    question = request.question.strip()

    try:
        vector = await embedding.embed(question)
        results = qdrant.search(
            vector=vector,
            limit=request.top_k,
            score_threshold=request.score_threshold,
            document_id=request.document_id,
            version=request.version,
            lifecycle_status=request.lifecycle_status,
        )

        if not results:
            return RAGResponse(
                question=question,
                answer=NO_ANSWER,
                grounded=False,
                answer_status=AnswerStatus.NO_ANSWER,
                evidence_status=APIEvidenceStatus.INSUFFICIENT_EVIDENCE,
                evidence_claims=[],
                evidence_reason="Няма намерени доказателства.",
                claims=[],
                sources=[],
            )

        search_results = []
        for result in results:
            payload = result.payload or {}
            search_results.append(
                SearchResult(
                    score=float(result.score),
                    document_id=payload.get("document_id"),
                    source_file=payload.get("source_file"),
                    version=payload.get("version"),
                    lifecycle_status=payload.get("lifecycle_status"),
                    document_date=payload.get("document_date"),
                    effective_from=payload.get("effective_from"),
                    effective_to=payload.get("effective_to"),
                    project_id=payload.get("project_id"),
                    access_scope=payload.get("access_scope"),
                    page=payload.get("page"),
                    page_type=payload.get("page_type"),
                    chunk_type=payload.get("chunk_type"),
                    section=payload.get("section"),
                    confidence=payload.get("confidence"),
                    chunk_id=payload.get("chunk_id"),
                    content=payload.get("content", ""),
                )
            )

        evidence_result = evidence.evaluate(
            question=question,
            results=search_results,
        )

        if evidence_result.status == EvidenceStatus.CONFLICT:
            sources = []
            for source_id in evidence_result.source_ids:
                result = search_results[source_id - 1]
                sources.append(
                    Source(
                        document_id=result.document_id,
                        source_file=result.source_file,
                        page=result.page,
                        chunk_id=result.chunk_id,
                        score=result.score,
                        content=result.content,
                    )
                )

            return RAGResponse(
                question=question,
                answer=(
                    "В предоставените документи има противоречива информация. "
                    "Не е избран източник като верен."
                ),
                grounded=False,
                answer_status=AnswerStatus.NO_ANSWER,
                evidence_status=APIEvidenceStatus.CONFLICT,
                evidence_claims=evidence_result.claims,
                evidence_reason=evidence_result.reason,
                claims=[],
                sources=sources,
            )

        messages = build_messages(
            question=question,
            results=search_results,
        )

        llm_content = await llm.chat(
            messages=messages,
            temperature=0.0,
            max_tokens=1024,
        )
        decision = parse_decision(llm_content)

        valid_source_ids = set(range(1, len(search_results) + 1))
        selected_source_ids = [
            source_id
            for source_id in decision["source_ids"]
            if (
                isinstance(source_id, int)
                and not isinstance(source_id, bool)
                and source_id in valid_source_ids
            )
        ]
        selected_source_ids = list(dict.fromkeys(selected_source_ids))

        claims = claims_engine.build(
            decision=decision,
            retrieved_sources=search_results,
        )
        partial_result = partial_engine.build(
            decision=decision,
            claims=claims,
        )

        source_ids_for_output = set(selected_source_ids)
        for claim in claims:
            for source_id in claim.source_ids:
                source_ids_for_output.add(source_id)

        sources = []
        for source_id in sorted(source_ids_for_output):
            result = search_results[source_id - 1]
            sources.append(
                Source(
                    document_id=result.document_id,
                    source_file=result.source_file,
                    page=result.page,
                    chunk_id=result.chunk_id,
                    score=result.score,
                    content=result.content,
                )
            )

        supported_claims = [
            claim for claim in claims if claim.supported
        ]
        all_claims_supported = (
            len(claims) > 0
            and len(supported_claims) == len(claims)
        )

        if partial_result.status == AnswerStatus.NO_ANSWER:
            return RAGResponse(
                question=question,
                answer=NO_ANSWER,
                grounded=False,
                answer_status=AnswerStatus.NO_ANSWER,
                evidence_status=APIEvidenceStatus.INSUFFICIENT_EVIDENCE,
                evidence_claims=evidence_result.claims,
                evidence_reason=(
                    "Няма достатъчно подкрепени твърдения "
                    "за изграждане на отговор."
                ),
                claims=[],
                sources=[],
            )

        if partial_result.status == AnswerStatus.PARTIAL:
            return RAGResponse(
                question=question,
                answer=partial_result.answer,
                grounded=False,
                answer_status=AnswerStatus.PARTIAL,
                evidence_status=APIEvidenceStatus.SUPPORTED,
                evidence_claims=evidence_result.claims,
                evidence_reason=(
                    "Отговорът съдържа само подкрепената "
                    "част от информацията."
                ),
                claims=claims,
                sources=sources,
            )

        grounded = (
            decision["answerable"]
            and len(selected_source_ids) > 0
            and all_claims_supported
        )

        if not grounded:
            return RAGResponse(
                question=question,
                answer=NO_ANSWER,
                grounded=False,
                answer_status=AnswerStatus.NO_ANSWER,
                evidence_status=APIEvidenceStatus.INSUFFICIENT_EVIDENCE,
                evidence_claims=evidence_result.claims,
                evidence_reason=(
                    "LLM отговорът не разполага с достатъчно "
                    "валидно provenance покритие."
                ),
                claims=[],
                sources=[],
            )

        return RAGResponse(
            question=question,
            answer=partial_result.answer,
            grounded=True,
            answer_status=AnswerStatus.FULL,
            evidence_status=APIEvidenceStatus.SUPPORTED,
            evidence_claims=evidence_result.claims,
            evidence_reason=evidence_result.reason,
            claims=claims,
            sources=sources,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"component": "knowledge-engine", "error": str(exc)},
        ) from exc
