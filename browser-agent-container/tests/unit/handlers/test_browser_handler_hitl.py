# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BrowserHandler HITL wiring.

Validates the glue between BrowserHandler and HandoffToUserTool:
  1. `_handle_chat_message` calls `_handoff_tool.set_hitl_context` before the
     agent starts streaming, so the first handoff_to_user call has a live
     context.
  2. `_terminate_browser_session` calls `_handoff_tool.clear_hitl_context` so
     stale references don't leak across sessions on the same connection.
  3. `_handle_hitl_response` populates the handler's response payload and
     sets the event, so `wait_for_hitl_response` resolves with it.
  4. `wait_for_hitl_response` returns None on timeout and emits a
     BROWSER_HITL_TIMEOUT frame.
"""

import asyncio
import json
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import tests.__setup__  # noqa: F401

from handlers.browser_handler import BrowserHandler
from handlers.screenshot_storage import LocalScreenshotStorage
from handlers.session_store import InMemorySessionStore
from models.websocket_message_types import BrowserMessageType


async def _async_gen(items):
    for item in items:
        yield item


def _run(coro: Any) -> Any:
    """Run a coroutine on a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _build_handler(
    messages: Optional[List[str]] = None,
    user_id: str = "test_user",
    profile: str = "browser",
):
    """Create a BrowserHandler whose factory + browser_tool are fully mocked."""
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.closed = False

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

    mock_browser_tool = MagicMock()
    mock_browser_tool.get_live_view_url.return_value = "https://live.example.com/dcv"
    mock_factory.browser_tool = mock_browser_tool
    mock_factory.cleanup = MagicMock()

    store = InMemorySessionStore()
    storage = LocalScreenshotStorage(base_dir="/tmp/test_sessions")

    handler = BrowserHandler(
        websocket=mock_ws,
        agent_factory=mock_factory,
        session_store=store,
        screenshot_storage=storage,
        profile=profile,
        user_id=user_id,
    )
    return handler, mock_ws, mock_factory, mock_browser_tool


class TestSetHitlContextWiredOnChatMessage(unittest.TestCase):
    """_handle_chat_message must call set_hitl_context before streaming starts.

    Regression guard: if this wiring is dropped, handoff_to_user is invoked
    with no context and returns an error result every time — silent failure
    from the user's point of view.
    """

    def test_set_hitl_context_called_on_first_chat_message(self) -> None:
        handler, mock_ws, factory, browser_tool = _build_handler()

        payload: Dict[str, Any] = {"content": "navigate somewhere"}

        _run(handler._handle_chat_message(payload))

        # set_hitl_context must have been called exactly once.
        browser_tool._handoff_tool.set_hitl_context.assert_called_once()

        # The websocket arg must be the handler's real WS adapter.
        call_kwargs = (
            browser_tool._handoff_tool.set_hitl_context.call_args.kwargs
        )
        self.assertIs(call_kwargs.get("websocket"), mock_ws)

        # wait_for_response must be the handler's bound coroutine.
        self.assertTrue(callable(call_kwargs.get("wait_for_response")))
        self.assertEqual(
            call_kwargs["wait_for_response"].__name__,
            "wait_for_hitl_response",
        )

    def test_set_hitl_context_is_called_before_stream_events(self) -> None:
        """Ordering: set_hitl_context must precede agent streaming.

        Verified by recording call order on the mocks and asserting the
        handoff wiring fires before the streamer begins pulling events.
        """
        handler, _ws, factory, browser_tool = _build_handler()

        call_log: List[str] = []

        browser_tool._handoff_tool.set_hitl_context.side_effect = (
            lambda *a, **kw: call_log.append("set_hitl_context")
        )

        # Replace stream_async with one that records when it starts.
        async def recording_gen(*_args, **_kwargs):
            call_log.append("stream_async_called")
            for item in ():
                yield item

        factory.create_agent.return_value.stream_async = recording_gen

        _run(handler._handle_chat_message({"content": "go"}))

        # set_hitl_context must precede stream_async.
        self.assertIn("set_hitl_context", call_log)
        self.assertIn("stream_async_called", call_log)
        self.assertLess(
            call_log.index("set_hitl_context"),
            call_log.index("stream_async_called"),
        )


class TestClearHitlContextOnTeardown(unittest.TestCase):
    """_terminate_browser_session must clear the HITL context so a later
    session reuse on the same connection doesn't inherit stale references."""

    def test_clear_hitl_context_called_on_browser_stop(self) -> None:
        handler, _ws, _factory, browser_tool = _build_handler()

        # Arrange an active session.
        handler.active_browser_session_name = handler.session_id
        handler._browser_tool = browser_tool

        _run(handler._terminate_browser_session(reason="stopped"))

        browser_tool._handoff_tool.clear_hitl_context.assert_called_once()


class TestHitlResponseDelivery(unittest.TestCase):
    """_handle_hitl_response must populate the payload and set the event."""

    def test_response_sets_event_and_payload(self) -> None:
        handler, _ws, _factory, _browser_tool = _build_handler()

        async def scenario() -> Optional[dict]:
            # Prime the waiter as wait_for_hitl_response does internally.
            handler.hitl_event = asyncio.Event()
            handler.hitl_response = None

            # Deliver the response like the dispatcher would.
            payload = {
                "type": BrowserMessageType.BROWSER_HITL_RESPONSE,
                "promptId": "p123",
                "action": "respond",
                "value": "go ahead",
            }
            await handler._handle_hitl_response(payload)

            # Event is set and payload captured.
            self.assertTrue(handler.hitl_event.is_set())
            return handler.hitl_response

        captured = _run(scenario())
        self.assertIsNotNone(captured)
        self.assertEqual(captured["value"], "go ahead")
        self.assertEqual(captured["promptId"], "p123")


class TestWaitForHitlResponseBehavior(unittest.TestCase):
    """wait_for_hitl_response returns the payload on success and None on timeout."""

    def test_returns_payload_when_response_arrives(self) -> None:
        handler, _ws, _factory, _browser_tool = _build_handler()

        async def scenario() -> Optional[dict]:
            # Kick off the waiter with a generous timeout.
            wait_task = asyncio.create_task(
                handler.wait_for_hitl_response(timeout=5.0),
            )
            # Give the waiter a tick to prime hitl_event / hitl_response.
            await asyncio.sleep(0.01)
            await handler._handle_hitl_response({"value": "yes", "promptId": "p"})
            return await wait_task

        result = _run(scenario())
        self.assertEqual(result["value"], "yes")

    def test_returns_none_and_emits_timeout_frame_on_timeout(self) -> None:
        handler, mock_ws, _factory, _browser_tool = _build_handler()

        async def scenario() -> Optional[dict]:
            return await handler.wait_for_hitl_response(timeout=0.1)

        result = _run(scenario())
        self.assertIsNone(result)

        # The handler must have emitted exactly one BROWSER_HITL_TIMEOUT frame.
        timeout_frames = [
            call_args.args[0]
            for call_args in mock_ws.send_json.call_args_list
            if isinstance(call_args.args[0], dict)
            and call_args.args[0].get("type") == BrowserMessageType.BROWSER_HITL_TIMEOUT
        ]
        self.assertEqual(len(timeout_frames), 1)
        self.assertEqual(timeout_frames[0]["session_id"], handler.session_id)


if __name__ == "__main__":
    unittest.main()
