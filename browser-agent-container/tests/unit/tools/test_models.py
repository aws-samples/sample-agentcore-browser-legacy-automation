# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for SemanticActionInput Pydantic model.
"""

import unittest
from pydantic import ValidationError

from tools.models import SemanticActionInput


# Minimal valid kwargs for constructing a SemanticActionInput
_VALID_BASE = {
    "session_name": "my-session",
    "locator_type": "role",
    "action": "click",
}

VALID_LOCATOR_TYPES = [
    "role", "label", "text", "placeholder", "alt_text", "title", "test_id"
]

VALID_ACTIONS = [
    "click", "dblclick", "fill", "clear", "check", "uncheck",
    "select_option", "hover", "focus", "blur", "press",
    "press_sequentially", "set_input_files", "scroll_into_view",
    "get_text", "get_attribute", "get_value", "count", "is_visible",
]


class TestSessionNameValidation(unittest.TestCase):
    """Test session_name regex pattern validation."""

    def test_valid_session_names(self) -> None:
        """Valid lowercase alphanumeric + hyphens are accepted."""
        valid_names = ["my-session", "a", "abc-123", "test-session-1", "a-b-c"]
        for name in valid_names:
            si = SemanticActionInput(**{**_VALID_BASE, "session_name": name})
            self.assertEqual(si.session_name, name)

    def test_rejects_uppercase(self) -> None:
        """Uppercase letters are rejected."""
        with self.assertRaises(ValidationError):
            SemanticActionInput(**{**_VALID_BASE, "session_name": "MySession"})

    def test_rejects_spaces(self) -> None:
        """Spaces are rejected."""
        with self.assertRaises(ValidationError):
            SemanticActionInput(**{**_VALID_BASE, "session_name": "my session"})

    def test_rejects_underscores(self) -> None:
        """Underscores are rejected."""
        with self.assertRaises(ValidationError):
            SemanticActionInput(**{**_VALID_BASE, "session_name": "my_session"})

    def test_rejects_special_chars(self) -> None:
        """Special characters are rejected."""
        for char in ["@", "!", "#", "$", "%", ".", "/"]:
            with self.assertRaises(ValidationError, msg=f"Should reject '{char}'"):
                SemanticActionInput(**{**_VALID_BASE, "session_name": f"test{char}name"})

    def test_rejects_empty_string(self) -> None:
        """Empty string is rejected."""
        with self.assertRaises(ValidationError):
            SemanticActionInput(**{**_VALID_BASE, "session_name": ""})


class TestLocatorTypeValidation(unittest.TestCase):
    """Test locator_type Literal validation."""

    def test_all_valid_locator_types_accepted(self) -> None:
        """All 7 valid locator_type values are accepted."""
        for lt in VALID_LOCATOR_TYPES:
            si = SemanticActionInput(**{**_VALID_BASE, "locator_type": lt})
            self.assertEqual(si.locator_type, lt)

    def test_rejects_unknown_locator_type(self) -> None:
        """Unknown locator_type values are rejected."""
        for bad in ["css", "xpath", "id", "class", "unknown", ""]:
            with self.assertRaises(ValidationError, msg=f"Should reject '{bad}'"):
                SemanticActionInput(**{**_VALID_BASE, "locator_type": bad})


class TestActionValidation(unittest.TestCase):
    """Test action Literal validation."""

    def test_all_valid_actions_accepted(self) -> None:
        """All 19 valid action values are accepted."""
        for act in VALID_ACTIONS:
            si = SemanticActionInput(**{**_VALID_BASE, "action": act})
            self.assertEqual(si.action, act)

    def test_rejects_unknown_action(self) -> None:
        """Unknown action values are rejected."""
        for bad in ["submit", "drag", "drop", "type", "unknown", ""]:
            with self.assertRaises(ValidationError, msg=f"Should reject '{bad}'"):
                SemanticActionInput(**{**_VALID_BASE, "action": bad})


class TestFieldDefaults(unittest.TestCase):
    """Test field defaults and optional fields."""

    def test_exact_defaults_to_false(self) -> None:
        """exact field defaults to False."""
        si = SemanticActionInput(**_VALID_BASE)
        self.assertFalse(si.exact)

    def test_title_text_field_exists(self) -> None:
        """title_text field exists and accepts a value."""
        si = SemanticActionInput(**{**_VALID_BASE, "title_text": "tooltip"})
        self.assertEqual(si.title_text, "tooltip")

    def test_optional_fields_accept_none(self) -> None:
        """All optional fields default to None."""
        si = SemanticActionInput(**_VALID_BASE)
        optional_fields = [
            "role", "name", "label", "text", "placeholder", "alt_text",
            "title_text", "test_id", "checked", "disabled", "expanded",
            "pressed", "selected", "level", "include_hidden",
            "filter_text", "filter_not_text", "nth", "frame_selector",
            "value", "option_label", "option_index", "attribute_name",
            "files", "key", "button", "click_count", "delay",
            "modifiers", "timeout", "force",
        ]
        for field_name in optional_fields:
            self.assertIsNone(
                getattr(si, field_name),
                msg=f"Field '{field_name}' should default to None",
            )

    def test_role_specific_filters_accepted(self) -> None:
        """Role-specific filter fields accept values."""
        si = SemanticActionInput(
            **{
                **_VALID_BASE,
                "checked": True,
                "disabled": False,
                "expanded": True,
                "pressed": False,
                "selected": True,
                "level": 2,
                "include_hidden": True,
            }
        )
        self.assertTrue(si.checked)
        self.assertFalse(si.disabled)
        self.assertTrue(si.expanded)
        self.assertFalse(si.pressed)
        self.assertTrue(si.selected)
        self.assertEqual(si.level, 2)
        self.assertTrue(si.include_hidden)

    def test_modifiers_accepts_valid_values(self) -> None:
        """modifiers field accepts valid Literal values."""
        si = SemanticActionInput(
            **{**_VALID_BASE, "modifiers": ["Shift", "Control"]}
        )
        self.assertEqual(si.modifiers, ["Shift", "Control"])

    def test_modifiers_rejects_invalid_values(self) -> None:
        """modifiers field rejects invalid values."""
        with self.assertRaises(ValidationError):
            SemanticActionInput(**{**_VALID_BASE, "modifiers": ["CapsLock"]})

    def test_files_accepts_list(self) -> None:
        """files field accepts a list of strings."""
        si = SemanticActionInput(
            **{**_VALID_BASE, "action": "set_input_files", "files": ["/tmp/a.txt"]}
        )
        self.assertEqual(si.files, ["/tmp/a.txt"])


if __name__ == "__main__":
    unittest.main()
