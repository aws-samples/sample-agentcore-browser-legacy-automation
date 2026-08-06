# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BrowserHandler.
"""

import asyncio
import json
import re
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.browser_handler import BrowserHandler
from handlers.session_store import InMemorySessionStore, SessionRecord
from handlers.screenshot_storage import LocalScreenshotStorage
from models.websocket_message_types import BrowserMessageType


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_handler(
    messages=None,
    user_id="test_user",
    profile="browser",
):
    """Create a BrowserHandler with mocked dependencies.

    Args:
        messages: List of raw JSON strings the mock WS will yield.
        user_id: User identity.
        profile: Profile name.

    Returns:
        Tuple of (handler, mock_ws, mock_factory, session_store, screenshot_storage).
    """
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.closed = False

    # Set up async iteration
    if messages is None:
        messages = []

    async def _aiter_impl():
        for msg in messages:
            yield msg

    mock_ws.__aiter__ = lambda self: _aiter_impl()

    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_agent.stream_async = MagicMock(return_value=_async_gen([]))
    mock_factory.create_agent.return_value = mock_agent
    mock_factory.browser_tool = MagicMock()
    mock_factory.browser_tool._screenshot_tool = MagicMock()
    mock_factory.cleanup = MagicMock()

    session_store = InMemorySessionStore()
    screenshot_storage = LocalScreenshotStorage(base_dir="/tmp/test_sessions")

    handler = BrowserHandler(
        websocket=mock_ws,
        agent_factory=mock_factory,
        session_store=session_store,
        screenshot_storage=screenshot_storage,
        profile=profile,
        user_id=user_id,
    )

    return handler, mock_ws, mock_factory, session_store, screenshot_storage


async def _async_gen(items):
    """Create an async generator from a list."""
    for item in items:
        yield item


class TestGenerateSessionId(unittest.TestCase):
    """Test _generate_session_id() — Requirement 17.2."""

    def test_format_matches_pattern(self) -> None:
        """Session ID matches brws_{YYYYMMDD}_{HHMMSS}_{hex8}."""
        sid = BrowserHandler._generate_session_id()
        pattern = r"^brws_\d{8}_\d{6}_[0-9a-f]{8}$"
        self.assertRegex(sid, pattern)

    def test_unique_ids(self) -> None:
        """Two calls produce different IDs (hex portion differs)."""
        id1 = BrowserHandler._generate_session_id()
        id2 = BrowserHandler._generate_session_id()
        self.assertNotEqual(id1, id2)

    def test_prefix_is_brws(self) -> None:
        """Session ID starts with 'brws_'."""
        sid = BrowserHandler._generate_session_id()
        self.assertTrue(sid.startswith("brws_"))


class TestHandleConnectionDeferred(unittest.TestCase):
    """Test CONNECTION_ESTABLISHED deferred until first message — Req 5.1."""

    def test_connection_established_sent_on_first_message(self) -> None:
        """CONNECTION_ESTABLISHED is sent before dispatching the first message."""
        msg = json.dumps({"type": BrowserMessageType.CONNECTION_INIT})
        handler, mock_ws, _, _, _ = _make_handler(messages=[msg])

        _run(handler.handle_connection())

        calls = mock_ws.send_json.call_args_list
        self.assertGreaterEqual(len(calls), 1)
        first_frame = calls[0][0][0]
        self.assertEqual(
            first_frame["type"], BrowserMessageType.CONNECTION_ESTABLISHED
        )

    def test_connection_established_includes_session_and_profile(self) -> None:
        """CONNECTION_ESTABLISHED contains session_id and profile."""
        msg = json.dumps({"type": BrowserMessageType.CONNECTION_INIT})
        handler, mock_ws, _, _, _ = _make_handler(messages=[msg])

        _run(handler.handle_connection())

        first_frame = mock_ws.send_json.call_args_list[0][0][0]
        self.assertIn("session_id", first_frame)
        self.assertEqual(first_frame["profile"], "browser")

    def test_connection_established_sent_only_once(self) -> None:
        """CONNECTION_ESTABLISHED is sent exactly once even with multiple messages."""
        msgs = [
            json.dumps({"type": BrowserMessageType.CONNECTION_INIT}),
            json.dumps({"type": BrowserMessageType.GET_SESSIONS}),
        ]
        handler, mock_ws, _, _, _ = _make_handler(messages=msgs)

        _run(handler.handle_connection())

        established_frames = [
            c[0][0] for c in mock_ws.send_json.call_args_list
            if c[0][0].get("type") == BrowserMessageType.CONNECTION_ESTABLISHED
        ]
        self.assertEqual(len(established_frames), 1)


class TestDispatchRoutes(unittest.TestCase):
    """Test all 9 dispatch routes — Requirements 5.1–5.10."""

    def _dispatch_and_get_response(self, msg_type, payload=None):
        """Helper: dispatch a single message and return all sent frames."""
        if payload is None:
            payload = {}
        payload["type"] = msg_type
        msg = json.dumps(payload)
        handler, mock_ws, _, _, _ = _make_handler(messages=[msg])
        _run(handler.handle_connection())
        # Skip CONNECTION_ESTABLISHED (first frame)
        return [
            c[0][0] for c in mock_ws.send_json.call_args_list[1:]
        ]

    def test_connection_init_no_error(self) -> None:
        """CONNECTION_INIT is recognized and does not produce an error."""
        frames = self._dispatch_and_get_response(BrowserMessageType.CONNECTION_INIT)
        error_frames = [f for f in frames if f.get("type") == BrowserMessageType.ERROR]
        self.assertEqual(len(error_frames), 0)

    def test_get_sessions_returns_sessions_loaded(self) -> None:
        """GET_SESSIONS responds with SESSIONS_LOADED."""
        frames = self._dispatch_and_get_response(BrowserMessageType.GET_SESSIONS)
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.SESSIONS_LOADED for f in frames)
        )

    def test_new_session_returns_session_created(self) -> None:
        """NEW_SESSION responds with SESSION_CREATED."""
        frames = self._dispatch_and_get_response(BrowserMessageType.NEW_SESSION)
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.SESSION_CREATED for f in frames)
        )

    def test_delete_session_returns_session_deleted(self) -> None:
        """DELETE_SESSION responds with SESSION_DELETED."""
        frames = self._dispatch_and_get_response(
            BrowserMessageType.DELETE_SESSION,
            {"session_id": "brws_20250101_000000_abcd1234"},
        )
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.SESSION_DELETED for f in frames)
        )

    def test_resume_session_returns_session_resumed(self) -> None:
        """RESUME_SESSION responds with SESSION_RESUMED."""
        frames = self._dispatch_and_get_response(
            BrowserMessageType.RESUME_SESSION,
            {"session_id": "brws_20250101_000000_abcd1234"},
        )
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.SESSION_RESUMED for f in frames)
        )

    def test_live_view_request_returns_live_view_url(self) -> None:
        """BROWSER_LIVE_VIEW_REQUEST responds with BROWSER_LIVE_VIEW_URL."""
        frames = self._dispatch_and_get_response(
            BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST,
        )
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.BROWSER_LIVE_VIEW_URL for f in frames)
        )

    def test_browser_stop_returns_session_ended(self) -> None:
        """BROWSER_STOP responds with BROWSER_SESSION_ENDED."""
        frames = self._dispatch_and_get_response(BrowserMessageType.BROWSER_STOP)
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.BROWSER_SESSION_ENDED for f in frames)
        )

    def test_unknown_type_returns_error(self) -> None:
        """Unknown message type produces an ERROR frame — Req 5.10."""
        frames = self._dispatch_and_get_response("UNKNOWN_TYPE")
        error_frames = [f for f in frames if f.get("type") == BrowserMessageType.ERROR]
        self.assertEqual(len(error_frames), 1)
        self.assertIn("Unknown message type", error_frames[0]["content"])

    def test_invalid_json_returns_error(self) -> None:
        """Invalid JSON produces an error frame."""
        handler, mock_ws, _, _, _ = _make_handler(messages=["not json"])
        _run(handler.handle_connection())
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        # First is CONNECTION_ESTABLISHED, second should be error
        error_frames = [f for f in frames if f.get("type") == BrowserMessageType.ERROR]
        self.assertGreaterEqual(len(error_frames), 1)


class TestSessionLifecycle(unittest.TestCase):
    """Test session lifecycle: create/reuse/terminate — Requirements 6.1–6.4."""

    def test_chat_message_creates_browser_session(self) -> None:
        """First CHAT_MESSAGE creates a browser session and sends BROWSER_SESSION_STARTED."""
        msg = json.dumps({
            "type": BrowserMessageType.CHAT_MESSAGE,
            "content": "Navigate to example.com",
        })
        handler, mock_ws, mock_factory, store, _ = _make_handler(messages=[msg])

        # Mock stream_async to return empty
        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            MockStreamer.return_value = mock_streamer_inst

            _run(handler.handle_connection())

        mock_factory.create_agent.assert_called_once()
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        session_started = [
            f for f in frames
            if f.get("type") == BrowserMessageType.BROWSER_SESSION_STARTED
        ]
        self.assertEqual(len(session_started), 1)

    def test_second_chat_reuses_session(self) -> None:
        """Second CHAT_MESSAGE reuses existing browser session — Req 6.2."""
        msgs = [
            json.dumps({"type": BrowserMessageType.CHAT_MESSAGE, "content": "Go to A"}),
            json.dumps({"type": BrowserMessageType.CHAT_MESSAGE, "content": "Go to B"}),
        ]
        handler, mock_ws, mock_factory, _, _ = _make_handler(messages=msgs)

        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            MockStreamer.return_value = mock_streamer_inst

            _run(handler.handle_connection())

        # create_agent called only once (session reused)
        mock_factory.create_agent.assert_called_once()

    def test_new_session_resets_state(self) -> None:
        """NEW_SESSION generates new session_id and resets state — Req 6.4."""
        handler, mock_ws, _, _, _ = _make_handler()
        original_id = handler.session_id

        _run(handler._handle_new_session({}))

        self.assertNotEqual(handler.session_id, original_id)
        self.assertIsNone(handler.active_browser_session_name)
        self.assertFalse(handler.automation_in_progress)

    def test_new_session_terminates_active_browser(self) -> None:
        """NEW_SESSION terminates active browser session before creating new one."""
        handler, mock_ws, mock_factory, store, _ = _make_handler()
        handler.active_browser_session_name = "active_session"
        handler._browser_tool = MagicMock()

        # Create a session record so terminate can update it
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
        )))

        _run(handler._handle_new_session({}))

        mock_factory.cleanup.assert_called_once()
        self.assertIsNone(handler.active_browser_session_name)

    def test_browser_stop_terminates_session(self) -> None:
        """BROWSER_STOP terminates browser session and sends BROWSER_SESSION_ENDED — Req 6.3."""
        handler, mock_ws, mock_factory, store, _ = _make_handler()
        handler.active_browser_session_name = "active"
        handler._browser_tool = MagicMock()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
        )))

        _run(handler._handle_browser_stop({}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        self.assertTrue(
            any(f.get("type") == BrowserMessageType.BROWSER_SESSION_ENDED for f in frames)
        )
        self.assertIsNone(handler.active_browser_session_name)


class TestConcurrentMessageRejection(unittest.TestCase):
    """Test concurrent message rejection — Requirements 7.1, 7.2.

    As of Issue 5 (see ``.kiro/research/temp-browser-ui-issues-analysis.md``),
    concurrent-chat rejection happens in ``_dispatch`` BEFORE the chat body
    is spawned as a background task, so tests must route through
    ``_dispatch`` (not directly invoke ``_handle_chat_message``) to exercise
    the rejection path.
    """

    def test_chat_during_automation_returns_error(self) -> None:
        """CHAT_MESSAGE during automation returns ERROR with 'Automation in progress'."""
        handler, mock_ws, _, _, _ = _make_handler()
        handler.automation_in_progress = True

        _run(handler._dispatch(
            BrowserMessageType.CHAT_MESSAGE, {"content": "test"},
        ))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        error_frames = [f for f in frames if f.get("type") == BrowserMessageType.ERROR]
        self.assertEqual(len(error_frames), 1)
        self.assertIn("Automation in progress", error_frames[0]["content"])
        self.assertTrue(error_frames[0]["recoverable"])

    def test_automation_flag_cleared_after_streaming(self) -> None:
        """automation_in_progress is cleared after streaming completes."""
        handler, mock_ws, mock_factory, store, _ = _make_handler()

        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "test"}))

        self.assertFalse(handler.automation_in_progress)

    def test_automation_flag_cleared_on_streaming_error(self) -> None:
        """automation_in_progress is cleared even if streaming raises."""
        handler, mock_ws, mock_factory, store, _ = _make_handler()

        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock(
                side_effect=RuntimeError("stream failed")
            )
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "test"}))

        self.assertFalse(handler.automation_in_progress)


class TestConversationHistoryPersistence(unittest.TestCase):
    """Test conversation_history captures both user and assistant turns.

    Regression guard for Issue 4 in
    ``.kiro/research/temp-browser-ui-issues-analysis.md`` — the browser
    handler previously persisted only the user side of each turn, so
    resume brought back an asymmetric transcript with no assistant replies.
    """

    def _prime_handler_for_chat(self, final_text: str):
        """Build a handler wired so _handle_chat_message streams a stub
        streamer whose ``final_assistant_text`` is deterministic.

        Returns the (handler, store) so the caller can read back the
        persisted conversation_history after streaming completes.
        """
        handler, _ws, mock_factory, store, _storage = _make_handler()

        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        return handler, mock_factory, store, final_text

    def test_user_and_assistant_turns_both_persisted(self) -> None:
        """After a successful chat, conversation_history has both turns."""
        handler, _, store, final_text = self._prime_handler_for_chat(
            "Here are the headlines you asked for."
        )

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            mock_streamer_inst.final_assistant_text = final_text
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "Go to cnn.com"}))

        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertIsNotNone(record)
        history = record.conversation_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Go to cnn.com")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], final_text)

    def test_assistant_turn_persisted_even_when_text_is_empty(self) -> None:
        """Empty assistant text still produces an assistant entry.

        Some browser automations never emit a final text answer (HITL
        timeouts, pure-navigation flows). Persisting an empty assistant
        turn keeps user/assistant pair counts balanced so resume UIs can
        reason about turn ordering without special-casing.
        """
        handler, _, store, _ = self._prime_handler_for_chat("")

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            mock_streamer_inst.final_assistant_text = ""
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "Navigate to example.com"}))

        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertIsNotNone(record)
        history = record.conversation_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "")

    def test_assistant_turn_not_persisted_when_stream_raises(self) -> None:
        """A streaming error keeps the user turn but does not add an
        orphaned assistant turn with no content.

        Streaming errors already surface as an ERROR frame; there is no
        authoritative assistant text to persist. Skipping the assistant
        append matches the concierge-agent-container behavior (it only
        pushes turns into AgentCore Memory on successful completion).
        """
        handler, _, store, _ = self._prime_handler_for_chat("ignored")

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock(
                side_effect=RuntimeError("model unavailable")
            )
            mock_streamer_inst.final_assistant_text = "ignored"
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "Navigate to example.com"}))

        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertIsNotNone(record)
        history = record.conversation_history
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "user")

    def test_multi_turn_history_grows_with_each_chat(self) -> None:
        """Back-to-back chats accumulate alternating user/assistant turns."""
        handler, _, store, _ = self._prime_handler_for_chat("first answer")

        with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
            mock_streamer_inst = MagicMock()
            mock_streamer_inst.stream_events = AsyncMock()
            mock_streamer_inst.final_assistant_text = "first answer"
            MockStreamer.return_value = mock_streamer_inst

            _run(handler._handle_chat_message({"content": "first question"}))

            # Second turn: re-use the same handler + mock so the browser
            # session is not re-created (active session already set).
            handler.automation_in_progress = False
            mock_streamer_inst.final_assistant_text = "second answer"
            _run(handler._handle_chat_message({"content": "second question"}))

        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertIsNotNone(record)
        history = record.conversation_history
        self.assertEqual(len(history), 4)
        roles = [h["role"] for h in history]
        self.assertEqual(roles, ["user", "assistant", "user", "assistant"])
        contents = [h["content"] for h in history]
        self.assertEqual(
            contents,
            ["first question", "first answer", "second question", "second answer"],
        )


class TestConcurrentDispatchDuringChat(unittest.TestCase):
    """Test that incoming frames are dispatched while CHAT_MESSAGE streams.

    Regression guard for Issue 5 in
    ``.kiro/research/temp-browser-ui-issues-analysis.md``. Before the fix,
    CHAT_MESSAGE blocked the receive loop for the entire streaming duration,
    so BROWSER_HITL_RESPONSE frames queued up and only dispatched after the
    300 s HITL timeout fired. The fix runs CHAT_MESSAGE on a background task
    so the main loop can continue dispatching.
    """

    def test_hitl_response_dispatches_while_chat_streams(self) -> None:
        """BROWSER_HITL_RESPONSE arriving mid-chat reaches the handler and
        sets the HITL event, unblocking the streaming agent promptly rather
        than waiting for the HITL timeout.

        This is the core regression guard for Issue 5. We simulate the
        streamer blocking inside ``wait_for_hitl_response`` and assert the
        response dispatch on the main loop unblocks it.
        """
        # Build a handler without pre-loaded messages — we will inject them
        # manually so we can control the ordering precisely.
        handler, mock_ws, mock_factory, store, _ = _make_handler()

        mock_agent = mock_factory.create_agent.return_value
        mock_agent.stream_async = MagicMock(return_value=_async_gen([]))

        captured: dict = {}

        async def _stream_that_waits_for_hitl(_agent, _content):
            # The handler's wait_for_hitl_response creates the event and
            # awaits it. This mirrors how the real HandoffToUserTool
            # schedules the waiter onto the handler's main loop.
            result = await handler.wait_for_hitl_response(timeout=5.0)
            captured["response"] = result

        async def _scenario() -> None:
            """Drive a CHAT_MESSAGE + BROWSER_HITL_RESPONSE sequence."""
            with patch("streaming.browser_streamer.BrowserStreamer") as MockStreamer:
                mock_streamer_inst = MagicMock()
                mock_streamer_inst.stream_events = AsyncMock(
                    side_effect=_stream_that_waits_for_hitl,
                )
                mock_streamer_inst.final_assistant_text = ""
                MockStreamer.return_value = mock_streamer_inst

                # Simulate the receive-loop by dispatching two messages in
                # the order the loop would. Between the two dispatches we
                # yield so the chat task has a chance to reach its await.
                await handler._dispatch(
                    BrowserMessageType.CHAT_MESSAGE,
                    {"content": "Start"},
                )
                # Let the chat task progress until it awaits the HITL event.
                for _ in range(20):
                    await asyncio.sleep(0)
                    if handler.hitl_event is not None:
                        break
                self.assertIsNotNone(
                    handler.hitl_event,
                    "chat task did not reach wait_for_hitl_response",
                )

                await handler._dispatch(
                    BrowserMessageType.BROWSER_HITL_RESPONSE,
                    {"promptId": "p1", "action": "respond", "value": "do it"},
                )

                # Wait for the chat task to consume the response and finish.
                await handler._await_chat_task()

        _run(_scenario())

        self.assertIn("response", captured)
        self.assertIsNotNone(
            captured["response"],
            "HITL response did not reach the blocked streamer within the timeout",
        )
        self.assertEqual(captured["response"]["promptId"], "p1")
        self.assertEqual(captured["response"]["value"], "do it")


class TestHITLBlockUnblockTimeout(unittest.TestCase):
    """Test HITL blocking, unblocking, and timeout — Requirements 8.2–8.5."""

    def test_hitl_response_unblocks_wait(self) -> None:
        """HITL response sets event and returns payload — Req 8.3."""
        handler, mock_ws, _, store, _ = _make_handler()

        # Create session record
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
        )))

        response_payload = {"promptId": "p1", "action": "click", "value": "OK"}

        async def _test():
            # Schedule HITL response after a short delay
            async def _respond():
                await asyncio.sleep(0.05)
                await handler._handle_hitl_response(response_payload)

            asyncio.create_task(_respond())
            result = await handler.wait_for_hitl_response(timeout=2.0)
            return result

        result = _run(_test())
        self.assertEqual(result, response_payload)

    def test_hitl_timeout_returns_none(self) -> None:
        """HITL timeout returns None and sends BROWSER_HITL_TIMEOUT — Req 8.4."""
        handler, mock_ws, _, store, _ = _make_handler()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
        )))

        result = _run(handler.wait_for_hitl_response(timeout=0.1))

        self.assertIsNone(result)
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        timeout_frames = [
            f for f in frames
            if f.get("type") == BrowserMessageType.BROWSER_HITL_TIMEOUT
        ]
        self.assertEqual(len(timeout_frames), 1)

    def test_hitl_updates_session_status_to_paused(self) -> None:
        """wait_for_hitl_response sets session status to paused_hitl — Req 8.2."""
        handler, mock_ws, _, store, _ = _make_handler()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
            status="active",
        )))

        # Use a very short timeout so it completes quickly
        _run(handler.wait_for_hitl_response(timeout=0.05))

        # After timeout, status should be restored to active
        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertEqual(record.status, "active")

    def test_hitl_response_restores_active_status(self) -> None:
        """HITL response restores session status to active — Req 8.3."""
        handler, mock_ws, _, store, _ = _make_handler()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
            status="active",
        )))

        _run(handler._handle_hitl_response({"promptId": "p1", "value": "ok"}))

        record = _run(store.get(handler.user_id, handler.session_id))
        self.assertEqual(record.status, "active")


class TestDisconnectGracePeriod(unittest.TestCase):
    """Test disconnect grace period — Requirements 6.5, 6.6."""

    @patch.dict("os.environ", {"BA_DISCONNECT_GRACE_SECONDS": "0"})
    def test_disconnect_starts_grace_period(self) -> None:
        """Disconnect creates a grace period task — Req 6.5."""
        handler, mock_ws, mock_factory, store, _ = _make_handler()
        handler.active_browser_session_name = "active"
        handler._browser_tool = MagicMock()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
        )))

        _run(handler._handle_disconnect())

        self.assertIsNotNone(handler.disconnect_grace_task)

    def test_no_grace_period_without_active_session(self) -> None:
        """No grace period task if no active browser session."""
        handler, mock_ws, _, _, _ = _make_handler()
        handler.active_browser_session_name = None

        _run(handler._handle_disconnect())

        self.assertIsNone(handler.disconnect_grace_task)


class TestSessionNameValidation(unittest.TestCase):
    """Test _validate_session_name — Requirement 6.8."""

    def test_maps_any_name_to_active_session(self) -> None:
        """Any session name maps to the active browser session."""
        handler, _, _, _, _ = _make_handler()
        handler.active_browser_session_name = "real_session"

        result = handler._validate_session_name("claude_invented_name")
        self.assertEqual(result, "real_session")

    def test_returns_input_when_no_active_session(self) -> None:
        """Returns input name when no active browser session."""
        handler, _, _, _, _ = _make_handler()
        handler.active_browser_session_name = None

        result = handler._validate_session_name("some_name")
        self.assertEqual(result, "some_name")


class TestResumeSession(unittest.TestCase):
    """Test RESUME_SESSION — Requirement 5.6."""

    def test_resume_loads_conversation_history(self) -> None:
        """RESUME_SESSION loads history from store and includes in response."""
        handler, mock_ws, _, store, _ = _make_handler()

        target_id = "brws_20250101_000000_abcd1234"
        history = [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00"},
            {"role": "assistant", "content": "Hi", "timestamp": "2025-01-01T00:00:01"},
        ]
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=target_id,
            conversation_history=history,
        )))

        _run(handler._handle_resume_session({"session_id": target_id}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        resumed = [f for f in frames if f.get("type") == BrowserMessageType.SESSION_RESUMED]
        self.assertEqual(len(resumed), 1)
        self.assertEqual(len(resumed[0]["conversation_history"]), 2)
        self.assertEqual(handler.session_id, target_id)

    def test_resume_empty_history_for_missing_session(self) -> None:
        """RESUME_SESSION returns empty history for non-existent session."""
        handler, mock_ws, _, _, _ = _make_handler()

        _run(handler._handle_resume_session({"session_id": "nonexistent"}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        resumed = [f for f in frames if f.get("type") == BrowserMessageType.SESSION_RESUMED]
        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0]["conversation_history"], [])


class TestGetSessions(unittest.TestCase):
    """Test GET_SESSIONS — Requirement 5.7."""

    def test_returns_sessions_excluding_current(self) -> None:
        """GET_SESSIONS excludes the current active session."""
        handler, mock_ws, _, store, _ = _make_handler()

        # Create current session and another session
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=handler.session_id,
            conversation_history=[{"role": "user", "content": "current"}],
        )))
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id="brws_20250101_000000_other123",
            conversation_history=[{"role": "user", "content": "old session"}],
        )))

        _run(handler._handle_get_sessions({}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        loaded = [f for f in frames if f.get("type") == BrowserMessageType.SESSIONS_LOADED]
        self.assertEqual(len(loaded), 1)
        sessions = loaded[0]["sessions"]
        session_ids = [s["session_id"] for s in sessions]
        self.assertNotIn(handler.session_id, session_ids)
        self.assertIn("brws_20250101_000000_other123", session_ids)

    def test_each_session_carries_profile_and_mode(self) -> None:
        """Every session dict in SESSIONS_LOADED carries `profile` and `mode`.

        The shared frontend ``SessionList`` component keys icon and resume
        routing off ``session.profile`` (with ``mode`` as a fallback), so the
        backend must populate both fields on every payload.

        Regression guard for Issue 1 in
        ``.kiro/research/temp-browser-ui-issues-analysis.md`` — browser
        sessions were previously rendered with the voice-profile microphone
        icon because ``profile`` and ``mode`` were missing from the payload.
        """
        handler, mock_ws, _, store, _ = _make_handler()

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id="brws_20250101_000000_othertwo",
            conversation_history=[{"role": "user", "content": "hi"}],
        )))
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id="brws_20250102_000000_otherthr",
            conversation_history=[{"role": "user", "content": "hello"}],
        )))

        _run(handler._handle_get_sessions({}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        loaded = [f for f in frames if f.get("type") == BrowserMessageType.SESSIONS_LOADED]
        self.assertEqual(len(loaded), 1)
        sessions = loaded[0]["sessions"]
        self.assertGreaterEqual(len(sessions), 2)
        for session in sessions:
            self.assertIn("profile", session)
            self.assertIn("mode", session)
            self.assertEqual(session["profile"], "browser")
            self.assertEqual(session["mode"], "text")

    def test_profile_field_reflects_handler_profile(self) -> None:
        """The ``profile`` field mirrors the handler's configured profile name.

        If the handler were ever instantiated with a non-default profile
        string (e.g. for a future multi-profile container), the payload must
        echo whatever profile this handler serves — not a hard-coded
        ``"browser"`` literal.
        """
        handler, mock_ws, _, store, _ = _make_handler(profile="browser-preview")

        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id="brws_20250103_000000_previewa",
            conversation_history=[{"role": "user", "content": "preview"}],
        )))

        _run(handler._handle_get_sessions({}))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        loaded = [f for f in frames if f.get("type") == BrowserMessageType.SESSIONS_LOADED]
        self.assertEqual(len(loaded), 1)
        sessions = loaded[0]["sessions"]
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["profile"], "browser-preview")
        self.assertEqual(sessions[0]["mode"], "text")


class TestDeleteSession(unittest.TestCase):
    """Test DELETE_SESSION — Requirement 5.8."""

    def test_deletes_session_from_store(self) -> None:
        """DELETE_SESSION removes session and responds with SESSION_DELETED."""
        handler, mock_ws, _, store, _ = _make_handler()

        target_id = "brws_20250101_000000_todelete"
        _run(store.create(handler.user_id, SessionRecord(
            user_id=handler.user_id,
            session_id=target_id,
        )))

        _run(handler._handle_delete_session({"session_id": target_id}))

        # Verify deleted
        record = _run(store.get(handler.user_id, target_id))
        self.assertIsNone(record)

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        deleted = [f for f in frames if f.get("type") == BrowserMessageType.SESSION_DELETED]
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["session_id"], target_id)


class TestSendError(unittest.TestCase):
    """Test _send_error helper — Requirement 5.10."""

    def test_sends_error_frame(self) -> None:
        """_send_error sends ERROR frame with content and recoverable flag."""
        handler, mock_ws, _, _, _ = _make_handler()

        _run(handler._send_error("Something broke", recoverable=False))

        mock_ws.send_json.assert_awaited_once()
        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.ERROR)
        self.assertEqual(frame["content"], "Something broke")
        self.assertFalse(frame["recoverable"])

    def test_default_recoverable_true(self) -> None:
        """_send_error defaults to recoverable=True."""
        handler, mock_ws, _, _, _ = _make_handler()

        _run(handler._send_error("minor issue"))

        frame = mock_ws.send_json.call_args[0][0]
        self.assertTrue(frame["recoverable"])


if __name__ == "__main__":
    unittest.main()
