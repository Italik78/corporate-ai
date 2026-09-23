from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .config import settings


class CanonicalStorageError(RuntimeError):
    """Raised when canonical source storage cannot safely complete."""


class FilesystemCanonicalStorage:
    """Filesystem-backed canonical source storage.

    The root directory is expected to be a dedicated writable mount. Source
    objects are stored below documents/{document_id}/original/{version}/.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.repository_storage_path).resolve()

    @staticmethod
    def _safe_component(value: str, field: str) -> str:
        if not value or value in {".", ".."}:
            raise CanonicalStorageError(f"INVALID_{field.upper()}")
        if "/" in value or "\\" in value or "\x00" in value:
            raise CanonicalStorageError(f"INVALID_{field.upper()}")
        if any(ord(char) < 32 for char in value):
            raise CanonicalStorageError(f"INVALID_{field.upper()}")
        return value

    def _source_path(self, document_id: str, version: int, filename: str) -> Path:
        if version < 1:
            raise CanonicalStorageError("INVALID_VERSION")
        safe_document_id = self._safe_component(document_id, "document_id")
        safe_filename = self._safe_component(Path(filename).name, "filename")
        if Path(filename).name != filename:
            raise CanonicalStorageError("INVALID_FILENAME")

        path = (
            self.root
            / "documents"
            / safe_document_id
            / "original"
            / str(version)
            / safe_filename
        ).resolve()

        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise CanonicalStorageError("INVALID_STORAGE_PATH") from exc
        return path

    def store(
        self,
        document_id: str,
        version: int,
        filename: str,
        data: bytes,
        content_hash: str,
    ) -> str:
        actual_hash = hashlib.sha256(data).hexdigest()
        expected_hash = content_hash.removeprefix("sha256:")
        if actual_hash != expected_hash:
            raise CanonicalStorageError("CONTENT_HASH_MISMATCH")

        path = self._source_path(document_id, version, filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise CanonicalStorageError("CANONICAL_STORAGE_WRITE_FAILED") from exc

        return str(path.relative_to(self.root))

    def read(self, document_id: str, version: int, filename: str) -> bytes:
        path = self._source_path(document_id, version, filename)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise CanonicalStorageError("CANONICAL_SOURCE_NOT_FOUND") from exc

    def delete(self, document_id: str, version: int, filename: str) -> None:
        path = self._source_path(document_id, version, filename)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise CanonicalStorageError("CANONICAL_STORAGE_DELETE_FAILED") from exc
