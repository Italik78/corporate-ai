from pathlib import Path
import hashlib

def validate_filename(filename: str) -> str:
    name = Path(filename or "").name
    if not name or name in {".", ".."}:
        raise ValueError("INVALID_FILENAME")
    return name

def validate_size(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        raise ValueError("FILE_TOO_LARGE")

def validate_extension(filename: str, allowed: set[str]) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise ValueError("UNSUPPORTED_FILE_TYPE")
    return suffix

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def security_scan(data: bytes, suffix: str | None = None) -> list[str]:
    # Extension/size/path checks are implemented here. AV integration is a deployment hook.
    # NUL bytes are expected in binary document formats such as PDF, DOCX, XLSX and PPTX.
    warnings = []

    text_suffixes = {".txt", ".md", ".markdown", ".csv"}
    if suffix in text_suffixes and b"\x00" in data[:4096]:
        warnings.append("BINARY_NUL_DETECTED")

    return warnings
