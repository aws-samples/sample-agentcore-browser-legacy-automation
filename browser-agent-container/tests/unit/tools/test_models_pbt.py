# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for SemanticActionInput Pydantic model.

Feature: 86-browser-agent-core-tools, Property 1: Session name regex validation
Feature: 86-browser-agent-core-tools, Property 2: Literal field validation rejects unknown values
Validates: Requirements 1.1, 1.2, 1.8
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.tools.__setup__
# pylint: enable=import-error,unused-import

import re
import unittest

from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import ValidationError

from tools.models import SemanticActionInput


# ── Constants ────────────────────────────────────────────────────────────
# Use \Z instead of $ to match Pydantic's Rust regex engine behaviour
# (Python $ matches before a trailing newline; \Z is strict end-of-string)
SESSION_NAME_REGEX = re.compile(r"^[a-z0-9-]+\Z")

VALID_LOCATOR_TYPES = frozenset([
    "role", "label", "text", "placeholder", "alt_text", "title", "test_id",
])

VALID_ACTIONS = frozenset([
    "click", "dblclick", "fill", "clear", "check", "uncheck",
    "select_option", "hover", "focus", "blur", "press",
    "press_sequentially", "set_input_files", "scroll_into_view",
    "get_text", "get_attribute", "get_value", "count", "is_visible",
])

_VALID_BASE = {
    "session_name": "test-session",
    "locator_type": "role",
    "action": "click",
}


class TestSessionNameRegexProperty(unittest.TestCase):
    """Property 1: Session name regex validation.

    For any string, SemanticActionInput accepts it as session_name
    iff it matches ^[a-z0-9-]+$.
    """

    # Feature: 86-browser-agent-core-tools, Property 1: Session name regex validation
    @settings(max_examples=100)
    @given(candidate=st.text(min_size=0, max_size=50))
    def test_prop_session_name_accepted_iff_regex_matches(self, candidate: str) -> None:
        """session_name is accepted iff it matches ^[a-z0-9-]+$.

        Validates: Requirements 1.1
        """
        should_accept = bool(SESSION_NAME_REGEX.match(candidate))

        if should_accept:
            si = SemanticActionInput(**{**_VALID_BASE, "session_name": candidate})
            self.assertEqual(si.session_name, candidate)
        else:
            with self.assertRaises(ValidationError):
                SemanticActionInput(**{**_VALID_BASE, "session_name": candidate})


class TestLiteralFieldValidationProperty(unittest.TestCase):
    """Property 2: Literal field validation rejects unknown values.

    For any string not in the valid locator types or action types,
    SemanticActionInput rejects it. All valid values are accepted.
    """

    # Feature: 86-browser-agent-core-tools, Property 2: Literal field validation rejects unknown values
    @settings(max_examples=100)
    @given(candidate=st.text(min_size=1, max_size=30))
    def test_prop_unknown_locator_type_rejected(self, candidate: str) -> None:
        """Unknown locator_type values are rejected; valid ones accepted.

        Validates: Requirements 1.2
        """
        if candidate in VALID_LOCATOR_TYPES:
            si = SemanticActionInput(**{**_VALID_BASE, "locator_type": candidate})
            self.assertEqual(si.locator_type, candidate)
        else:
            with self.assertRaises(ValidationError):
                SemanticActionInput(**{**_VALID_BASE, "locator_type": candidate})

    # Feature: 86-browser-agent-core-tools, Property 2: Literal field validation rejects unknown values
    @settings(max_examples=100)
    @given(candidate=st.text(min_size=1, max_size=30))
    def test_prop_unknown_action_rejected(self, candidate: str) -> None:
        """Unknown action values are rejected; valid ones accepted.

        Validates: Requirements 1.8
        """
        if candidate in VALID_ACTIONS:
            si = SemanticActionInput(**{**_VALID_BASE, "action": candidate})
            self.assertEqual(si.action, candidate)
        else:
            with self.assertRaises(ValidationError):
                SemanticActionInput(**{**_VALID_BASE, "action": candidate})

    def test_all_valid_locator_types_accepted(self) -> None:
        """Exhaustive check: all 7 valid locator types are accepted."""
        for lt in VALID_LOCATOR_TYPES:
            si = SemanticActionInput(**{**_VALID_BASE, "locator_type": lt})
            self.assertEqual(si.locator_type, lt)

    def test_all_valid_actions_accepted(self) -> None:
        """Exhaustive check: all 19 valid actions are accepted."""
        for act in VALID_ACTIONS:
            si = SemanticActionInput(**{**_VALID_BASE, "action": act})
            self.assertEqual(si.action, act)


if __name__ == "__main__":
    unittest.main()
