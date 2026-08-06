# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for SemanticActionTool.
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import unittest
from unittest.mock import MagicMock, call

from tools.models import SemanticActionInput
from tools.semantic_action_tool import SemanticActionTool


def _make_input(**overrides) -> SemanticActionInput:
    """Build a minimal valid SemanticActionInput with overrides."""
    defaults = {
        "session_name": "test-session",
        "locator_type": "role",
        "role": "button",
        "name": "Submit",
        "action": "click",
    }
    defaults.update(overrides)
    return SemanticActionInput(**defaults)


class TestLocatorBuilding(unittest.TestCase):
    """Test locator building for all 7 locator types."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = None
        self.tool = SemanticActionTool(self.browser_tool)

    def test_role_locator_calls_get_by_role(self) -> None:
        """locator_type='role' calls get_by_role with name."""
        si = _make_input(locator_type="role", role="button", name="Submit")
        self.tool.execute(si)
        self.mock_page.get_by_role.assert_called_once_with("button", name="Submit")

    def test_role_locator_passes_role_filters(self) -> None:
        """Role-specific filters are passed as kwargs to get_by_role."""
        si = _make_input(
            locator_type="role", role="checkbox", name="Agree",
            checked=True, disabled=False, level=2,
        )
        self.tool.execute(si)
        self.mock_page.get_by_role.assert_called_once_with(
            "checkbox", name="Agree", checked=True, disabled=False, level=2,
        )

    def test_role_locator_does_not_pass_exact(self) -> None:
        """get_by_role does NOT receive exact parameter (design choice)."""
        si = _make_input(locator_type="role", role="button", name="OK", exact=True)
        self.tool.execute(si)
        call_kwargs = self.mock_page.get_by_role.call_args
        self.assertNotIn("exact", call_kwargs.kwargs)

    def test_label_locator_calls_get_by_label(self) -> None:
        """locator_type='label' calls get_by_label with exact."""
        si = _make_input(locator_type="label", label="Email", action="fill", value="x")
        self.tool.execute(si)
        self.mock_page.get_by_label.assert_called_once_with("Email", exact=False)

    def test_text_locator_calls_get_by_text(self) -> None:
        """locator_type='text' calls get_by_text with exact."""
        si = _make_input(locator_type="text", text="Hello", action="click")
        self.tool.execute(si)
        self.mock_page.get_by_text.assert_called_once_with("Hello", exact=False)

    def test_placeholder_locator_calls_get_by_placeholder(self) -> None:
        """locator_type='placeholder' calls get_by_placeholder with exact."""
        si = _make_input(
            locator_type="placeholder", placeholder="Search...", action="fill", value="q",
        )
        self.tool.execute(si)
        self.mock_page.get_by_placeholder.assert_called_once_with("Search...", exact=False)

    def test_alt_text_locator_calls_get_by_alt_text(self) -> None:
        """locator_type='alt_text' calls get_by_alt_text with exact."""
        si = _make_input(locator_type="alt_text", alt_text="Logo", action="click")
        self.tool.execute(si)
        self.mock_page.get_by_alt_text.assert_called_once_with("Logo", exact=False)

    def test_title_locator_calls_get_by_title(self) -> None:
        """locator_type='title' calls get_by_title with title_text and exact."""
        si = _make_input(locator_type="title", title_text="Tooltip", action="click")
        self.tool.execute(si)
        self.mock_page.get_by_title.assert_called_once_with("Tooltip", exact=False)

    def test_test_id_locator_calls_get_by_test_id(self) -> None:
        """locator_type='test_id' calls get_by_test_id without exact."""
        si = _make_input(locator_type="test_id", test_id="submit-btn", action="click")
        self.tool.execute(si)
        self.mock_page.get_by_test_id.assert_called_once_with("submit-btn")

    def test_exact_true_passed_to_label(self) -> None:
        """exact=True is forwarded to get_by_label."""
        si = _make_input(locator_type="label", label="Name", exact=True, action="click")
        self.tool.execute(si)
        self.mock_page.get_by_label.assert_called_once_with("Name", exact=True)


class TestActionExecution(unittest.TestCase):
    """Test action execution for representative actions."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = None
        self.tool = SemanticActionTool(self.browser_tool)
        # Make locator chain return itself for chaining
        self.mock_locator = self.mock_page.get_by_role.return_value

    def test_click_action(self) -> None:
        """click action calls locator.click()."""
        si = _make_input(action="click")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.mock_locator.click.assert_called_once()

    def test_fill_action(self) -> None:
        """fill action calls locator.fill(value)."""
        si = _make_input(action="fill", value="hello")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.mock_locator.fill.assert_called_once()
        # Verify value was passed (first positional arg)
        call_args = self.mock_locator.fill.call_args
        self.assertEqual(call_args[0][0], "hello")

    def test_check_action(self) -> None:
        """check action calls locator.check()."""
        si = _make_input(action="check")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.mock_locator.check.assert_called_once()

    def test_select_option_by_label(self) -> None:
        """select_option with option_label calls locator.select_option(label=...)."""
        si = _make_input(action="select_option", option_label="Small")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.mock_locator.select_option.assert_called_once()
        call_kwargs = self.mock_locator.select_option.call_args.kwargs
        self.assertEqual(call_kwargs["label"], "Small")

    def test_select_option_by_index(self) -> None:
        """select_option with option_index calls locator.select_option(index=...)."""
        si = _make_input(action="select_option", option_index=2)
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        call_kwargs = self.mock_locator.select_option.call_args.kwargs
        self.assertEqual(call_kwargs["index"], 2)

    def test_select_option_by_value(self) -> None:
        """select_option with value calls locator.select_option(value)."""
        si = _make_input(action="select_option", value="sm")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.mock_locator.select_option.assert_called_once()

    def test_get_text_returns_value_in_text(self) -> None:
        """get_text returns the element text in the result."""
        self.browser_tool._execute_async.return_value = "Hello World"
        si = _make_input(action="get_text")
        result = self.tool.execute(si)
        self.assertEqual(result["status"], "success")
        self.assertIn("Hello World", result["content"][0]["text"])


class TestSelectOptionNoForce(unittest.TestCase):
    """Test that select_option does NOT pass force parameter."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = None
        self.tool = SemanticActionTool(self.browser_tool)
        self.mock_locator = self.mock_page.get_by_role.return_value

    def test_select_option_does_not_pass_force(self) -> None:
        """select_option never passes force even when force=True on input."""
        si = _make_input(action="select_option", option_label="Large", force=True)
        self.tool.execute(si)
        call_kwargs = self.mock_locator.select_option.call_args.kwargs
        self.assertNotIn("force", call_kwargs)


class TestFilterAndNth(unittest.TestCase):
    """Test filter_text, filter_not_text, and nth narrowing."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = None
        self.tool = SemanticActionTool(self.browser_tool)
        self.mock_locator = self.mock_page.get_by_role.return_value

    def test_filter_text_applies_filter(self) -> None:
        """filter_text applies .filter(has_text=...) to locator."""
        si = _make_input(filter_text="Price")
        self.tool.execute(si)
        self.mock_locator.filter.assert_called_with(has_text="Price")

    def test_filter_not_text_applies_filter(self) -> None:
        """filter_not_text applies .filter(has_not_text=...) to locator."""
        si = _make_input(filter_not_text="Sold Out")
        self.tool.execute(si)
        self.mock_locator.filter.assert_called_with(has_not_text="Sold Out")

    def test_nth_applies_nth(self) -> None:
        """nth applies .nth(n) to locator."""
        si = _make_input(nth=2)
        self.tool.execute(si)
        self.mock_locator.nth.assert_called_once_with(2)

    def test_both_filters_applied(self) -> None:
        """Both filter_text and filter_not_text are applied in sequence."""
        si = _make_input(filter_text="Available", filter_not_text="Sold Out")
        self.tool.execute(si)
        # filter is called twice — once for has_text, once for has_not_text
        filter_calls = self.mock_locator.filter.call_args_list
        self.assertEqual(len(filter_calls), 1)
        # The second filter is called on the result of the first
        self.mock_locator.filter.return_value.filter.assert_called_once_with(
            has_not_text="Sold Out"
        )


class TestFrameSelector(unittest.TestCase):
    """Test frame_selector enters iframe via page.frame_locator()."""

    def setUp(self) -> None:
        self.browser_tool = MagicMock()
        self.browser_tool.validate_session.return_value = None
        self.mock_page = MagicMock()
        self.browser_tool.get_session_page.return_value = self.mock_page
        self.browser_tool._execute_async.return_value = None
        self.tool = SemanticActionTool(self.browser_tool)

    def test_frame_selector_enters_iframe(self) -> None:
        """frame_selector causes page.frame_locator() to be called."""
        si = _make_input(frame_selector="iframe#content")
        self.tool.execute(si)
        self.mock_page.frame_locator.assert_called_once_with("iframe#content")
        # Locator is built on the frame, not the page
        frame = self.mock_page.frame_locator.return_value
        frame.get_by_role.assert_called_once()

    def test_no_frame_selector_uses_page_directly(self) -> None:
        """Without frame_selector, locator is built on the page."""
        si = _make_input()
        self.tool.execute(si)
        self.mock_page.frame_locator.assert_not_called()
        self.mock_page.get_by_role.assert_called_once()


class TestSessionValidation(unittest.TestCase):
    """Test session validation and missing page errors."""

    def test_returns_error_on_invalid_session(self) -> None:
        """Session validation error is returned directly."""
        browser_tool = MagicMock()
        error_result = {"status": "error", "content": [{"text": "Invalid session"}]}
        browser_tool.validate_session.return_value = error_result
        tool = SemanticActionTool(browser_tool)

        si = _make_input()
        result = tool.execute(si)

        self.assertEqual(result, error_result)
        browser_tool.get_session_page.assert_not_called()

    def test_returns_error_when_no_page(self) -> None:
        """Returns error when get_session_page returns None."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        browser_tool.get_session_page.return_value = None
        tool = SemanticActionTool(browser_tool)

        si = _make_input()
        result = tool.execute(si)

        self.assertEqual(result["status"], "error")
        self.assertIn("No active page", result["content"][0]["text"])


class TestExceptionHandling(unittest.TestCase):
    """Test exception during action returns error result."""

    def test_playwright_exception_returns_error(self) -> None:
        """Exception during action execution returns error result."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.side_effect = TimeoutError("Element not found within 30s")
        tool = SemanticActionTool(browser_tool)

        si = _make_input(action="click")
        result = tool.execute(si)

        self.assertEqual(result["status"], "error")
        self.assertIn("Element not found within 30s", result["content"][0]["text"])

    def test_value_error_returns_error(self) -> None:
        """ValueError during locator building returns error result."""
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        # Make get_by_role raise to simulate an error
        mock_page.get_by_role.side_effect = ValueError("Bad role")
        tool = SemanticActionTool(browser_tool)

        si = _make_input()
        result = tool.execute(si)

        self.assertEqual(result["status"], "error")
        self.assertIn("Bad role", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
