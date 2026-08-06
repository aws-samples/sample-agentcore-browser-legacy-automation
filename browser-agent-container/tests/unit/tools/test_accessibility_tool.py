# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for AccessibilityTool.
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import unittest
import unittest.mock
from unittest.mock import MagicMock, call

from tools.accessibility_tool import AccessibilityTool


def _make_cdp_node(
    node_id: str,
    role: str,
    name: str = "",
    parent_id: str = None,
    child_ids: list = None,
    properties: list = None,
) -> dict:
    """Helper to build a CDP AXTree node dict."""
    node = {
        "nodeId": node_id,
        "role": {"value": role},
        "name": {"value": name},
        "childIds": child_ids or [],
        "properties": properties or [],
    }
    if parent_id is not None:
        node["parentId"] = parent_id
    return node


class TestAXTreeCaptureViaCDP(unittest.TestCase):
    """Test AXTree capture via mock CDP session."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.tool = AccessibilityTool(self.browser_tool)

        # Mock CDP session
        self.mock_cdp = MagicMock()
        # _execute_async returns: cdp_session, ax_result, detach result
        self.browser_tool._execute_async.side_effect = [
            self.mock_cdp,  # new_cdp_session
            {"nodes": [_make_cdp_node("1", "WebArea", "Test Page")]},  # send
            None,  # detach
        ]

    def test_cdp_session_created_and_detached(self) -> None:
        """Verify new_cdp_session, send, and detach are called."""
        self.tool.snapshot("test-session")

        # _execute_async called 3 times: new_cdp_session, send, detach
        self.assertEqual(self.browser_tool._execute_async.call_count, 3)
        self.mock_page.context.new_cdp_session.assert_called_once_with(self.mock_page)
        self.mock_cdp.send.assert_called_once_with("Accessibility.getFullAXTree")
        self.mock_cdp.detach.assert_called_once()

    def test_returns_success_with_tree_text(self) -> None:
        """Successful capture returns status success with tree text."""
        result = self.tool.snapshot("test-session")

        self.assertEqual(result["status"], "success")
        self.assertIn("Accessibility tree", result["content"][0]["text"])
        self.assertIn("WebArea", result["content"][0]["text"])
        self.assertIn('"Test Page"', result["content"][0]["text"])


class TestTreeBuilding(unittest.TestCase):
    """Test tree building from flat node list with parent/child relationships."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.tool = AccessibilityTool(self.browser_tool)

    def test_parent_child_hierarchy(self) -> None:
        """Flat nodes with parentId/childIds produce correct hierarchy."""
        nodes = [
            _make_cdp_node("1", "WebArea", "Page", child_ids=["2", "3"]),
            _make_cdp_node("2", "heading", "Title", parent_id="1"),
            _make_cdp_node("3", "button", "Submit", parent_id="1"),
        ]
        self.browser_tool._execute_async.side_effect = [
            MagicMock(),  # cdp session
            {"nodes": nodes},
            None,  # detach
        ]

        result = self.tool.snapshot("test-session")
        text = result["content"][0]["text"]

        # Root at indent 0, children at indent 1
        self.assertIn("- WebArea", text)
        self.assertIn("  - heading", text)
        self.assertIn("  - button", text)

    def test_deeply_nested_tree(self) -> None:
        """Three-level nesting produces correct indentation."""
        nodes = [
            _make_cdp_node("1", "WebArea", "Page", child_ids=["2"]),
            _make_cdp_node("2", "navigation", "Nav", parent_id="1", child_ids=["3"]),
            _make_cdp_node("3", "link", "Home", parent_id="2"),
        ]
        self.browser_tool._execute_async.side_effect = [
            MagicMock(), {"nodes": nodes}, None,
        ]

        result = self.tool.snapshot("test-session")
        text = result["content"][0]["text"]

        self.assertIn("- WebArea", text)
        self.assertIn("  - navigation", text)
        self.assertIn("    - link", text)


class TestSerializationFormat(unittest.TestCase):
    """Test serialization format: correct indentation, role, name, state attributes."""

    def setUp(self) -> None:
        self.tool = AccessibilityTool(MagicMock())

    def test_basic_node_format(self) -> None:
        """Node serializes as '- role "name"'."""
        node = {"role": "button", "name": "Submit", "children": []}
        result = self.tool._serialize_tree(node)
        self.assertEqual(result, '- button "Submit"')

    def test_node_without_name(self) -> None:
        """Node without name serializes as '- role' (no quotes)."""
        node = {"role": "separator", "name": "", "children": []}
        result = self.tool._serialize_tree(node)
        self.assertEqual(result, "- separator")

    def test_state_attributes_in_brackets(self) -> None:
        """State attributes appear in square brackets."""
        node = {
            "role": "textbox", "name": "Email", "children": [],
            "focused": True, "disabled": True,
        }
        result = self.tool._serialize_tree(node)
        self.assertIn("[focused, disabled]", result)

    def test_level_attribute(self) -> None:
        """Level attribute serializes as level=N."""
        node = {
            "role": "heading", "name": "Title", "children": [],
            "level": 1,
        }
        result = self.tool._serialize_tree(node)
        self.assertIn("[level=1]", result)

    def test_valuetext_attribute(self) -> None:
        """Valuetext attribute serializes as value="text"."""
        node = {
            "role": "slider", "name": "Volume", "children": [],
            "valuetext": "50%",
        }
        result = self.tool._serialize_tree(node)
        self.assertIn('value="50%"', result)

    def test_checked_and_selected(self) -> None:
        """Checked and selected attributes appear when True."""
        node = {
            "role": "checkbox", "name": "Agree", "children": [],
            "checked": True, "selected": True,
        }
        result = self.tool._serialize_tree(node)
        self.assertIn("checked", result)
        self.assertIn("selected", result)

    def test_expanded_attribute(self) -> None:
        """Expanded attribute appears when True."""
        node = {
            "role": "button", "name": "Menu", "children": [],
            "expanded": True,
        }
        result = self.tool._serialize_tree(node)
        self.assertIn("[expanded]", result)

    def test_indentation_with_children(self) -> None:
        """Children are indented 2 spaces deeper than parent."""
        node = {
            "role": "navigation", "name": "Main", "children": [
                {"role": "link", "name": "Home", "children": []},
                {"role": "link", "name": "About", "children": []},
            ],
        }
        result = self.tool._serialize_tree(node)
        lines = result.split("\n")
        self.assertTrue(lines[0].startswith("- navigation"))
        self.assertTrue(lines[1].startswith("  - link"))
        self.assertTrue(lines[2].startswith("  - link"))


class TestEmptyTree(unittest.TestCase):
    """Test empty tree returns success with fallback message."""

    def test_empty_nodes_returns_fallback(self) -> None:
        """Zero nodes returns success advising screenshot_for_vision."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page

        mock_cdp = MagicMock()
        browser_tool._execute_async.side_effect = [
            mock_cdp,
            {"nodes": []},
            None,
        ]

        tool = AccessibilityTool(browser_tool)
        result = tool.snapshot("test-session")

        self.assertEqual(result["status"], "success")
        self.assertIn("screenshot_for_vision", result["content"][0]["text"])


class TestTruncation(unittest.TestCase):
    """Test truncation at MAX_NODES (500) with warning log."""

    def test_truncates_at_max_nodes(self) -> None:
        """Nodes exceeding MAX_NODES are truncated to 500."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page

        # Generate 600 nodes — root + 599 children
        nodes = [_make_cdp_node("0", "WebArea", "Page",
                                child_ids=[str(i) for i in range(1, 600)])]
        for i in range(1, 600):
            nodes.append(_make_cdp_node(str(i), "button", f"Btn{i}", parent_id="0"))

        mock_cdp = MagicMock()
        browser_tool._execute_async.side_effect = [
            mock_cdp,
            {"nodes": nodes},
            None,
        ]

        tool = AccessibilityTool(browser_tool)
        result = tool.snapshot("test-session")

        self.assertEqual(result["status"], "success")
        # The tree text should not contain all 600 buttons
        text = result["content"][0]["text"]
        self.assertNotIn("Btn599", text)

    def test_truncation_logs_warning(self) -> None:
        """Warning is logged with original count, truncated count, session name."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page

        nodes = [_make_cdp_node(str(i), "button", f"B{i}") for i in range(550)]
        mock_cdp = MagicMock()
        browser_tool._execute_async.side_effect = [
            mock_cdp, {"nodes": nodes}, None,
        ]

        tool = AccessibilityTool(browser_tool)
        with unittest.mock.patch.object(tool, "logger") as mock_logger:
            tool.snapshot("my-session")
            mock_logger.warning.assert_called()
            warning_args = mock_logger.warning.call_args
            # Verify the warning contains original count, truncated count, session name
            self.assertIn(550, warning_args[0])
            self.assertIn(500, warning_args[0])
            self.assertIn("my-session", warning_args[0])


class TestGenericRoleSkipping(unittest.TestCase):
    """Test generic role skipping (nodes with generic role and no name are omitted)."""

    def setUp(self) -> None:
        self.tool = AccessibilityTool(MagicMock())

    def test_generic_role_no_name_skipped(self) -> None:
        """Nodes with generic role and empty name are omitted from output."""
        node = {
            "role": "generic", "name": "", "children": [
                {"role": "button", "name": "OK", "children": []},
            ],
        }
        result = self.tool._serialize_tree(node)
        self.assertNotIn("generic", result)
        self.assertIn('- button "OK"', result)

    def test_all_skip_roles_omitted(self) -> None:
        """All skip roles (none, generic, presentation, LineBreak, InlineTextBox, StaticText) are omitted when no name."""
        for skip_role in ("none", "generic", "presentation", "LineBreak",
                          "InlineTextBox", "StaticText"):
            node = {
                "role": skip_role, "name": "", "children": [
                    {"role": "link", "name": "Test", "children": []},
                ],
            }
            result = self.tool._serialize_tree(node)
            self.assertNotIn(f"- {skip_role}", result,
                             f"Role '{skip_role}' should be skipped when name is empty")
            self.assertIn('- link "Test"', result)

    def test_generic_role_with_name_kept(self) -> None:
        """Generic role WITH a name is NOT skipped."""
        node = {"role": "generic", "name": "Container", "children": []}
        result = self.tool._serialize_tree(node)
        self.assertIn('- generic "Container"', result)

    def test_children_of_skipped_node_preserved(self) -> None:
        """Children of skipped generic nodes are still rendered at same indent."""
        node = {
            "role": "none", "name": "", "children": [
                {"role": "heading", "name": "Title", "children": []},
                {"role": "paragraph", "name": "Text", "children": []},
            ],
        }
        result = self.tool._serialize_tree(node)
        self.assertIn('- heading "Title"', result)
        self.assertIn('- paragraph "Text"', result)


class TestCDPError(unittest.TestCase):
    """Test CDP error returns error result."""

    def test_cdp_exception_returns_error(self) -> None:
        """Exception during CDP call returns error result."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.side_effect = RuntimeError("CDP connection lost")

        tool = AccessibilityTool(browser_tool)
        result = tool.snapshot("test-session")

        self.assertEqual(result["status"], "error")
        self.assertIn("CDP connection lost", result["content"][0]["text"])

    def test_session_validation_error_returned(self) -> None:
        """Session validation error is returned directly."""
        browser_tool = MagicMock()
        error_result = {"status": "error", "content": [{"text": "Invalid session"}]}
        browser_tool.validate_session.return_value = error_result

        tool = AccessibilityTool(browser_tool)
        result = tool.snapshot("bad-session")

        self.assertEqual(result, error_result)
        browser_tool.get_session_page.assert_not_called()

    def test_no_page_returns_error(self) -> None:
        """Returns error when get_session_page returns None."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        browser_tool.get_session_page.return_value = None

        tool = AccessibilityTool(browser_tool)
        result = tool.snapshot("test-session")

        self.assertEqual(result["status"], "error")
        self.assertIn("No active page", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
