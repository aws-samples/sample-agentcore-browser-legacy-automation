# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for ScreenshotTool refactor (pluggable storage).
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from handlers.screenshot_storage import (
    LocalScreenshotStorage,
    ScreenshotStorageBase,
)
from tools.screenshot_tool import ScreenshotTool


class TestStorageInjection(unittest.TestCase):
    """Test ScreenshotStorageBase injection via constructor — Req 10c.1."""

    def test_accepts_custom_storage(self) -> None:
        """Constructor accepts a ScreenshotStorageBase instance."""
        browser_tool = MagicMock()
        mock_storage = MagicMock(spec=ScreenshotStorageBase)
        tool = ScreenshotTool(browser_tool, storage=mock_storage)
        self.assertIs(tool._storage, mock_storage)

    def test_defaults_to_local_storage(self) -> None:
        """Constructor defaults to LocalScreenshotStorage when no storage given."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        self.assertIsInstance(tool._storage, LocalScreenshotStorage)

    def test_default_user_id_is_local(self) -> None:
        """Default user_id is 'local'."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        self.assertEqual(tool._user_id, "local")

    def test_default_session_id_is_empty(self) -> None:
        """Default session_id is empty string."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        self.assertEqual(tool._session_id, "")


class TestSetContext(unittest.TestCase):
    """Test set_context(user_id, session_id) — Req 10c.4."""

    def test_set_context_updates_user_and_session(self) -> None:
        """set_context sets _user_id and _session_id."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        tool.set_context("user-abc", "brws_20260317_120000_deadbeef")
        self.assertEqual(tool._user_id, "user-abc")
        self.assertEqual(tool._session_id, "brws_20260317_120000_deadbeef")

    def test_set_context_overwrites_previous(self) -> None:
        """set_context overwrites previously set values."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        tool.set_context("user-1", "sess-1")
        tool.set_context("user-2", "sess-2")
        self.assertEqual(tool._user_id, "user-2")
        self.assertEqual(tool._session_id, "sess-2")


class TestDelegationToStorage(unittest.TestCase):
    """Test that capture delegates to storage.save() — Req 10c.2, 10c.3."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = b"\x89PNG_test"

        self.mock_storage = MagicMock(spec=ScreenshotStorageBase)
        self.mock_storage.save.return_value = "/saved/path/screenshot.png"

        self.tool = ScreenshotTool(self.browser_tool, storage=self.mock_storage)
        self.tool.set_context("user-abc", "brws_123")

    def test_capture_calls_storage_save(self) -> None:
        """capture() delegates to storage.save(user_id, session_id, filename, bytes)."""
        self.tool.capture("test-session", "homepage")

        self.mock_storage.save.assert_called_once()
        call_args = self.mock_storage.save.call_args
        self.assertEqual(call_args[0][0], "user-abc")
        self.assertEqual(call_args[0][1], "brws_123")
        self.assertTrue(call_args[0][2].endswith("_homepage.png"))
        self.assertEqual(call_args[0][3], b"\x89PNG_test")

    def test_capture_uses_storage_return_in_text(self) -> None:
        """capture() includes storage return path in the text block."""
        result = self.tool.capture("test-session", "homepage")

        self.assertEqual(result["status"], "success")
        self.assertIn("/saved/path/screenshot.png", result["content"][1]["text"])

    def test_filename_format_timestamp_title(self) -> None:
        """Filename follows {timestamp}_{slugified_title}.png format."""
        self.tool.capture("test-session", "My Test Page!")

        call_args = self.mock_storage.save.call_args
        filename = call_args[0][2]
        self.assertTrue(filename.endswith(".png"))
        self.assertIn("my-test-page-", filename)
        # Timestamp prefix: YYYY-MM-DDTHH-MM-SS-mmm
        parts = filename.split("_", 1)
        self.assertTrue(parts[0].startswith("20"))

    def test_capture_with_user_id_session_id_path(self) -> None:
        """Storage receives correct user_id and session_id for path hierarchy."""
        self.tool.set_context("user-xyz", "brws_20260317_100000_abcd1234")
        self.tool.capture("sess", "test-shot")

        call_args = self.mock_storage.save.call_args
        self.assertEqual(call_args[0][0], "user-xyz")
        self.assertEqual(call_args[0][1], "brws_20260317_100000_abcd1234")


class TestBASessionsDirDefault(unittest.TestCase):
    """Test BA_SESSIONS_DIR default for LocalScreenshotStorage — Req 10c.5."""

    def test_default_local_storage_base_dir(self) -> None:
        """Default LocalScreenshotStorage uses 'sessions' as base_dir."""
        browser_tool = MagicMock()
        tool = ScreenshotTool(browser_tool)
        self.assertIsInstance(tool._storage, LocalScreenshotStorage)
        self.assertEqual(tool._storage._base_dir, "sessions")

    def test_custom_storage_overrides_default(self) -> None:
        """When custom storage is provided, BA_SESSIONS_DIR is irrelevant."""
        browser_tool = MagicMock()
        custom_storage = LocalScreenshotStorage(base_dir="custom-dir")
        tool = ScreenshotTool(browser_tool, storage=custom_storage)
        self.assertEqual(tool._storage._base_dir, "custom-dir")


class TestImageBlockStructure(unittest.TestCase):
    """Test that capture still returns correct ImageBlock structure after refactor."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.fake_bytes = b"\x89PNG\r\n\x1a\nfake_screenshot_data"
        self.browser_tool._execute_async.return_value = self.fake_bytes

        self.mock_storage = MagicMock(spec=ScreenshotStorageBase)
        self.mock_storage.save.return_value = "/path/to/screenshot.png"

        self.tool = ScreenshotTool(self.browser_tool, storage=self.mock_storage)

    def test_returns_imageblock_with_bytes(self) -> None:
        """Result contains ImageBlock with PNG bytes."""
        result = self.tool.capture("test-session", "homepage")

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["content"]), 2)
        image_block = result["content"][0]
        self.assertEqual(image_block["image"]["format"], "png")
        self.assertEqual(image_block["image"]["source"]["bytes"], self.fake_bytes)


class TestErrorHandling(unittest.TestCase):
    """Test error paths remain correct after refactor."""

    def test_session_validation_error(self) -> None:
        """Session validation error is returned directly."""
        browser_tool = MagicMock()
        error_result = {"status": "error", "content": [{"text": "Invalid session"}]}
        browser_tool.validate_session.return_value = error_result

        tool = ScreenshotTool(browser_tool)
        result = tool.capture("bad-session", "test")
        self.assertEqual(result, error_result)

    def test_no_active_page_error(self) -> None:
        """Returns error when get_session_page returns None."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        browser_tool.get_session_page.return_value = None

        tool = ScreenshotTool(browser_tool)
        result = tool.capture("test-session", "test")
        self.assertEqual(result["status"], "error")
        self.assertIn("No active page", result["content"][0]["text"])

    def test_storage_save_exception(self) -> None:
        """Returns error when storage.save raises."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = b"png_data"

        mock_storage = MagicMock(spec=ScreenshotStorageBase)
        mock_storage.save.side_effect = OSError("disk full")

        tool = ScreenshotTool(browser_tool, storage=mock_storage)
        result = tool.capture("test-session", "test")
        self.assertEqual(result["status"], "error")
        self.assertIn("disk full", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
