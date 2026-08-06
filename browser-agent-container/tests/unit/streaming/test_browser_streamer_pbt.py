# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for BrowserStreamer.

Property 5: BrowserStreamer event-to-frame mapping (Req 17.3, 9.1, 9.2, 9.3, 9.4, 9.5, 9.7)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.streaming.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from handlers.session_store import InMemorySessionStore, SessionRecord
from handlers.screenshot_storage import LocalScreenshotStorage
from models.websocket_message_types import BrowserMessageType
from streaming.browser_streamer import BrowserStreamer


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_streamer():
    """Create a BrowserStreamer with mocked WebSocket."""
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.closed = False

    store = InMemorySessionStore()
    storage = LocalScreenshotStorage(base_dir="/tmp/test")
    run_async(store.create("u1", SessionRecord(user_id="u1", session_id="s1")))

    streamer = BrowserStreamer(
        websocket=mock_ws,
        session_store=store,
        screenshot_storage=storage,
        user_id="u1",
        session_id="s1",
    )
    return streamer, mock_ws


BROWSER_TOOLS = [
    "screenshot_for_vision", "semantic_action", "browser",
    "accessibility_snapshot",
]
# Tools that must NEVER produce streamer-emitted frames. `handoff_to_user` is
# handled inline by `HandoffToUserTool`, which emits BROWSER_HITL_PROMPT
# directly — the streamer must treat it as an unknown tool.
STREAMER_IGNORED_TOOLS = ["handoff_to_user"]


# ============================================================
# Property 5: BrowserStreamer event-to-frame mapping
# Feature: 86-browser-agent-container-deployment, Property 5: BrowserStreamer event-to-frame mapping
# Validates: Requirements 17.3, 9.1, 9.2, 9.3, 9.4, 9.5, 9.7
# ============================================================

class TestEventToFrameMappingProperty(unittest.TestCase):
    """Property 5: BrowserStreamer event-to-frame mapping."""

    @settings(max_examples=100)
    @given(text=st.text(min_size=1, max_size=200))
    def test_reasoning_event_maps_to_reasoning_frame(self, text: str) -> None:
        """Any non-empty reasoningText event produces a REASONING frame."""
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({"reasoningText": text}))
        mock_ws.send_json.assert_awaited_once()
        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.REASONING)
        self.assertEqual(frame["content"], text)

    @settings(max_examples=100)
    @given(text=st.text(min_size=1, max_size=200))
    def test_data_event_buffers_and_classifies_as_stream_on_text_only_message(
        self, text: str,
    ) -> None:
        """Any non-empty data event followed by a text-only assistant message
        produces exactly one STREAM frame with the concatenated content.

        Issue 3 contract: ``data`` chunks are buffered until the enclosing
        assistant ``message`` event classifies them. A text-only message
        means the final answer cycle — buffer flushes as STREAM.
        """
        streamer, mock_ws = _make_streamer()
        # Data alone: buffered, no frame yet.
        run_async(streamer._process_event({"data": text}))
        mock_ws.send_json.assert_not_awaited()
        self.assertEqual(streamer._data_buffer, [text])

        # Text-only assistant message flushes the buffer as STREAM.
        run_async(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            },
        }))
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        stream_frames = [
            f for f in frames if f.get("type") == BrowserMessageType.STREAM
        ]
        self.assertEqual(len(stream_frames), 1)
        self.assertEqual(stream_frames[0]["content"], text)
        self.assertTrue(streamer._reached_final_answer)

    @settings(max_examples=100)
    @given(text=st.text(min_size=1, max_size=200))
    def test_data_event_classifies_as_reasoning_on_message_with_toolUse(
        self, text: str,
    ) -> None:
        """Any non-empty data event followed by an assistant message that
        includes a ``toolUse`` block produces exactly one REASONING frame.

        Issue 3 contract: pre-tool narration flushes as REASONING.
        """
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({"data": text}))
        run_async(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": text},
                    {"toolUse": {"toolUseId": "tu_x", "name": "browser", "input": {}}},
                ],
            },
        }))
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        reasoning_frames = [
            f for f in frames if f.get("type") == BrowserMessageType.REASONING
        ]
        self.assertEqual(len(reasoning_frames), 1)
        self.assertEqual(reasoning_frames[0]["content"], text)
        self.assertFalse(streamer._reached_final_answer)

    @settings(max_examples=100)
    @given(
        tool_name=st.sampled_from(BROWSER_TOOLS),
        tool_id=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=4, max_size=20,
        ),
    )
    def test_tool_use_maps_to_action_start(
        self, tool_name: str, tool_id: str
    ) -> None:
        """Any browser tool current_tool_use produces BROWSER_ACTION_START."""
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({
            "current_tool_use": {
                "name": tool_name,
                "toolUseId": tool_id,
                "input": {},
            },
        }))
        mock_ws.send_json.assert_awaited_once()
        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.BROWSER_ACTION_START)
        self.assertEqual(frame["actionType"], tool_name)
        self.assertGreaterEqual(frame["stepNumber"], 1)

    @settings(max_examples=100)
    @given(
        tool_name=st.text(min_size=1, max_size=30).filter(
            lambda t: t not in BROWSER_TOOLS
        ),
    )
    def test_unknown_tool_produces_no_frame(self, tool_name: str) -> None:
        """Non-browser tool names produce no frame.

        Note: `handoff_to_user` falls under this property on purpose — the
        streamer treats it as unknown because the tool is responsible for
        emitting its own BROWSER_HITL_PROMPT frame. See
        `test_handoff_tool_never_produces_streamer_frame` for the targeted
        regression guard.
        """
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({
            "current_tool_use": {
                "name": tool_name,
                "toolUseId": "tu_unknown",
                "input": {},
            },
        }))
        mock_ws.send_json.assert_not_awaited()

    @settings(max_examples=50)
    @given(
        tool_id=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=4, max_size=20,
        ),
        input_payload=st.dictionaries(
            keys=st.sampled_from(["message", "question", "breakout_of_loop"]),
            values=st.one_of(st.text(max_size=50), st.booleans()),
            max_size=3,
        ),
    )
    def test_handoff_tool_never_produces_streamer_frame(
        self, tool_id: str, input_payload: dict,
    ) -> None:
        """handoff_to_user current_tool_use must NEVER produce a streamer frame.

        Regression property: HandoffToUserTool is responsible for emitting
        BROWSER_HITL_PROMPT directly. If the streamer ever starts tracking
        handoff_to_user again it will produce duplicate / out-of-order
        frames, so this property enforces the contract for every sampled
        input shape.
        """
        streamer, mock_ws = _make_streamer()

        for ignored_name in STREAMER_IGNORED_TOOLS:
            run_async(streamer._process_event({
                "current_tool_use": {
                    "name": ignored_name,
                    "toolUseId": tool_id,
                    "input": input_payload,
                },
            }))

        mock_ws.send_json.assert_not_awaited()
        self.assertEqual(streamer.step_counter, 0)

    @settings(max_examples=100)
    @given(st.just(""))
    def test_empty_reasoning_produces_no_frame(self, text: str) -> None:
        """Empty reasoningText produces no frame."""
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({"reasoningText": text}))
        mock_ws.send_json.assert_not_awaited()

    @settings(max_examples=100)
    @given(st.just(""))
    def test_empty_data_produces_no_frame(self, text: str) -> None:
        """Empty data produces no frame."""
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event({"data": text}))
        mock_ws.send_json.assert_not_awaited()

    @settings(max_examples=100)
    @given(
        event=st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=50),
            st.lists(st.integers(), max_size=5),
        )
    )
    def test_non_dict_events_silently_ignored(self, event) -> None:
        """Non-dict events produce no frame and no error."""
        streamer, mock_ws = _make_streamer()
        run_async(streamer._process_event(event))
        mock_ws.send_json.assert_not_awaited()

    @settings(max_examples=100)
    @given(
        n_tools=st.integers(min_value=1, max_value=10),
    )
    def test_step_counter_increments_monotonically(self, n_tools: int) -> None:
        """Step counter increments by 1 for each new tool invocation."""
        streamer, mock_ws = _make_streamer()
        for i in range(n_tools):
            run_async(streamer._process_event({
                "current_tool_use": {
                    "name": "browser",
                    "toolUseId": "tu_%d" % i,
                    "input": {},
                },
            }))
        self.assertEqual(streamer.step_counter, n_tools)
        for idx, call in enumerate(mock_ws.send_json.call_args_list):
            frame = call[0][0]
            self.assertEqual(frame["stepNumber"], idx + 1)


if __name__ == "__main__":
    unittest.main()
