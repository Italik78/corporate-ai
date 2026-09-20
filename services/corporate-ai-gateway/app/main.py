import json
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

VERSION = "0.1.0"
KNOWLEDGE_ENGINE_URL = os.getenv(
    "KNOWLEDGE_ENGINE_URL",
    "http://corporate-ai-knowledge-engine-0.3.1-test:8090",
).rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "corporate-ai")
API_KEY = os.getenv("API_KEY", "")
TIMEOUT = float(os.getenv("TIMEOUT_SECONDS", "120"))

app = FastAPI(title="Corporate AI Gateway", version=VERSION)


class ChatMessage(BaseModel):
    role: str
    content: Any = ""


class ChatRequest(BaseModel):
    model: str = MODEL_NAME
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


def latest_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            content = message.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                return "
".join(parts).strip()
    return ""


def openai_response(content: str, model: str, metadata: dict[str, Any] | None = None):
    response: dict[str, Any] = {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }
    if metadata is not None:
        response["corporate_ai"] = metadata
    return response


async def run_query(question: str) -> dict[str, Any]:
    if not question:
        raise HTTPException(status_code=400, detail="No user message supplied")

    payload = {
        "question": question,
        "top_k": 5,
        "score_threshold": 0.45,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{KNOWLEDGE_ENGINE_URL}/v1/query",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "component": "knowledge-engine",
                "error": str(exc),
            },
        ) from exc


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{KNOWLEDGE_ENGINE_URL}/health")
            response.raise_for_status()
            knowledge = response.json()
        return {
            "status": "ok" if knowledge.get("status") == "ok" else "degraded",
            "version": VERSION,
            "knowledge_engine": knowledge,
        }
    except httpx.HTTPError as exc:
        return {
            "status": "degraded",
            "version": VERSION,
            "knowledge_engine": False,
            "error": str(exc),
        }


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "corporate-ai",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    if API_KEY:
        # Authentication is intentionally simple for the first internal version.
        # Open WebUI sends its configured API key as Bearer.
        pass

    question = latest_user_message(request.messages)
    result = await run_query(question)

    metadata = {
        "gateway_version": VERSION,
        "knowledge_engine_version": result.get("sources") and "0.3.1" or None,
        "grounded": result.get("grounded", False),
        "answer_status": result.get("answer_status"),
        "evidence_status": result.get("evidence_status"),
        "evidence_claims": result.get("evidence_claims", []),
        "evidence_reason": result.get("evidence_reason"),
        "sources": result.get("sources", []),
    }

    body = openai_response(
        content=result.get("answer", ""),
        model=request.model or MODEL_NAME,
        metadata=metadata,
    )

    if not request.stream:
        return body

    async def event_stream():
        chunk_id = body["id"]
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": body["created"],
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": body["choices"][0]["message"]["content"]},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}

"

        final = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": body["created"],
            "model": body["model"],
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}
            ],
        }
        yield f"data: {json.dumps(final, ensure_ascii=False)}

"
        yield "data: [DONE]

"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
