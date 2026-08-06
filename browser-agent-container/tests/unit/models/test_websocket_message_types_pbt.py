# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Feature: 86-browser-agent-core-tools, Property 11: BrowserMessageType constant values match attribute names
"""Property-based test: BrowserMessageType constant values match attribute names.

Validates: Requirements 8.6
"""

import tests.__setup__  # noqa: F401
import unittest

from hypothesis import given, settings, strategies as st

from models.websocket_message_types import BrowserMessageType


# Collect all class-level string constants (exclude dunder and non-string attrs)
_ALL_CONSTANT_NAMES = [
    attr for attr in dir(BrowserMessageType)
    if not attr.startswith("_")
    and isinstance(getattr(BrowserMessageType, attr), str)
]


class TestPropertyBrowserMessageTypeValues(unittest.TestCase):
    """Property 11: Every class-level string constant has value identical to its attribute name."""

    @given(index=st.integers(min_value=0, max_value=max(len(_ALL_CONSTANT_NAMES) - 1, 0)))
    @settings(max_examples=100)
    def test_prop_message_type_values(self, index: int) -> None:
        """For any constant selected by index, its value equals its attribute name."""
        attr_name = _ALL_CONSTANT_NAMES[index]
        attr_value = getattr(BrowserMessageType, attr_name)
        self.assertEqual(
            attr_value, attr_name,
            f"BrowserMessageType.{attr_name} = '{attr_value}', expected '{attr_name}'",
        )

    def test_exhaustive_all_values_match_names(self) -> None:
        """Exhaustive check: every string constant value matches its attribute name."""
        for attr_name in _ALL_CONSTANT_NAMES:
            with self.subTest(constant=attr_name):
                attr_value = getattr(BrowserMessageType, attr_name)
                self.assertEqual(attr_value, attr_name)

    def test_all_constants_are_uppercase(self) -> None:
        """All constant names are uppercase (convention check)."""
        for attr_name in _ALL_CONSTANT_NAMES:
            with self.subTest(constant=attr_name):
                self.assertEqual(attr_name, attr_name.upper())


if __name__ == "__main__":
    unittest.main()
