# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for AccessibilityTool.

Feature: 86-browser-agent-core-tools, Property 8: AXTree truncation at MAX_NODES
Feature: 86-browser-agent-core-tools, Property 9: AXTree serialization preserves non-generic nodes with attributes
Validates: Requirements 4.4, 4.5, 4.6, 4.7
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import unittest
import unittest.mock
from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from tools.accessibility_tool import AccessibilityTool


# ── Helpers ──────────────────────────────────────────────────────────────

GENERIC_ROLES = {"none", "generic", "presentation", "LineBreak",
                 "InlineTextBox", "StaticText"}

NON_GENERIC_ROLES = [
    "button", "link", "heading", "textbox", "checkbox", "radio",
    "combobox", "slider", "navigation", "search", "banner", "main",
    "complementary", "contentinfo", "form", "list", "listitem",
    "menuitem", "tab", "tabpanel", "dialog", "alert", "separator",
    "img", "table", "row", "cell", "columnheader", "rowheader",
    "tree", "treeitem", "toolbar", "tooltip", "status", "log",
    "marquee", "timer", "progressbar", "meter", "spinbutton",
    "scrollbar", "switch", "WebArea", "article", "region",
]


def _make_cdp_node(
    node_id: str,
    role: str,
    name: str = "",
    parent_id: str = None,
    child_ids: list = None,
    properties: list = None,
) -> dict:
    """Build a CDP AXTree node dict."""
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


def _make_cdp_property(name: str, value: object) -> dict:
    """Build a CDP property dict."""
    return {"name": name, "value": {"value": value}}


class TestAXTreeTruncationProperty(unittest.TestCase):
    """Property 8: AXTree truncation at MAX_NODES.

    For any CDP AXTree response with more than 500 nodes, the AccessibilityTool
    should truncate to exactly 500 nodes in the output and log a warning
    containing the original count, truncated count, and session name.

    Validates: Requirements 4.4
    """

    # Feature: 86-browser-agent-core-tools, Property 8: AXTree truncation at MAX_NODES
    @settings(max_examples=100)
    @given(extra_nodes=st.integers(min_value=1, max_value=500))
    def test_prop_truncation_at_max_nodes(self, extra_nodes: int) -> None:
        """AXTree with >500 nodes is truncated to exactly 500.

        Validates: Requirements 4.4
        """
        total_nodes = 500 + extra_nodes

        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page

        # Build flat node list: root + (total_nodes - 1) children
        nodes = [_make_cdp_node("0", "WebArea", "Page",
                                child_ids=[str(i) for i in range(1, total_nodes)])]
        for i in range(1, total_nodes):
            nodes.append(_make_cdp_node(str(i), "button", f"B{i}", parent_id="0"))

        mock_cdp = MagicMock()
        browser_tool._execute_async.side_effect = [
            mock_cdp,
            {"nodes": nodes},
            None,
        ]

        tool = AccessibilityTool(browser_tool)

        with unittest.mock.patch.object(tool, "logger") as mock_logger:
            result = tool.snapshot("prop-session")

        # Result is success
        self.assertEqual(result["status"], "success")

        # Warning was logged with original count, truncated count, session name
        mock_logger.warning.assert_called()
        warning_args = mock_logger.warning.call_args[0]
        self.assertIn(total_nodes, warning_args,
                      f"Warning should contain original count {total_nodes}")
        self.assertIn(500, warning_args,
                      "Warning should contain truncated count 500")
        self.assertIn("prop-session", warning_args,
                      "Warning should contain session name")

    # Feature: 86-browser-agent-core-tools, Property 8: AXTree truncation at MAX_NODES
    @settings(max_examples=100)
    @given(node_count=st.integers(min_value=1, max_value=500))
    def test_prop_no_truncation_at_or_below_max(self, node_count: int) -> None:
        """AXTree with <=500 nodes is NOT truncated.

        Validates: Requirements 4.4
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page

        nodes = [_make_cdp_node("0", "WebArea", "Page",
                                child_ids=[str(i) for i in range(1, node_count)])]
        for i in range(1, node_count):
            nodes.append(_make_cdp_node(str(i), "button", f"B{i}", parent_id="0"))

        mock_cdp = MagicMock()
        browser_tool._execute_async.side_effect = [
            mock_cdp,
            {"nodes": nodes},
            None,
        ]

        tool = AccessibilityTool(browser_tool)

        with unittest.mock.patch.object(tool, "logger") as mock_logger:
            result = tool.snapshot("prop-session")

        self.assertEqual(result["status"], "success")
        # No truncation warning should be logged
        for call_args in mock_logger.warning.call_args_list:
            args = call_args[0]
            self.assertNotIn("truncating", str(args[0]).lower(),
                             "Should not log truncation warning for <=500 nodes")


class TestAXTreeSerializationProperty(unittest.TestCase):
    """Property 9: AXTree serialization preserves non-generic nodes with attributes.

    For any AXTree node with a non-generic role and a non-empty name, the
    serialized text output should contain both the role and the quoted name.
    For nodes with state attributes, those attributes should appear in brackets.

    Validates: Requirements 4.5, 4.6, 4.7
    """

    # Feature: 86-browser-agent-core-tools, Property 9: AXTree serialization preserves non-generic nodes with attributes
    @settings(max_examples=100)
    @given(
        role=st.sampled_from(NON_GENERIC_ROLES),
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"),
                                   blacklist_characters='"'),
            min_size=1, max_size=50,
        ),
    )
    def test_prop_non_generic_node_preserved(self, role: str, name: str) -> None:
        """Non-generic nodes with names appear in serialized output.

        Validates: Requirements 4.5, 4.6
        """
        tool = AccessibilityTool(MagicMock())
        node = {"role": role, "name": name, "children": []}
        result = tool._serialize_tree(node)

        self.assertIn(role, result,
                      f"Role '{role}' should appear in serialized output")
        self.assertIn(f'"{name}"', result,
                      f"Quoted name '{name}' should appear in serialized output")

    # Feature: 86-browser-agent-core-tools, Property 9: AXTree serialization preserves non-generic nodes with attributes
    @settings(max_examples=100)
    @given(
        role=st.sampled_from(NON_GENERIC_ROLES),
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"),
                                   blacklist_characters='"'),
            min_size=1, max_size=30,
        ),
        focused=st.booleans(),
        checked=st.sampled_from([True, False, None]),
        disabled=st.booleans(),
        expanded=st.sampled_from([True, False, None]),
        selected=st.sampled_from([True, False, None]),
        level=st.one_of(st.none(), st.integers(min_value=1, max_value=6)),
    )
    def test_prop_state_attrs_in_brackets(
        self, role: str, name: str, focused: bool, checked: object,
        disabled: bool, expanded: object, selected: object, level: object,
    ) -> None:
        """State attributes appear in square brackets when present.

        Validates: Requirements 4.6, 4.7
        """
        tool = AccessibilityTool(MagicMock())
        node: dict = {"role": role, "name": name, "children": []}

        if focused:
            node["focused"] = True
        if checked is True:
            node["checked"] = True
        if disabled:
            node["disabled"] = True
        if expanded is True:
            node["expanded"] = True
        if selected is True:
            node["selected"] = True
        if level is not None:
            node["level"] = level

        result = tool._serialize_tree(node)

        # Verify each set attribute appears in the output
        if focused:
            self.assertIn("focused", result)
        if checked is True:
            self.assertIn("checked", result)
        if disabled:
            self.assertIn("disabled", result)
        if expanded is True:
            self.assertIn("expanded", result)
        if selected is True:
            self.assertIn("selected", result)
        if level is not None:
            self.assertIn(f"level={level}", result)

        # If any attrs are set, brackets should be present
        has_attrs = any([
            focused,
            checked is True,
            disabled,
            expanded is True,
            selected is True,
            level is not None,
        ])
        if has_attrs:
            self.assertIn("[", result, "Brackets should be present when attrs exist")
            self.assertIn("]", result, "Brackets should be present when attrs exist")

    # Feature: 86-browser-agent-core-tools, Property 9: AXTree serialization preserves non-generic nodes with attributes
    @settings(max_examples=100)
    @given(
        role=st.sampled_from(NON_GENERIC_ROLES),
        valuetext=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"),
                                   blacklist_characters='"'),
            min_size=1, max_size=30,
        ),
    )
    def test_prop_valuetext_in_brackets(self, role: str, valuetext: str) -> None:
        """Valuetext attribute appears as value="text" in brackets.

        Validates: Requirements 4.7
        """
        tool = AccessibilityTool(MagicMock())
        node = {"role": role, "name": "Test", "children": [], "valuetext": valuetext}
        result = tool._serialize_tree(node)

        self.assertIn(f'value="{valuetext}"', result,
                      f"valuetext '{valuetext}' should appear in brackets")


if __name__ == "__main__":
    unittest.main()
