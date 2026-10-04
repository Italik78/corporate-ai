import importlib.util
import sys
from pathlib import Path


POLLER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "nextcloud-poller"
    / "app.py"
)


def _load_poller(monkeypatch, state_file: Path, module_name: str):
    monkeypatch.setenv("NEXTCLOUD_BASE_URL", "https://nextcloud.invalid")
    monkeypatch.setenv("NEXTCLOUD_USERNAME", "test-user")
    monkeypatch.setenv("NEXTCLOUD_PASSWORD", "test-password")
    monkeypatch.setenv("STATE_FILE", str(state_file))
    spec = importlib.util.spec_from_file_location(module_name, POLLER_SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_poller_state_survives_process_reload(monkeypatch, tmp_path):
    """A fresh poller process can resume from the persisted state file."""
    state_file = tmp_path / "state" / "nextcloud-poller-state.json"
    state_file.parent.mkdir()

    first_process = _load_poller(monkeypatch, state_file, "poller_process_one")
    expected = {"/dav/files/user/Corporate%20AI/Incoming/a.pdf": "etag-123"}
    first_process.save_state(expected)

    second_process = _load_poller(monkeypatch, state_file, "poller_process_two")
    assert second_process.load_state() == expected
    assert not state_file.with_suffix(".json.tmp").exists()
    same_etag_file = {
        "href": "/dav/files/user/Corporate%20AI/Incoming/a.pdf",
        "etag": "etag-123",
    }
    changed_etag_file = {**same_etag_file, "etag": "etag-124"}
    assert not second_process.has_changed(second_process.load_state(), same_etag_file)
    assert second_process.has_changed(second_process.load_state(), changed_etag_file)


def test_poller_state_replace_keeps_previous_file_on_serialization_failure(
    monkeypatch, tmp_path
):
    state_file = tmp_path / "state.json"
    poller = _load_poller(monkeypatch, state_file, "poller_atomic_write")
    original = {"href": "etag-old"}
    poller.save_state(original)

    # JSON serialization fails before replace; the last committed state remains.
    class NotSerializable:
        pass

    try:
        poller.save_state({"href": NotSerializable()})
    except TypeError:
        pass
    else:
        raise AssertionError("expected JSON serialization failure")

    assert poller.load_state() == original
