# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for BrowserHandler.

Properties:
  1: Session ID format (Req 17.2)
  10: Session name validation maps to active session (Req 6.8)
  11: Concurrent message rejection during automation (Req 7.1)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.handlers.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import re
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from handlers.browser_handler import BrowserHandler
from handlers.session_store import InMemorySessionStore
from handlers.screenshot_storage import LocalScreenshotStorage
from models.websocket_message_types import BrowserMessageType


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------- Helpers ----------

SESSION_ID_PATTERN = re.compile(r"^brws_(\d{8})_(\d{6})_([0-9a-f]{8})$")


def _make_handler(active_session=None, automation_in_progress=False):
    """Create a BrowserHandler with minimal mocks."""
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.closed = False

    handler = BrowserHandler(
        websocket=mock_ws,
        agent_factory=MagicMock(),
        session_store=InMemorySessionStore(),
        screenshot_storage=LocalScreenshotStorage(base_dir="/tmp/test"),
        profile="browser",
        user_id="test_user",
    )
    handler.active_browser_session_name = active_session
    handler.automation_in_progress = automation_in_progress
    return handler, mock_ws



# ============================================================
# Property 1: Session ID format
# Feature: 86-browser-agent-container-deployment, Property 1: Session ID format
# Validates: Requirements 17.2
# ============================================================

class TestSessionIdFormatProperty(unittest.TestCase):
    """Property 1: Session ID format."""

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_session_id_matches_format(self, _iteration: int) -> None:
        """Every generated session ID matches brws_{YYYYMMDD}_{HHMMSS}_{hex8}."""
        sid = BrowserHandler._generate_session_id()
        match = SESSION_ID_PATTERN.match(sid)
        self.assertIsNotNone(match, "Session ID '%s' does not match pattern" % sid)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_date_component_is_valid(self, _iteration: int) -> None:
        """The YYYYMMDD component is a valid date."""
        sid = BrowserHandler._generate_session_id()
        match = SESSION_ID_PATTERN.match(sid)
        self.assertIsNotNone(match)
        date_str = match.group(1)
        try:
            datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            self.fail("Invalid date component: %s" % date_str)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_time_component_is_valid(self, _iteration: int) -> None:
        """The HHMMSS component has valid hour/minute/second ranges."""
        sid = BrowserHandler._generate_session_id()
        match = SESSION_ID_PATTERN.match(sid)
        self.assertIsNotNone(match)
        time_str = match.group(2)
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        self.assertLessEqual(hour, 23)
        self.assertLessEqual(minute, 59)
        self.assertLessEqual(second, 59)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_hex_component_is_8_chars(self, _iteration: int) -> None:
        """The hex component is exactly 8 lowercase hex characters."""
        sid = BrowserHandler._generate_session_id()
        match = SESSION_ID_PATTERN.match(sid)
        self.assertIsNotNone(match)
        hex_part = match.group(3)
        self.assertEqual(len(hex_part), 8)
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_part))

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=49))
    def test_session_ids_are_unique(self, _iteration: int) -> None:
        """Two consecutive calls produce different session IDs."""
        id1 = BrowserHandler._generate_session_id()
        id2 = BrowserHandler._generate_session_id()
        self.assertNotEqual(id1, id2)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_prefix_is_brws(self, _iteration: int) -> None:
        """Every session ID starts with 'brws_'."""
        sid = BrowserHandler._generate_session_id()
        self.assertTrue(sid.startswith("brws_"))


# ============================================================
# Property 10: Session name validation maps to active session
# Feature: 86-browser-agent-container-deployment, Property 10: Session name validation
# Validates: Requirements 6.8
# ============================================================

class TestSessionNameValidationProperty(unittest.TestCase):
    """Property 10: Session name validation maps to active session."""

    @settings(max_examples=100)
    @given(
        input_name=st.text(min_size=1, max_size=100),
        active_name=st.text(min_size=1, max_size=50),
    )
    def test_any_name_maps_to_active_session(
        self, input_name: str, active_name: str
    ) -> None:
        """Any input name maps to the active browser session when one exists."""
        handler, _ = _make_handler(active_session=active_name)
        result = handler._validate_session_name(input_name)
        self.assertEqual(result, active_name)

    @settings(max_examples=100)
    @given(input_name=st.text(min_size=0, max_size=100))
    def test_returns_input_when_no_active_session(self, input_name: str) -> None:
        """Input name is returned unchanged when no active session exists."""
        handler, _ = _make_handler(active_session=None)
        result = handler._validate_session_name(input_name)
        self.assertEqual(result, input_name)

    @settings(max_examples=100)
    @given(
        name_a=st.text(min_size=1, max_size=50),
        name_b=st.text(min_size=1, max_size=50),
        active=st.text(min_size=1, max_size=50),
    )
    def test_different_inputs_same_output_when_active(
        self, name_a: str, name_b: str, active: str
    ) -> None:
        """Different input names all map to the same active session."""
        handler, _ = _make_handler(active_session=active)
        result_a = handler._validate_session_name(name_a)
        result_b = handler._validate_session_name(name_b)
        self.assertEqual(result_a, result_b)
        self.assertEqual(result_a, active)

    @settings(max_examples=100)
    @given(active=st.text(min_size=1, max_size=50))
    def test_active_session_name_returned_for_empty_input(
        self, active: str
    ) -> None:
        """Even empty string input maps to active session."""
        handler, _ = _make_handler(active_session=active)
        result = handler._validate_session_name("")
        self.assertEqual(result, active)


# ============================================================
# Property 11: Concurrent message rejection during automation
# Feature: 86-browser-agent-container-deployment, Property 11: Concurrent message rejection
# Validates: Requirements 7.1
# ============================================================

class TestConcurrentMessageRejectionProperty(unittest.TestCase):
    """Property 11: Concurrent message rejection during automation.

    As of Issue 5 (see ``.kiro/research/temp-browser-ui-issues-analysis.md``),
    the concurrent-chat rejection lives in ``_dispatch`` rather than at the
    top of ``_handle_chat_message``, so these properties must route through
    ``_dispatch`` to exercise the rejection path.
    """

    @settings(max_examples=100)
    @given(content=st.text(min_size=0, max_size=500))
    def test_chat_rejected_during_automation(self, content: str) -> None:
        """Any CHAT_MESSAGE during automation produces an ERROR frame."""
        handler, mock_ws = _make_handler(automation_in_progress=True)
        run_async(handler._dispatch(
            BrowserMessageType.CHAT_MESSAGE, {"content": content},
        ))

        mock_ws.send_json.assert_awaited_once()
        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.ERROR)
        self.assertIn("Automation in progress", frame["content"])
        self.assertTrue(frame["recoverable"])

    @settings(max_examples=100)
    @given(content=st.text(min_size=0, max_size=500))
    def test_automation_flag_unchanged_after_rejection(self, content: str) -> None:
        """automation_in_progress remains True after rejection."""
        handler, _ = _make_handler(automation_in_progress=True)
        run_async(handler._dispatch(
            BrowserMessageType.CHAT_MESSAGE, {"content": content},
        ))
        self.assertTrue(handler.automation_in_progress)

    @settings(max_examples=100)
    @given(n_messages=st.integers(min_value=1, max_value=10))
    def test_multiple_concurrent_messages_all_rejected(
        self, n_messages: int
    ) -> None:
        """Multiple concurrent CHAT_MESSAGEs are all rejected."""
        handler, mock_ws = _make_handler(automation_in_progress=True)
        for i in range(n_messages):
            run_async(handler._dispatch(
                BrowserMessageType.CHAT_MESSAGE, {"content": "msg %d" % i},
            ))

        self.assertEqual(mock_ws.send_json.await_count, n_messages)
        for call in mock_ws.send_json.call_args_list:
            frame = call[0][0]
            self.assertEqual(frame["type"], BrowserMessageType.ERROR)
            self.assertIn("Automation in progress", frame["content"])

    @settings(max_examples=100)
    @given(content=st.text(min_size=0, max_size=200))
    def test_no_agent_created_during_rejection(self, content: str) -> None:
        """No agent is created when message is rejected."""
        handler, _ = _make_handler(automation_in_progress=True)
        factory = handler.agent_factory
        run_async(handler._dispatch(
            BrowserMessageType.CHAT_MESSAGE, {"content": content},
        ))
        factory.create_agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
