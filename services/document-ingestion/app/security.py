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

def sha256_file(path, chunk_size: int = 1024 * 1024) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file_size(path, max_bytes: int, chunk_size: int = 1024 * 1024) -> int:
    import os

    size = os.path.getsize(path)
    if size > max_bytes:
        raise ValueError("FILE_TOO_LARGE")
    return size


def security_scan_file(path, suffix: str, chunk_size: int = 1024 * 1024) -> list[str]:
    warnings: list[str] = []
    if suffix in {".txt", ".md", ".markdown", ".csv"}:
        with open(path, "rb") as handle:
            while chunk := handle.read(chunk_size):
                if b"\x00" in chunk:
                    raise ValueError("MALFORMED_TEXT_FILE")
    return warnings


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
