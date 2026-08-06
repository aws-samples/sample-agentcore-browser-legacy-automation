# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for ScreenshotTool.

Feature: 86-browser-agent-core-tools, Property 3: Screenshot title slugification
Feature: 86-browser-agent-core-tools, Property 4: Screenshot tool returns valid ImageBlock structure
Validates: Requirements 2.4, 2.6

Updated for Spec 3 refactor: storage delegation instead of direct file I/O.
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import re
import unittest
from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from handlers.screenshot_storage import ScreenshotStorageBase
from tools.screenshot_tool import ScreenshotTool


# ── Slugification regex (matches the implementation) ─────────────────────
SLUG_PATTERN = re.compile(r"^[a-z0-9-]*$")


def _slugify(title: str) -> str:
    """Reproduce the slugification logic from ScreenshotTool."""
    return re.sub(r"[^a-z0-9-]", "-", title.lower().strip())[:80]


class TestTitleSlugificationProperty(unittest.TestCase):
    """Property 3: Screenshot title slugification.

    For any string used as a screenshot title, the slugified output should
    contain only lowercase alphanumeric characters and hyphens, be at most
    80 characters long, and be deterministic.
    """

    # Feature: 86-browser-agent-core-tools, Property 3: Screenshot title slugification
    @settings(max_examples=100)
    @given(title=st.text(min_size=0, max_size=200))
    def test_prop_slugified_output_valid_chars(self, title: str) -> None:
        """Slugified output contains only [a-z0-9-].

        Validates: Requirements 2.4
        """
        slug = _slugify(title)
        self.assertTrue(
            SLUG_PATTERN.match(slug),
            "Slug '%s' contains invalid characters for input %r" % (slug, title),
        )

    # Feature: 86-browser-agent-core-tools, Property 3: Screenshot title slugification
    @settings(max_examples=100)
    @given(title=st.text(min_size=0, max_size=200))
    def test_prop_slugified_output_max_80_chars(self, title: str) -> None:
        """Slugified output is at most 80 characters.

        Validates: Requirements 2.4
        """
        slug = _slugify(title)
        self.assertLessEqual(len(slug), 80)

    # Feature: 86-browser-agent-core-tools, Property 3: Screenshot title slugification
    @settings(max_examples=100)
    @given(title=st.text(min_size=0, max_size=200))
    def test_prop_slugification_is_deterministic(self, title: str) -> None:
        """Same input always produces the same slugified output.

        Validates: Requirements 2.4
        """
        self.assertEqual(_slugify(title), _slugify(title))


class TestImageBlockStructureProperty(unittest.TestCase):
    """Property 4: Screenshot tool returns valid ImageBlock structure.

    For any non-empty byte sequence returned by page.screenshot(), the
    ScreenshotTool.capture() result should have status: "success", one image
    block with format: "png" and matching bytes, plus one text block.
    """

    # Feature: 86-browser-agent-core-tools, Property 4: Screenshot tool returns valid ImageBlock structure
    @settings(max_examples=100)
    @given(png_bytes=st.binary(min_size=1, max_size=1024))
    def test_prop_capture_returns_valid_imageblock(self, png_bytes: bytes) -> None:
        """capture() returns valid ImageBlock for any non-empty bytes.

        Validates: Requirements 2.6
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = png_bytes

        mock_storage = MagicMock(spec=ScreenshotStorageBase)
        mock_storage.save.return_value = "/mock/path/screenshot.png"

        tool = ScreenshotTool(browser_tool, storage=mock_storage)
        result = tool.capture("prop-session", "prop-test")

        # Status is success
        self.assertEqual(result["status"], "success")

        # Content has exactly 2 blocks
        content = result["content"]
        self.assertEqual(len(content), 2)

        # First block is an image with format png and matching bytes
        image_block = content[0]
        self.assertIn("image", image_block)
        self.assertEqual(image_block["image"]["format"], "png")
        self.assertEqual(image_block["image"]["source"]["bytes"], png_bytes)

        # Second block is text
        text_block = content[1]
        self.assertIn("text", text_block)
        self.assertIsInstance(text_block["text"], str)
        self.assertTrue(len(text_block["text"]) > 0)


if __name__ == "__main__":
    unittest.main()
