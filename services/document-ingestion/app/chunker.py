import re
from .models import Chunk, NormalizedDocument

def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)

def chunk_document(doc: NormalizedDocument, target_words: int=180, overlap_words: int=30) -> list[Chunk]:
    chunks=[]
    current=[]
    current_blocks=[]
    idx=0
    for block in doc.blocks:
        words=_words(block.content)
        if not words:
            continue
        if current and len(current)+len(words)>target_words:
            idx+=1
            chunks.append(_make(doc, idx, current, current_blocks))
            current=current[-overlap_words:] if overlap_words else []
            current_blocks=current_blocks[-1:] if overlap_words else []
        current.extend(words)
        current_blocks.append(block)
    if current:
        idx+=1
        chunks.append(_make(doc, idx, current, current_blocks))
    return chunks

def _make(doc, idx, words, blocks):
    first=blocks[0]
    last=blocks[-1]
    confidence=min((b.confidence for b in blocks), default=1.0)
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
            "block_ids":[b.block_id for b in blocks],
            "first_block":first.block_id,
            "last_block":last.block_id,
            "content_hash":doc.content_hash,
        },
    )
