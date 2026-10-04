from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


FILTER_PATH = (
    Path(__file__).parents[1]
    / "filters"
    / "corporate_knowledge_boundary.py"
)
SPEC = importlib.util.spec_from_file_location("corporate_knowledge_boundary", FILTER_PATH)
FILTER_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FILTER_MODULE)
MODEL_POLICY = json.loads(
    (
        Path(__file__).parents[1]
        / "config"
        / "corporate-ai-model-knowledge-boundary.json"
    ).read_text()
)


class CorporateKnowledgeBoundaryTests(unittest.TestCase):
    def test_removes_native_file_and_knowledge_references(self) -> None:
        body = {
            "model": "corporate-ai",
            "messages": [{"role": "user", "content": "Question"}],
            "files": [{"type": "file", "id": "user-local-file"}],
            "metadata": {
                "files": [{"type": "collection", "id": "corporate-kb"}],
                "folder_knowledge": [{"type": "collection", "id": "folder-kb"}],
                "chat_id": "chat-1",
            },
        }

        filtered = FILTER_MODULE.remove_native_knowledge_references(body)

        self.assertNotIn("files", filtered)
        self.assertNotIn("files", filtered["metadata"])
        self.assertNotIn("folder_knowledge", filtered["metadata"])
        self.assertEqual(filtered["metadata"]["chat_id"], "chat-1")
        self.assertEqual(filtered["messages"], body["messages"])

    def test_keeps_original_request_unchanged(self) -> None:
        body = {
            "files": [{"type": "file", "id": "local-file"}],
            "metadata": {"files": [{"type": "collection", "id": "kb"}]},
        }

        FILTER_MODULE.remove_native_knowledge_references(body)

        self.assertEqual(body["files"][0]["id"], "local-file")
        self.assertEqual(body["metadata"]["files"][0]["id"], "kb")

    def test_filter_removes_request_folder_knowledge_only(self) -> None:
        request_metadata = {
            "folder_knowledge": [{"type": "collection", "id": "folder-kb"}],
            "chat_id": "chat-1",
        }

        result = FILTER_MODULE.Filter().inlet({}, __metadata__=request_metadata)

        self.assertEqual(result, {})
        self.assertNotIn("folder_knowledge", request_metadata)
        self.assertEqual(request_metadata["chat_id"], "chat-1")

    def test_leaves_requests_without_files_unchanged(self) -> None:
        body = {"model": "corporate-ai", "messages": []}
        self.assertEqual(FILTER_MODULE.remove_native_knowledge_references(body), body)

    def test_filter_enables_open_webui_file_handler_guard(self) -> None:
        self.assertIs(FILTER_MODULE.Filter.file_handler, True)
        filtered = FILTER_MODULE.Filter().inlet(
            {"files": [{"type": "collection", "id": "corporate-kb"}]}
        )
        self.assertNotIn("files", filtered)

    def test_model_policy_disables_native_file_and_knowledge_tools(self) -> None:
        metadata = MODEL_POLICY["required_metadata_patch"]
        self.assertEqual(MODEL_POLICY["model_id"], "corporate-ai")
        self.assertEqual(metadata["knowledge"], [])
        self.assertFalse(metadata["builtinTools"]["files"])
        self.assertFalse(metadata["builtinTools"]["knowledge"])
        self.assertFalse(metadata["capabilities"]["file_upload"])
        self.assertTrue(metadata["capabilities"]["file_context"])


if __name__ == "__main__":
    unittest.main()
