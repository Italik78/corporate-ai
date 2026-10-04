from dataclasses import dataclass
from enum import StrEnum

from .models import DocumentVersionResponse
from .storage import CanonicalStorageError, FilesystemCanonicalStorage


class ReconciliationState(StrEnum):
    VALID = "VALID"
    REPAIRABLE = "REPAIRABLE"
    LEGACY = "LEGACY"
    INVALID = "INVALID"


@dataclass(frozen=True)
class VersionIntegrity:
    state: ReconciliationState
    document_id: str
    version: int
    lifecycle_status: str
    canonical_storage_key: str | None
    reason: str
    candidate_storage_key: str | None = None


def inspect_canonical_source(
    version: DocumentVersionResponse,
    storage: FilesystemCanonicalStorage,
) -> VersionIntegrity:
    """Classify canonical bytes without modifying metadata or storage.

    Missing keys are classified LEGACY unless the adapter's expected key
    exists and its hash verifies, in which case explicit repair is possible.
    A present but unusable key is INVALID. Valid bytes for a still-INGESTING
    version are REPAIRABLE because stable chunk IDs permit safe replay.
    """
    base = {
        "document_id": version.document_id,
        "version": version.version,
        "lifecycle_status": version.lifecycle_status.value,
        "canonical_storage_key": version.canonical_storage_key,
    }
    if not version.canonical_storage_key:
        try:
            candidate = storage.expected_key(
                version.document_id,
                version.version,
                version.source_file,
            )
            storage.verify_key_hash(candidate, version.content_hash)
        except CanonicalStorageError:
            state = ReconciliationState.LEGACY
            reason = "CANONICAL_STORAGE_KEY_MISSING"
        else:
            state = ReconciliationState.REPAIRABLE
            reason = "CANONICAL_KEY_MISSING_SOURCE_VERIFIED"
        return VersionIntegrity(
            state=state,
            reason=reason,
            **base,
            candidate_storage_key=(candidate if state == ReconciliationState.REPAIRABLE else None),
        )
    expected_key = (
        f"documents/{version.document_id}/original/"
        f"{version.version}/{version.source_file}"
    )
    if version.canonical_storage_key != expected_key:
        return VersionIntegrity(
            state=ReconciliationState.INVALID,
            reason="CANONICAL_STORAGE_KEY_MISMATCH",
            **base,
        )
    try:
        storage.verify_key_hash(version.canonical_storage_key, version.content_hash)
    except CanonicalStorageError as exc:
        return VersionIntegrity(
            state=ReconciliationState.INVALID,
            reason=str(exc),
            **base,
        )

    state = (
        ReconciliationState.REPAIRABLE
        if version.lifecycle_status.value == "INGESTING"
        else ReconciliationState.VALID
    )
    return VersionIntegrity(
        state=state,
        reason=(
            "CANONICAL_SOURCE_VERIFIED_REPLAYABLE"
            if state == ReconciliationState.REPAIRABLE
            else "CANONICAL_SOURCE_HASH_VERIFIED"
        ),
        **base,
    )
