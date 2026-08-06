# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""AccessibilityTool — returns the page's accessibility tree as structured text via CDP."""

from typing import Any, Dict, List
from logging import Logger

from utils.logging_helper import get_logger


class AccessibilityTool:
    """Captures the page's accessibility tree (AXTree) as structured text via CDP.

    Uses Chrome DevTools Protocol (CDP) ``Accessibility.getFullAXTree`` instead of
    Playwright's deprecated ``page.accessibility.snapshot()`` API.

    The AXTree is the same structure screen readers use — it contains roles, names,
    values, and states of interactive elements, stripped of visual/layout noise.
    This provides a fast (~100ms), cheap (~200-2000 tokens) alternative to screenshots
    for element identification on well-structured pages.
    """

    logger: Logger = get_logger(f"{__name__}.AccessibilityTool")

    MAX_NODES: int = 500  # Limit to prevent context window overflow on complex pages

    def __init__(self, browser_tool: Any) -> None:
        """Initialize with a reference to the parent VisualBrowserTool.

        Args:
            browser_tool: VisualBrowserTool instance (provides get_session_page,
                          validate_session, _execute_async).
        """
        self.browser_tool = browser_tool

    def snapshot(self, session_name: str) -> Dict[str, Any]:
        """Capture the accessibility tree via CDP and return as structured text.

        Args:
            session_name: Browser session name.

        Returns:
            Tool result with the AXTree as text content.
        """
        self.logger.debug("Capturing accessibility snapshot: session=%s", session_name)

        error = self.browser_tool.validate_session(session_name)
        if error:
            self.logger.error("Session validation failed: session=%s", session_name)
            return error

        page = self.browser_tool.get_session_page(session_name)
        if not page:
            self.logger.error("No active page for session: %s", session_name)
            return {"status": "error", "content": [{"text": "No active page"}]}

        try:
            # Use CDP to get the full accessibility tree (non-deprecated path)
            cdp_session = self.browser_tool._execute_async(
                page.context.new_cdp_session(page)
            )
            ax_result = self.browser_tool._execute_async(
                cdp_session.send("Accessibility.getFullAXTree")
            )
            self.browser_tool._execute_async(cdp_session.detach())

            nodes = ax_result.get("nodes", [])
            if not nodes:
                self.logger.warning("Empty AXTree for session %s, advising screenshot fallback",
                                    session_name)
                return {
                    "status": "success",
                    "content": [{"text": "Accessibility tree is empty. "
                                 "This page likely has no semantic HTML structure. "
                                 "Use screenshot_for_vision instead."}],
                }

            # Limit nodes to prevent context window overflow on complex pages
            if len(nodes) > self.MAX_NODES:
                self.logger.warning(
                    "AXTree has %s nodes, truncating to %s for session %s",
                    len(nodes), self.MAX_NODES, session_name
                )
                nodes = nodes[:self.MAX_NODES]

            # Build a tree structure from the flat CDP node list
            tree = self._build_tree(nodes)

            # Serialize to a compact, readable format
            tree_text = self._serialize_tree(tree)
            node_count = tree_text.count("\n") + 1

            self.logger.info("Accessibility snapshot: %s nodes for session %s",
                             node_count, session_name)

            return {
                "status": "success",
                "content": [{"text": f"Accessibility tree ({node_count} nodes):\n{tree_text}"}],
            }

        except Exception as e:
            self.logger.error("Accessibility snapshot failed: %s", str(e))
            return {"status": "error", "content": [{"text": f"Error: {str(e)}"}]}

    def _build_tree(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a hierarchical tree from CDP's flat AXTree node list.

        CDP returns a flat list of nodes with parentId references.
        We reconstruct the tree for serialization.

        Args:
            nodes: Flat list of CDP AXTree nodes.

        Returns:
            Root tree node with nested children.
        """
        node_map: Dict[str, Dict[str, Any]] = {}
        root = None

        for node in nodes:
            node_id = node.get("nodeId", "")
            role = node.get("role", {}).get("value", "")
            name = node.get("name", {}).get("value", "")

            tree_node: Dict[str, Any] = {
                "role": role,
                "name": name,
                "children": [],
            }

            # Extract properties
            for prop in node.get("properties", []):
                prop_name = prop.get("name", "")
                prop_value = prop.get("value", {}).get("value")
                if prop_name in ("focused", "checked", "disabled", "expanded",
                                 "selected", "level", "valuetext"):
                    tree_node[prop_name] = prop_value

            node_map[node_id] = tree_node

            # Track root — node with no parentId (safer than assuming first node)
            if not node.get("parentId") and root is None:
                root = tree_node

        # Build parent-child relationships
        for node in nodes:
            node_id = node.get("nodeId", "")
            child_ids = node.get("childIds", [])
            tree_node = node_map.get(node_id)
            if tree_node:
                for child_id in child_ids:
                    child = node_map.get(child_id)
                    if child:
                        tree_node["children"].append(child)

        return root or {"role": "none", "name": "", "children": []}

    def _serialize_tree(self, node: Dict[str, Any], indent: int = 0) -> str:
        """Serialize an AXTree node to a compact text format.

        Output format:
          - heading "Sign In" [level=1]
          - textbox "Email" [focused]
          - textbox "Password"
          - button "Sign In"

        Args:
            node: Tree node dict with role, name, children, and optional state attrs.
            indent: Current indentation level (2 spaces per level).

        Returns:
            Multi-line string representation of the subtree.
        """
        lines: List[str] = []
        prefix = "  " * indent

        role = node.get("role", "")
        name = node.get("name", "")

        # Skip generic/container roles that add noise
        skip_roles = {"none", "generic", "presentation", "LineBreak",
                      "InlineTextBox", "StaticText"}
        if role in skip_roles and not name:
            # Still process children at the same indent level
            for child in node.get("children", []):
                lines.append(self._serialize_tree(child, indent))
            return "\n".join(filter(None, lines))

        # Build the line
        parts = [f"{prefix}- {role}"]
        if name:
            parts.append(f'"{name}"')

        # Add relevant state attributes
        attrs: List[str] = []
        if node.get("focused"):
            attrs.append("focused")
        if node.get("checked") is True:
            attrs.append("checked")
        if node.get("disabled"):
            attrs.append("disabled")
        if node.get("expanded") is True:
            attrs.append("expanded")
        if node.get("selected") is True:
            attrs.append("selected")
        if node.get("level"):
            attrs.append(f"level={node['level']}")
        if node.get("valuetext"):
            attrs.append(f"value=\"{node['valuetext']}\"")

        if attrs:
            parts.append(f"[{', '.join(attrs)}]")

        line = " ".join(parts)
        lines.append(line)

        # Process children
        for child in node.get("children", []):
            child_text = self._serialize_tree(child, indent + 1)
            if child_text:
                lines.append(child_text)

        return "\n".join(filter(None, lines))
