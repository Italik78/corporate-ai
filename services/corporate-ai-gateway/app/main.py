import json
import os
import re
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

VERSION = "0.2.0"
KNOWLEDGE_ENGINE_URL = os.getenv(
    "KNOWLEDGE_ENGINE_URL",
    "http://corporate-ai-knowledge-engine-0.3.1-test:8090",
).rstrip("/")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "http://corporate-ai-qwen36:8000/v1").rstrip("/")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen36")
MODEL_NAME = os.getenv("MODEL_NAME", "corporate-ai")
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
        if message.role != "user":
            continue
        content = message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(parts).strip()
    return ""


def messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def openai_response(content: str, model: str, metadata: dict[str, Any]):
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "corporate_ai": metadata,
    }


def extract_qwen_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Invalid Qwen response")
    return content if isinstance(content, str) else str(content)


async def qwen_chat(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": QWEN_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{QWEN_BASE_URL}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return extract_qwen_content(response.json())
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={"component": "qwen", "error": str(exc)},
        ) from exc


def heuristic_route(question: str) -> str | None:
    q = question.casefold()

    rag_terms = (
        "дневни командировъчни",
        "командировъчни",
        "вътрешна политика",
        "вътрешните правила",
        "наша политика",
        "нашата политика",
        "предоставените документи",
        "предоставените данни",
        "в документа",
        "в документите",
        "според документа",
        "според документите",
        "според вътрешните",
        "процедура за закупуване",
        "процедура за покупка",
        "служителите",
        "фактура",
        "нашата организация",
        "в нашата организация",
        "в компанията",
        "нашата компания",
    )
    if any(term in q for term in rag_terms):
        return "rag"

    return None


async def classify_route(question: str) -> tuple[str, str]:
    heuristic = heuristic_route(question)
    if heuristic:
        return heuristic, "deterministic_domain_match"

    router_prompt = """You are the routing controller for a corporate AI assistant.
Choose exactly one route for the user's question:
- GENERAL: answer from the model's general knowledge/reasoning; no company documents are required.
- RAG: the answer depends on company-internal information, provided documents, internal policies, procedures, records, or other knowledge-base facts.

Rules:
- If the user asks about internal/company-specific facts, policies, procedures, documents, employees, expenses, procurement requirements, or stored records, choose RAG.
- If the user asks a general conceptual, educational, mathematical, writing, brainstorming, or coding question with no company-specific dependency, choose GENERAL.
- When uncertain between GENERAL and RAG, choose RAG.
Return ONLY valid JSON: {"route":"GENERAL"} or {"route":"RAG"}.
"""
    raw = await qwen_chat(
        [
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=40,
    )
    try:
        match = re.search(r"\{\s*"route"\s*:\s*"(GENERAL|RAG)"\s*\}", raw.upper())
        if match:
            return match.group(1).lower(), "llm_router"
    except Exception:
        pass

    # Fail closed toward evidence for ambiguous routing.
    return "rag", "router_fallback"


async def run_query(question: str) -> dict[str, Any]:
    if not question:
        raise HTTPException(status_code=400, detail="No user message supplied")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{KNOWLEDGE_ENGINE_URL}/v1/query",
                json={"question": question, "top_k": 5, "score_threshold": 0.45},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={"component": "knowledge-engine", "error": str(exc)},
        ) from exc


def metadata_from_rag(result: dict[str, Any], route_reason: str) -> dict[str, Any]:
    return {
        "gateway_version": VERSION,
        "route": "rag",
        "route_reason": route_reason,
        "grounded": result.get("grounded", False),
        "answer_status": result.get("answer_status"),
        "evidence_status": result.get("evidence_status"),
        "evidence_claims": result.get("evidence_claims", []),
        "evidence_reason": result.get("evidence_reason"),
        "sources": result.get("sources", []),
    }


@app.get("/health")
async def health():
    knowledge_ok = False
    knowledge: Any = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{KNOWLEDGE_ENGINE_URL}/health")
            response.raise_for_status()
            knowledge = response.json()
            knowledge_ok = knowledge.get("status") == "ok"
    except httpx.HTTPError:
        pass

    qwen_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{QWEN_BASE_URL}/models")
            response.raise_for_status()
            qwen_ok = True
    except httpx.HTTPError:
        pass

    return {
        "status": "ok" if knowledge_ok and qwen_ok else "degraded",
        "version": VERSION,
        "knowledge_engine": knowledge,
        "qwen": qwen_ok,
    }


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [{
            "id": MODEL_NAME,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "corporate-ai",
        }],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    question = latest_user_message(request.messages)
    if not question:
        raise HTTPException(status_code=400, detail="No user message supplied")

    route, route_reason = await classify_route(question)

    if route == "general":
        system = (
            "You are the Corporate AI assistant. Answer the user's question directly "
            "using your general knowledge and reasoning. Do not claim to have consulted "
            "company documents unless they were actually provided through the knowledge route. "
            "Do not invent company-specific facts."
        )
        qwen_messages = [{"role": "system", "content": system}] + messages_to_openai(request.messages)
        answer = await qwen_chat(
            qwen_messages,
            temperature=request.temperature if request.temperature is not None else 0.2,
            max_tokens=request.max_tokens,
        )
        metadata = {
            "gateway_version": VERSION,
            "route": "general",
            "route_reason": route_reason,
            "grounded": False,
            "answer_status": "GENERAL",
            "evidence_status": "NOT_REQUIRED",
            "evidence_claims": [],
            "evidence_reason": None,
            "sources": [],
        }
    else:
        result = await run_query(question)
        answer = result.get("answer", "")
        metadata = metadata_from_rag(result, route_reason)

    body = openai_response(answer, request.model or MODEL_NAME, metadata)

    if not request.stream:
        return body

    async def event_stream():
        chunk_id = body["id"]
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": body["created"],
            "model": body["model"],
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": body["choices"][0]["message"]["content"],
                },
                "finish_reason": None,
            }],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        final = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": body["created"],
            "model": body["model"],
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
