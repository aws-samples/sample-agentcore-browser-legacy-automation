# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for ScreenshotTool.

Updated for Spec 3 refactor: storage delegation instead of direct file I/O.
"""

import unittest
from unittest.mock import MagicMock

from handlers.screenshot_storage import ScreenshotStorageBase
from tools.screenshot_tool import ScreenshotTool


class TestScreenshotCapture(unittest.TestCase):
    """Test screenshot capture returns correct ImageBlock structure."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_storage = MagicMock(spec=ScreenshotStorageBase)
        self.mock_storage.save.return_value = "/path/to/screenshot.png"
        self.tool = ScreenshotTool(self.browser_tool, storage=self.mock_storage)

    def test_capture_returns_imageblock_structure(self) -> None:
        """Screenshot capture with mock page returns correct ImageBlock structure."""
        fake_bytes = b"\x89PNG\r\n\x1a\nfake_screenshot_data"
        mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = mock_page
        self.browser_tool._execute_async.return_value = fake_bytes

        result = self.tool.capture("test-session", "homepage")

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["content"]), 2)

        image_block = result["content"][0]
        self.assertIn("image", image_block)
        self.assertEqual(image_block["image"]["format"], "png")
        self.assertEqual(image_block["image"]["source"]["bytes"], fake_bytes)

        text_block = result["content"][1]
        self.assertIn("text", text_block)
        self.assertIn("Screenshot saved:", text_block["text"])

    def test_capture_calls_screenshot_with_full_page(self) -> None:
        """full_page parameter is passed through to page.screenshot()."""
        mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = mock_page
        self.browser_tool._execute_async.return_value = b"png_data"

        self.tool.capture("test-session", "full-page-shot", full_page=True)

        mock_page.screenshot.assert_called_once_with(type="png", full_page=True)


class TestStorageDelegation(unittest.TestCase):
    """Test file persistence delegates to storage backend."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_storage = MagicMock(spec=ScreenshotStorageBase)
        self.mock_storage.save.return_value = "/saved/screenshot.png"
        self.tool = ScreenshotTool(self.browser_tool, storage=self.mock_storage)
        self.tool.set_context("user-abc", "brws_123")

    def test_delegates_to_storage_save(self) -> None:
        """capture() calls storage.save with user_id, session_id, filename, bytes."""
        mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = mock_page
        self.browser_tool._execute_async.return_value = b"png_data"

        self.tool.capture("my-session", "test-title")

        self.mock_storage.save.assert_called_once()
        args = self.mock_storage.save.call_args[0]
        self.assertEqual(args[0], "user-abc")
        self.assertEqual(args[1], "brws_123")
        self.assertTrue(args[2].endswith(".png"))
        self.assertEqual(args[3], b"png_data")

    def test_filename_format(self) -> None:
        """Filename follows {timestamp}_{slugified_title}.png format."""
        mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = mock_page
        self.browser_tool._execute_async.return_value = b"png_data"

        self.tool.capture("sess-1", "My Test Page!")

        filename = self.mock_storage.save.call_args[0][2]
        self.assertIn("my-test-page-", filename)
        self.assertTrue(filename.endswith(".png"))

    def test_storage_return_in_text_block(self) -> None:
        """Storage return path appears in the text block."""
        mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = mock_page
        self.browser_tool._execute_async.return_value = b"png_data"

        result = self.tool.capture("sess-1", "test")

        self.assertIn("/saved/screenshot.png", result["content"][1]["text"])


class TestSessionValidationError(unittest.TestCase):
    """Test session validation error returns error result."""

    def test_returns_error_on_invalid_session(self) -> None:
        """Session validation error is returned directly."""
        browser_tool = MagicMock()
        error_result = {"status": "error", "content": [{"text": "Invalid session"}]}
        browser_tool.validate_session.return_value = error_result

        tool = ScreenshotTool(browser_tool)
        result = tool.capture("bad-session", "test")

        self.assertEqual(result, error_result)
        browser_tool.get_session_page.assert_not_called()


class TestMissingPage(unittest.TestCase):
    """Test missing page returns error result."""

    def test_returns_error_when_no_page(self) -> None:
        """Returns error when get_session_page returns None."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        browser_tool.get_session_page.return_value = None

        tool = ScreenshotTool(browser_tool)
        result = tool.capture("test-session", "test")

        self.assertEqual(result["status"], "error")
        self.assertIn("No active page", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
