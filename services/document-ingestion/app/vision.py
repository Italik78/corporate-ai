import base64
import json
import re
from pathlib import Path
from typing import Any

import fitz
import httpx

from .config import settings


VISION_PROMPT = """Анализирай изображението на страницата на документ.

Върни САМО валиден JSON без markdown и без допълнителен текст.

Схема:
{
  "page_type": "TEXT|TABLE|VISUAL|COMPLEX",
  "title": null,
  "text": "",
  "tables": [],
  "key_values": [],
  "entities": [],
  "visual_elements": [],
  "uncertain_items": [],
  "confidence": 0.0
}

Правила:
- Не измисляй липсващ или нечетлив текст.
- Ако нещо не е ясно, не го отгатвай; добави го в uncertain_items.
- Запази числата, датите, имената и стойностите точно както са видими.
- За таблици използвай обект с "headers" и "rows".
- Всяка row трябва да има точно същия брой елементи като headers.
- При липсваща или нечетлива клетка използвай null.
- Отговорът трябва да е кратък и структуриран.
"""


class VisionError(ValueError):
    """Base error for PDF Vision processing."""


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VisionError("PDF_VISION_INVALID_JSON") from exc

    if not isinstance(value, dict):
        raise VisionError("PDF_VISION_INVALID_JSON")

    required = {
        "page_type",
        "title",
        "text",
        "tables",
        "key_values",
        "entities",
        "visual_elements",
        "uncertain_items",
        "confidence",
    }
    if not required.issubset(value):
        raise VisionError("PDF_VISION_INVALID_SCHEMA")

    try:
        confidence = float(value["confidence"])
    except (TypeError, ValueError) as exc:
        raise VisionError("PDF_VISION_INVALID_SCHEMA") from exc

    if not 0.0 <= confidence <= 1.0:
        raise VisionError("PDF_VISION_INVALID_SCHEMA")

    if not isinstance(value["text"], str):
        raise VisionError("PDF_VISION_INVALID_SCHEMA")

    if not isinstance(value["tables"], list):
        raise VisionError("PDF_VISION_INVALID_SCHEMA")

    return value


def _render_page(document: fitz.Document, page_number: int, dpi: int) -> bytes:
    try:
        page = document.load_page(page_number - 1)
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    except Exception as exc:
        raise VisionError("PDF_VISION_RENDER_ERROR") from exc


async def analyze_pdf_page(
    pdf_path: str | Path,
    page_number: int,
) -> dict[str, Any]:
    path = Path(pdf_path)

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        raise VisionError("PDF_VISION_PDF_OPEN_ERROR") from exc

    try:
        if page_number < 1 or page_number > document.page_count:
            raise VisionError("PDF_VISION_PAGE_OUT_OF_RANGE")

        image_bytes = _render_page(
            document,
            page_number,
            settings.vision_render_dpi,
        )
    finally:
        document.close()

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{image_b64}"

    payload = {
        "model": settings.vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    url = f"{settings.vision_base_url.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(
            timeout=settings.vision_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException as exc:
        raise VisionError("PDF_VISION_TIMEOUT") from exc
    except httpx.HTTPError as exc:
        raise VisionError("PDF_VISION_HTTP_ERROR") from exc
    except ValueError as exc:
        raise VisionError("PDF_VISION_INVALID_RESPONSE") from exc

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise VisionError("PDF_VISION_INVALID_RESPONSE") from exc

    if not isinstance(content, str) or not content.strip():
        raise VisionError("PDF_VISION_EMPTY_RESPONSE")

    return _extract_json(content)


async def analyze_sparse_pdf_pages(
    pdf_path: str | Path,
    native_blocks: list[Any],
) -> list[dict[str, Any]]:
    path = Path(pdf_path)

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        raise VisionError("PDF_VISION_PDF_OPEN_ERROR") from exc

    try:
        native_chars_by_page: dict[int, int] = {}
        for block in native_blocks:
            if block.page is None:
                continue
            native_chars_by_page[block.page] = (
                native_chars_by_page.get(block.page, 0)
                + len(block.content.strip())
            )

        candidates: list[int] = []
        for page_number in range(1, document.page_count + 1):
            native_chars = native_chars_by_page.get(page_number, 0)
            if native_chars >= settings.vision_min_native_text_chars:
                continue

            page = document.load_page(page_number - 1)
            if page.get_images(full=True) or native_chars == 0:
                candidates.append(page_number)
    finally:
        document.close()

    results: list[dict[str, Any]] = []
    for page_number in candidates:
        result = await analyze_pdf_page(path, page_number)
        result["_page"] = page_number
        results.append(result)

    return results
