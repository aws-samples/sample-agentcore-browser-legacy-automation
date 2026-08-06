# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for SemanticActionTool.

Feature: 86-browser-agent-core-tools, Property 5: Locator dispatch calls correct Playwright method with parameters
Feature: 86-browser-agent-core-tools, Property 6: Read actions return value in text content
Feature: 86-browser-agent-core-tools, Property 7: Semantic action exceptions produce error results
Validates: Requirements 3.3, 3.4, 3.5, 3.10, 3.11
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import unittest
from unittest.mock import MagicMock

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from tools.models import SemanticActionInput
from tools.semantic_action_tool import SemanticActionTool


# ── Strategies ───────────────────────────────────────────────────────────

LOCATOR_TYPES = ["role", "label", "text", "placeholder", "alt_text", "title", "test_id"]

LOCATOR_TO_METHOD = {
    "role": "get_by_role",
    "label": "get_by_label",
    "text": "get_by_text",
    "placeholder": "get_by_placeholder",
    "alt_text": "get_by_alt_text",
    "title": "get_by_title",
    "test_id": "get_by_test_id",
}

# Locator types that receive the exact parameter
EXACT_LOCATOR_TYPES = {"label", "text", "placeholder", "alt_text", "title"}

READ_ACTIONS = ["get_text", "get_attribute", "get_value", "count", "is_visible"]

# Strategy for safe locator text (non-empty, no null bytes)
safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1, max_size=50,
)


def _build_input_for_locator(locator_type: str, locator_value: str, exact: bool) -> dict:
    """Build a minimal SemanticActionInput dict for a given locator_type."""
    base = {
        "session_name": "prop-session",
        "locator_type": locator_type,
        "action": "click",
        "exact": exact,
    }
    if locator_type == "role":
        base["role"] = "button"
        base["name"] = locator_value
    elif locator_type == "label":
        base["label"] = locator_value
    elif locator_type == "text":
        base["text"] = locator_value
    elif locator_type == "placeholder":
        base["placeholder"] = locator_value
    elif locator_type == "alt_text":
        base["alt_text"] = locator_value
    elif locator_type == "title":
        base["title_text"] = locator_value
    elif locator_type == "test_id":
        base["test_id"] = locator_value
    return base


class TestLocatorDispatchProperty(unittest.TestCase):
    """Property 5: Locator dispatch calls correct Playwright method with parameters.

    For any valid SemanticActionInput with a given locator_type, the
    SemanticActionTool._build_locator() method should call the corresponding
    Playwright locator method, passing exact for non-role/non-test_id types
    and role-specific filters for the role type.
    """

    # Feature: 86-browser-agent-core-tools, Property 5: Locator dispatch calls correct Playwright method with parameters
    @settings(max_examples=100)
    @given(
        locator_type=st.sampled_from(LOCATOR_TYPES),
        locator_value=safe_text,
        exact=st.booleans(),
    )
    def test_prop_locator_dispatch_calls_correct_method(
        self, locator_type: str, locator_value: str, exact: bool,
    ) -> None:
        """Correct get_by_* method is called for each locator_type.

        Validates: Requirements 3.3, 3.4, 3.5
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = None
        tool = SemanticActionTool(browser_tool)

        input_dict = _build_input_for_locator(locator_type, locator_value, exact)
        si = SemanticActionInput(**input_dict)
        tool.execute(si)

        expected_method = LOCATOR_TO_METHOD[locator_type]
        method_mock = getattr(mock_page, expected_method)
        method_mock.assert_called_once()

    # Feature: 86-browser-agent-core-tools, Property 5: Locator dispatch calls correct Playwright method with parameters
    @settings(max_examples=100)
    @given(
        locator_type=st.sampled_from(list(EXACT_LOCATOR_TYPES)),
        locator_value=safe_text,
        exact=st.booleans(),
    )
    def test_prop_exact_passed_for_non_role_non_test_id(
        self, locator_type: str, locator_value: str, exact: bool,
    ) -> None:
        """exact parameter is passed for label, text, placeholder, alt_text, title.

        Validates: Requirements 3.5
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = None
        tool = SemanticActionTool(browser_tool)

        input_dict = _build_input_for_locator(locator_type, locator_value, exact)
        si = SemanticActionInput(**input_dict)
        tool.execute(si)

        expected_method = LOCATOR_TO_METHOD[locator_type]
        method_mock = getattr(mock_page, expected_method)
        call_kwargs = method_mock.call_args.kwargs
        self.assertIn("exact", call_kwargs)
        self.assertEqual(call_kwargs["exact"], exact)

    # Feature: 86-browser-agent-core-tools, Property 5: Locator dispatch calls correct Playwright method with parameters
    @settings(max_examples=100)
    @given(
        name=safe_text,
        checked=st.one_of(st.none(), st.booleans()),
        disabled=st.one_of(st.none(), st.booleans()),
        expanded=st.one_of(st.none(), st.booleans()),
        level=st.one_of(st.none(), st.integers(min_value=1, max_value=6)),
    )
    def test_prop_role_filters_passed_to_get_by_role(
        self, name: str, checked, disabled, expanded, level,
    ) -> None:
        """Role-specific filters are passed as kwargs to get_by_role.

        Validates: Requirements 3.4
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = None
        tool = SemanticActionTool(browser_tool)

        si = SemanticActionInput(
            session_name="prop-session",
            locator_type="role",
            role="checkbox",
            name=name,
            action="click",
            checked=checked,
            disabled=disabled,
            expanded=expanded,
            level=level,
        )
        tool.execute(si)

        call_kwargs = mock_page.get_by_role.call_args.kwargs
        # name is always passed when provided
        self.assertEqual(call_kwargs["name"], name)
        # exact is NOT passed for role
        self.assertNotIn("exact", call_kwargs)
        # Non-None filters are passed
        if checked is not None:
            self.assertEqual(call_kwargs["checked"], checked)
        else:
            self.assertNotIn("checked", call_kwargs)
        if disabled is not None:
            self.assertEqual(call_kwargs["disabled"], disabled)
        else:
            self.assertNotIn("disabled", call_kwargs)
        if expanded is not None:
            self.assertEqual(call_kwargs["expanded"], expanded)
        else:
            self.assertNotIn("expanded", call_kwargs)
        if level is not None:
            self.assertEqual(call_kwargs["level"], level)
        else:
            self.assertNotIn("level", call_kwargs)


class TestReadActionsReturnValueProperty(unittest.TestCase):
    """Property 6: Read actions return value in text content.

    For any read action, the result should have status: "success" and
    text content that includes the value returned by the Playwright method.
    """

    # Feature: 86-browser-agent-core-tools, Property 6: Read actions return value in text content
    @settings(max_examples=100)
    @given(
        action=st.sampled_from(READ_ACTIONS),
        return_value=safe_text,
    )
    def test_prop_read_actions_return_value_in_text(
        self, action: str, return_value: str,
    ) -> None:
        """Read actions include the returned value in the text content.

        Validates: Requirements 3.10
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.return_value = return_value
        tool = SemanticActionTool(browser_tool)

        input_dict = {
            "session_name": "prop-session",
            "locator_type": "role",
            "role": "button",
            "name": "Test",
            "action": action,
        }
        if action == "get_attribute":
            input_dict["attribute_name"] = "href"

        si = SemanticActionInput(**input_dict)
        result = tool.execute(si)

        self.assertEqual(result["status"], "success")
        text_content = result["content"][0]["text"]
        self.assertIn(str(return_value), text_content)


class TestActionExceptionsProperty(unittest.TestCase):
    """Property 7: Semantic action exceptions produce error results.

    For any exception raised during a Playwright locator action, the result
    should have status: "error" and text containing the exception message.
    """

    # Feature: 86-browser-agent-core-tools, Property 7: Semantic action exceptions produce error results
    @settings(max_examples=100)
    @given(
        error_message=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",), blacklist_characters="\x00"
            ),
            min_size=1, max_size=100,
        ),
    )
    def test_prop_action_exceptions_produce_errors(self, error_message: str) -> None:
        """Any exception during action produces an error result with the message.

        Validates: Requirements 3.11
        """
        browser_tool = MagicMock()
        browser_tool.validate_session.return_value = None
        mock_page = MagicMock()
        browser_tool.get_session_page.return_value = mock_page
        browser_tool._execute_async.side_effect = RuntimeError(error_message)
        tool = SemanticActionTool(browser_tool)

        si = SemanticActionInput(
            session_name="prop-session",
            locator_type="role",
            role="button",
            name="Test",
            action="click",
        )
        result = tool.execute(si)

        self.assertEqual(result["status"], "error")
        self.assertIn(error_message, result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
