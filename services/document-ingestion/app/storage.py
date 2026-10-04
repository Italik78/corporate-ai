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
    def _sync_parent(path: Path) -> None:
        """Persist the rename's directory entry on filesystems that support it."""
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

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

    def expected_key(self, document_id: str, version: int, filename: str) -> str:
        """Return the adapter's canonical relative key after path validation."""
        return str(self._source_path(document_id, version, filename).relative_to(self.root))

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
            self._sync_parent(path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise CanonicalStorageError("CANONICAL_STORAGE_WRITE_FAILED") from exc

        return str(path.relative_to(self.root))

    def store_file(
        self,
        document_id: str,
        version: int,
        filename: str,
        source_path: str | Path,
        content_hash: str,
        chunk_size: int = 1024 * 1024,
    ) -> str:
        source = Path(source_path).resolve()
        if not source.is_file():
            raise CanonicalStorageError("SOURCE_FILE_NOT_FOUND")

        expected_hash = content_hash.removeprefix("sha256:")
        digest = hashlib.sha256()
        path = self._source_path(document_id, version, filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with source.open("rb") as src, temporary.open("wb") as dst:
                while chunk := src.read(chunk_size):
                    digest.update(chunk)
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())

            if digest.hexdigest() != expected_hash:
                temporary.unlink(missing_ok=True)
                raise CanonicalStorageError("CONTENT_HASH_MISMATCH")

            os.replace(temporary, path)
            self._sync_parent(path)
        except CanonicalStorageError:
            raise
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

    def read_key(self, key: str) -> bytes:
        """Read an already persisted relative storage key safely.

        Keys are metadata and therefore are treated as untrusted input even
        when they came from our own database.
        """
        path = self._safe_key_path(key)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise CanonicalStorageError("CANONICAL_SOURCE_NOT_FOUND") from exc

    def verify_key(self, key: str, content_hash: str) -> bytes:
        data = self.read_key(key)
        expected_hash = content_hash.removeprefix("sha256:")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise CanonicalStorageError("CANONICAL_CONTENT_HASH_MISMATCH")
        return data

    def verify_key_hash(self, key: str, content_hash: str) -> None:
        path = self._safe_key_path(key)
        expected_hash = content_hash.removeprefix("sha256:")
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
        except OSError as exc:
            raise CanonicalStorageError("CANONICAL_SOURCE_NOT_FOUND") from exc
        if digest.hexdigest() != expected_hash:
            raise CanonicalStorageError("CANONICAL_CONTENT_HASH_MISMATCH")

    def copy_verified_key(
        self, key: str, content_hash: str, destination: str | Path
    ) -> None:
        source = self._safe_key_path(key)
        target = Path(destination)
        digest = hashlib.sha256()
        expected_hash = content_hash.removeprefix("sha256:")
        try:
            with source.open("rb") as src, target.open("wb") as dst:
                while chunk := src.read(1024 * 1024):
                    digest.update(chunk)
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
            if digest.hexdigest() != expected_hash:
                target.unlink(missing_ok=True)
                raise CanonicalStorageError("CANONICAL_CONTENT_HASH_MISMATCH")
        except CanonicalStorageError:
            raise
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise CanonicalStorageError("CANONICAL_SOURCE_NOT_FOUND") from exc

    def _safe_key_path(self, key: str) -> Path:
        if not key or "\\" in key or "\x00" in key:
            raise CanonicalStorageError("INVALID_STORAGE_KEY")
        relative = Path(key)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise CanonicalStorageError("INVALID_STORAGE_KEY")
        path = (self.root / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise CanonicalStorageError("INVALID_STORAGE_KEY") from exc
        return path

    def delete(self, document_id: str, version: int, filename: str) -> None:
        path = self._source_path(document_id, version, filename)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise CanonicalStorageError("CANONICAL_STORAGE_DELETE_FAILED") from exc
