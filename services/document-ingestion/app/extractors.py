from pathlib import Path
from .models import NormalizedBlock

def extract_text(filename: str, data: bytes) -> list[NormalizedBlock]:
    suffix=Path(filename).suffix.lower()
    encoding="utf-8"
    try:
        text=data.decode(encoding)
    except UnicodeDecodeError:
        text=data.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return []
    blocks=[]
    section=None
    counter=0
    for raw in text.splitlines():
        line=raw.strip()
        if not line:
            continue
        if suffix in {".md",".markdown"} and line.startswith("#"):
            section=line.lstrip("#").strip()
            counter+=1
            blocks.append(NormalizedBlock(
                block_id=f"b-{counter:06d}", block_type="heading",
                content=section, section=section,
                provenance={"line": counter, "source_format":"markdown"}))
            continue
        counter+=1
        blocks.append(NormalizedBlock(
            block_id=f"b-{counter:06d}", content=line, section=section,
            provenance={"line": counter, "source_format":"text"}))
    return blocks
