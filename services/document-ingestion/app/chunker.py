"""Deterministic, structure-aware chunking for normalized documents."""

import re

from .models import Chunk, NormalizedBlock, NormalizedDocument


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def chunk_document(
    doc: NormalizedDocument,
    target_words: int = 180,
    overlap_words: int = 30,
) -> list[Chunk]:
    """Create bounded chunks while preserving block provenance."""
    if target_words <= 0:
        raise ValueError("target_words must be positive")
    if overlap_words < 0 or overlap_words >= target_words:
        raise ValueError("overlap_words must be >= 0 and < target_words")

    chunks: list[Chunk] = []
    current_words: list[str] = []
    current_blocks: list[NormalizedBlock] = []
    block_words: dict[str, list[str]] = {}
    idx = 0

    for block in doc.blocks:
        words = _words(block.content)
        if not words:
            continue

        block_words[block.block_id] = words

        if current_words and len(current_words) + len(words) > target_words:
            idx += 1
            chunks.append(_make(doc, idx, current_words, current_blocks))
            current_words, current_blocks = _overlap(
                current_words, current_blocks, overlap_words, block_words
            )

        start = 0
        while start < len(words):
            room = target_words - len(current_words)
            take = min(room, len(words) - start)
            current_words.extend(words[start:start + take])
            current_blocks.append(block)
            start += take

            if len(current_words) == target_words and start < len(words):
                idx += 1
                chunks.append(_make(doc, idx, current_words, current_blocks))
                current_words, current_blocks = _overlap(
                    current_words, current_blocks, overlap_words, block_words
                )

    if current_words:
        idx += 1
        chunks.append(_make(doc, idx, current_words, current_blocks))

    return chunks


def _overlap(
    words: list[str],
    blocks: list[NormalizedBlock],
    overlap_words: int,
    block_words: dict[str, list[str]],
) -> tuple[list[str], list[NormalizedBlock]]:
    if not overlap_words:
        return [], []

    trailing = words[-overlap_words:]
    remaining = len(trailing)
    selected: list[NormalizedBlock] = []

    for block in reversed(blocks):
        block_size = len(block_words.get(block.block_id, _words(block.content)))
        if block_size:
            selected.append(block)
            remaining -= block_size
        if remaining <= 0:
            break

    return trailing, list(reversed(selected))


def _make(
    doc: NormalizedDocument,
    idx: int,
    words: list[str],
    blocks: list[NormalizedBlock],
) -> Chunk:
    first = blocks[0]
    last = blocks[-1]
    confidence = min((b.confidence for b in blocks), default=1.0)

    return Chunk(
        chunk_id=f"{doc.document_id}:chunk:{idx:05d}",
        document_id=doc.document_id,
        source_file=doc.source_file,
        page=first.page,
        page_type="TEXT",
        chunk_type="text",
        section=first.section,
        confidence=confidence,
        content=" ".join(words),
        provenance={
            "block_ids": list(dict.fromkeys(b.block_id for b in blocks)),
            "first_block": first.block_id,
            "last_block": last.block_id,
            "content_hash": doc.content_hash,
        },
    )
