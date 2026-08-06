# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BROWSER_AGENT_SYSTEM_PROMPT.
"""

import tests.__setup__  # noqa: F401
import unittest

from prompts.browser_system_prompt import BROWSER_AGENT_SYSTEM_PROMPT


class TestBrowserSystemPromptType(unittest.TestCase):
    """Test BROWSER_AGENT_SYSTEM_PROMPT is a non-empty string."""

    def test_is_string(self) -> None:
        """Prompt constant is a string."""
        self.assertIsInstance(BROWSER_AGENT_SYSTEM_PROMPT, str)

    def test_is_non_empty(self) -> None:
        """Prompt constant is not empty."""
        self.assertTrue(len(BROWSER_AGENT_SYSTEM_PROMPT) > 0)

    def test_has_substantial_content(self) -> None:
        """Prompt has substantial content (at least 500 chars)."""
        self.assertGreater(len(BROWSER_AGENT_SYSTEM_PROMPT), 500)


class TestBrowserSystemPromptToolSections(unittest.TestCase):
    """Test prompt contains key tool references."""

    def test_contains_accessibility_snapshot(self) -> None:
        """Prompt mentions accessibility_snapshot tool."""
        self.assertIn("accessibility_snapshot", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_screenshot_for_vision(self) -> None:
        """Prompt mentions screenshot_for_vision tool."""
        self.assertIn("screenshot_for_vision", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_semantic_action(self) -> None:
        """Prompt mentions semantic_action tool."""
        self.assertIn("semantic_action", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_handoff_to_user(self) -> None:
        """Prompt mentions handoff_to_user tool."""
        self.assertIn("handoff_to_user", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_browser_tool(self) -> None:
        """Prompt mentions browser tool."""
        self.assertIn("browser", BROWSER_AGENT_SYSTEM_PROMPT)


class TestBrowserSystemPromptWorkflowSections(unittest.TestCase):
    """Test prompt contains key workflow instruction sections."""

    def test_contains_session_management(self) -> None:
        """Prompt includes session management instructions."""
        self.assertIn("Session Management", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_core_workflow(self) -> None:
        """Prompt includes core workflow instructions."""
        self.assertIn("Core Workflow", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_popup_handling(self) -> None:
        """Prompt includes popup and dialog handling instructions."""
        self.assertIn("Popup", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_scrolling_strategy(self) -> None:
        """Prompt includes scrolling strategy instructions."""
        self.assertIn("Scrolling", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_error_escalation(self) -> None:
        """Prompt includes error handling escalation chain."""
        self.assertIn("Error Handling", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_human_in_the_loop(self) -> None:
        """Prompt includes HITL usage instructions."""
        self.assertIn("Human-in-the-Loop", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_semantic_locator_guide(self) -> None:
        """Prompt includes semantic locator selection guide."""
        self.assertIn("Semantic Locators", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_screenshot_titles(self) -> None:
        """Prompt includes screenshot title guidance."""
        self.assertIn("Screenshot Titles", BROWSER_AGENT_SYSTEM_PROMPT)


class TestBrowserSystemPromptErrorBudget(unittest.TestCase):
    """Test prompt encodes error budget rules."""

    def test_contains_max_3_retries(self) -> None:
        """Prompt specifies max 3 retries per element."""
        self.assertIn("3 retries", BROWSER_AGENT_SYSTEM_PROMPT)

    def test_contains_max_5_consecutive_failures(self) -> None:
        """Prompt specifies max 5 consecutive failures before HITL."""
        self.assertIn("5 consecutive", BROWSER_AGENT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
