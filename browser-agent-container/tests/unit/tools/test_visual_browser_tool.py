# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for VisualBrowserTool.
"""

import unittest
from unittest.mock import patch, MagicMock

from tools.visual_browser_tool import VisualBrowserTool
from tools.screenshot_tool import ScreenshotTool
from tools.semantic_action_tool import SemanticActionTool
from tools.accessibility_tool import AccessibilityTool


class TestVisualBrowserToolSubclass(unittest.TestCase):
    """Test VisualBrowserTool subclasses AgentCoreBrowser."""

    def test_subclasses_agentcore_browser(self) -> None:
        """VisualBrowserTool inherits from AgentCoreBrowser."""
        from strands_tools.browser import AgentCoreBrowser
        self.assertTrue(issubclass(VisualBrowserTool, AgentCoreBrowser))


class TestVisualBrowserToolConstructor(unittest.TestCase):
    """Test constructor instantiates delegate tools."""

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def test_instantiates_screenshot_tool(self, mock_init: MagicMock) -> None:
        """Constructor creates a ScreenshotTool instance."""
        vbt = VisualBrowserTool()
        self.assertIsInstance(vbt._screenshot_tool, ScreenshotTool)

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def test_instantiates_semantic_action_tool(self, mock_init: MagicMock) -> None:
        """Constructor creates a SemanticActionTool instance."""
        vbt = VisualBrowserTool()
        self.assertIsInstance(vbt._semantic_tool, SemanticActionTool)

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def test_instantiates_accessibility_tool(self, mock_init: MagicMock) -> None:
        """Constructor creates an AccessibilityTool instance."""
        vbt = VisualBrowserTool()
        self.assertIsInstance(vbt._accessibility_tool, AccessibilityTool)

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def test_passes_self_as_browser_tool(self, mock_init: MagicMock) -> None:
        """Delegate tools receive the VisualBrowserTool instance as browser_tool."""
        vbt = VisualBrowserTool()
        self.assertIs(vbt._screenshot_tool.browser_tool, vbt)
        self.assertIs(vbt._semantic_tool.browser_tool, vbt)
        self.assertIs(vbt._accessibility_tool.browser_tool, vbt)

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def test_passes_kwargs_to_super(self, mock_init: MagicMock) -> None:
        """Constructor passes kwargs through to AgentCoreBrowser.__init__."""
        VisualBrowserTool(region="us-east-1", session_timeout=1800)
        mock_init.assert_called_once_with(region="us-east-1", session_timeout=1800)


class TestVisualBrowserToolMethods(unittest.TestCase):
    """Test tool methods are callable and delegate correctly."""

    @patch("tools.visual_browser_tool.AgentCoreBrowser.__init__", return_value=None)
    def setUp(self, mock_init: MagicMock) -> None:
        self.vbt = VisualBrowserTool()

    def test_screenshot_for_vision_is_callable(self) -> None:
        """screenshot_for_vision is a callable method."""
        self.assertTrue(callable(self.vbt.screenshot_for_vision))

    def test_semantic_action_is_callable(self) -> None:
        """semantic_action is a callable method."""
        self.assertTrue(callable(self.vbt.semantic_action))

    def test_accessibility_snapshot_is_callable(self) -> None:
        """accessibility_snapshot is a callable method."""
        self.assertTrue(callable(self.vbt.accessibility_snapshot))

    def test_screenshot_for_vision_delegates_to_screenshot_tool(self) -> None:
        """screenshot_for_vision delegates to ScreenshotTool.capture()."""
        self.vbt._screenshot_tool = MagicMock()
        expected = {"status": "success", "content": [{"text": "ok"}]}
        self.vbt._screenshot_tool.capture.return_value = expected

        result = self.vbt.screenshot_for_vision("sess-1", "title", full_page=True)

        self.vbt._screenshot_tool.capture.assert_called_once_with("sess-1", "title", True)
        self.assertEqual(result, expected)

    def test_semantic_action_delegates_to_semantic_tool(self) -> None:
        """semantic_action delegates to SemanticActionTool.execute()."""
        self.vbt._semantic_tool = MagicMock()
        expected = {"status": "success", "content": [{"text": "clicked"}]}
        self.vbt._semantic_tool.execute.return_value = expected
        mock_input = MagicMock()

        # Use keyword arg — the flat schema means Claude sends kwargs directly,
        # but the backward-compat path accepts semantic_input= for existing callers.
        result = self.vbt.semantic_action(semantic_input=mock_input)

        self.vbt._semantic_tool.execute.assert_called_once_with(mock_input)
        self.assertEqual(result, expected)

    def test_semantic_action_accepts_flat_kwargs(self) -> None:
        """semantic_action accepts flat kwargs and constructs SemanticActionInput."""
        self.vbt._semantic_tool = MagicMock()
        expected = {"status": "success", "content": [{"text": "clicked"}]}
        self.vbt._semantic_tool.execute.return_value = expected

        result = self.vbt.semantic_action(
            session_name="test-session",
            locator_type="role",
            role="button",
            name="Submit",
            action="click",
        )

        # Verify SemanticActionInput was constructed and passed
        call_args = self.vbt._semantic_tool.execute.call_args[0][0]
        self.assertEqual(call_args.session_name, "test-session")
        self.assertEqual(call_args.locator_type, "role")
        self.assertEqual(call_args.role, "button")
        self.assertEqual(call_args.name, "Submit")
        self.assertEqual(call_args.action, "click")
        self.assertEqual(result, expected)

    def test_accessibility_snapshot_delegates_to_accessibility_tool(self) -> None:
        """accessibility_snapshot delegates to AccessibilityTool.snapshot()."""
        self.vbt._accessibility_tool = MagicMock()
        expected = {"status": "success", "content": [{"text": "tree"}]}
        self.vbt._accessibility_tool.snapshot.return_value = expected

        result = self.vbt.accessibility_snapshot("sess-1")

        self.vbt._accessibility_tool.snapshot.assert_called_once_with("sess-1")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
