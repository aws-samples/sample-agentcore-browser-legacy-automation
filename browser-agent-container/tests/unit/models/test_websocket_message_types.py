# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BrowserMessageType constants.
"""

import tests.__setup__  # noqa: F401
import unittest

from models.websocket_message_types import BrowserMessageType


# All 28 expected constants organized by direction
CLIENT_TO_SERVER = [
    "CONNECTION_INIT",
    "CHAT_MESSAGE",
    "BROWSER_STOP",
    "BROWSER_HITL_RESPONSE",
    "BROWSER_LIVE_VIEW_REQUEST",
    "NEW_SESSION",
    "RESUME_SESSION",
    "GET_SESSIONS",
    "DELETE_SESSION",
]

SERVER_CONNECTION_SESSION = [
    "CONNECTION_ESTABLISHED",
    "SESSION_CREATED",
    "SESSION_RESUMED",
    "SESSIONS_LOADED",
    "SESSION_DELETED",
]

SERVER_ORCHESTRATION = [
    "ORCHESTRATION_START",
    "ORCHESTRATION_END",
    "REASONING",
    "STREAM",
    "METADATA",
]

SERVER_BROWSER_SPECIFIC = [
    "BROWSER_SESSION_STARTED",
    "BROWSER_ACTION_START",
    "BROWSER_SCREENSHOT",
    "BROWSER_ACTION_COMPLETE",
    "BROWSER_HITL_PROMPT",
    "BROWSER_LIVE_VIEW_URL",
    "BROWSER_SESSION_ENDED",
    "BROWSER_HITL_TIMEOUT",
]

ERROR_TYPES = [
    "ERROR",
]

ALL_CONSTANTS = (
    CLIENT_TO_SERVER
    + SERVER_CONNECTION_SESSION
    + SERVER_ORCHESTRATION
    + SERVER_BROWSER_SPECIFIC
    + ERROR_TYPES
)


class TestBrowserMessageTypeConstants(unittest.TestCase):
    """Test all 28 constants are defined on BrowserMessageType."""

    def test_total_constant_count(self) -> None:
        """BrowserMessageType defines exactly 28 string constants."""
        string_attrs = [
            attr for attr in dir(BrowserMessageType)
            if not attr.startswith("_")
            and isinstance(getattr(BrowserMessageType, attr), str)
        ]
        self.assertEqual(len(string_attrs), 28)

    def test_all_expected_constants_exist(self) -> None:
        """Every expected constant name is defined as a class attribute."""
        for name in ALL_CONSTANTS:
            with self.subTest(constant=name):
                self.assertTrue(
                    hasattr(BrowserMessageType, name),
                    f"Missing constant: {name}",
                )


class TestBrowserMessageTypeValues(unittest.TestCase):
    """Test each constant value matches its attribute name."""

    def test_each_value_matches_attribute_name(self) -> None:
        """Every constant's value equals its attribute name."""
        for name in ALL_CONSTANTS:
            with self.subTest(constant=name):
                value = getattr(BrowserMessageType, name)
                self.assertEqual(
                    value, name,
                    f"{name} value is '{value}', expected '{name}'",
                )

    def test_all_values_are_strings(self) -> None:
        """Every constant value is a string."""
        for name in ALL_CONSTANTS:
            with self.subTest(constant=name):
                self.assertIsInstance(getattr(BrowserMessageType, name), str)


class TestBrowserMessageTypeClientToServer(unittest.TestCase):
    """Test client→server frame type constants."""

    def test_client_to_server_count(self) -> None:
        """9 client→server constants defined."""
        self.assertEqual(len(CLIENT_TO_SERVER), 9)

    def test_connection_init(self) -> None:
        self.assertEqual(BrowserMessageType.CONNECTION_INIT, "CONNECTION_INIT")

    def test_chat_message(self) -> None:
        self.assertEqual(BrowserMessageType.CHAT_MESSAGE, "CHAT_MESSAGE")

    def test_browser_stop(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_STOP, "BROWSER_STOP")

    def test_browser_hitl_response(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_HITL_RESPONSE, "BROWSER_HITL_RESPONSE")

    def test_browser_live_view_request(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST, "BROWSER_LIVE_VIEW_REQUEST")

    def test_new_session(self) -> None:
        self.assertEqual(BrowserMessageType.NEW_SESSION, "NEW_SESSION")

    def test_resume_session(self) -> None:
        self.assertEqual(BrowserMessageType.RESUME_SESSION, "RESUME_SESSION")

    def test_get_sessions(self) -> None:
        self.assertEqual(BrowserMessageType.GET_SESSIONS, "GET_SESSIONS")

    def test_delete_session(self) -> None:
        self.assertEqual(BrowserMessageType.DELETE_SESSION, "DELETE_SESSION")


class TestBrowserMessageTypeServerConnectionSession(unittest.TestCase):
    """Test server→client connection and session frame type constants."""

    def test_connection_established(self) -> None:
        self.assertEqual(BrowserMessageType.CONNECTION_ESTABLISHED, "CONNECTION_ESTABLISHED")

    def test_session_created(self) -> None:
        self.assertEqual(BrowserMessageType.SESSION_CREATED, "SESSION_CREATED")

    def test_session_resumed(self) -> None:
        self.assertEqual(BrowserMessageType.SESSION_RESUMED, "SESSION_RESUMED")

    def test_sessions_loaded(self) -> None:
        self.assertEqual(BrowserMessageType.SESSIONS_LOADED, "SESSIONS_LOADED")

    def test_session_deleted(self) -> None:
        self.assertEqual(BrowserMessageType.SESSION_DELETED, "SESSION_DELETED")


class TestBrowserMessageTypeOrchestration(unittest.TestCase):
    """Test server→client orchestration streaming frame type constants."""

    def test_orchestration_start(self) -> None:
        self.assertEqual(BrowserMessageType.ORCHESTRATION_START, "ORCHESTRATION_START")

    def test_orchestration_end(self) -> None:
        self.assertEqual(BrowserMessageType.ORCHESTRATION_END, "ORCHESTRATION_END")

    def test_reasoning(self) -> None:
        self.assertEqual(BrowserMessageType.REASONING, "REASONING")

    def test_stream(self) -> None:
        self.assertEqual(BrowserMessageType.STREAM, "STREAM")

    def test_metadata(self) -> None:
        self.assertEqual(BrowserMessageType.METADATA, "METADATA")


class TestBrowserMessageTypeBrowserSpecific(unittest.TestCase):
    """Test server→client browser-specific frame type constants."""

    def test_browser_session_started(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_SESSION_STARTED, "BROWSER_SESSION_STARTED")

    def test_browser_action_start(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_ACTION_START, "BROWSER_ACTION_START")

    def test_browser_screenshot(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_SCREENSHOT, "BROWSER_SCREENSHOT")

    def test_browser_action_complete(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_ACTION_COMPLETE, "BROWSER_ACTION_COMPLETE")

    def test_browser_hitl_prompt(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_HITL_PROMPT, "BROWSER_HITL_PROMPT")

    def test_browser_live_view_url(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_LIVE_VIEW_URL, "BROWSER_LIVE_VIEW_URL")

    def test_browser_session_ended(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_SESSION_ENDED, "BROWSER_SESSION_ENDED")

    def test_browser_hitl_timeout(self) -> None:
        self.assertEqual(BrowserMessageType.BROWSER_HITL_TIMEOUT, "BROWSER_HITL_TIMEOUT")


class TestBrowserMessageTypeError(unittest.TestCase):
    """Test error frame type constant."""

    def test_error(self) -> None:
        self.assertEqual(BrowserMessageType.ERROR, "ERROR")


if __name__ == "__main__":
    unittest.main()
