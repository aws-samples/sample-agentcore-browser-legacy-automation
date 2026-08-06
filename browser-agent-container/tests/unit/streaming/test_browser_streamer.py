# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BrowserStreamer.
"""

import asyncio
import base64
import unittest
from unittest.mock import AsyncMock, MagicMock

from handlers.session_store import InMemorySessionStore, SessionRecord
from handlers.screenshot_storage import LocalScreenshotStorage
from models.websocket_message_types import BrowserMessageType
from streaming.browser_streamer import BrowserStreamer


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


async def _async_gen(items):
    """Create an async generator from a list."""
    for item in items:
        yield item


def _make_streamer(user_id="test_user", session_id="brws_20250101_000000_abcd1234"):
    """Create a BrowserStreamer with mocked dependencies."""
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.closed = False

    store = InMemorySessionStore()
    storage = LocalScreenshotStorage(base_dir="/tmp/test_sessions")

    # Create session record
    _run(store.create(user_id, SessionRecord(
        user_id=user_id,
        session_id=session_id,
    )))

    streamer = BrowserStreamer(
        websocket=mock_ws,
        session_store=store,
        screenshot_storage=storage,
        user_id=user_id,
        session_id=session_id,
    )

    return streamer, mock_ws, store


class TestReasoningEvent(unittest.TestCase):
    """Test reasoningText → REASONING frame — Requirement 9.1."""

    def test_reasoning_event_sends_reasoning_frame(self) -> None:
        """reasoningText event produces REASONING frame with content."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"reasoningText": "Thinking about this..."}))

        mock_ws.send_json.assert_awaited_once_with({
            "type": BrowserMessageType.REASONING,
            "content": "Thinking about this...",
        })

    def test_empty_reasoning_ignored(self) -> None:
        """Empty reasoningText is ignored."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"reasoningText": ""}))

        mock_ws.send_json.assert_not_awaited()


class TestDataEvent(unittest.TestCase):
    """Test data chunks — buffered-and-classified (Issue 3).

    A ``data`` event no longer dispatches a STREAM frame immediately — it is
    buffered until an enclosing assistant ``message`` event tells the
    streamer whether the buffered text was pre-tool narration (flush as
    REASONING) or the final answer (flush as STREAM). After the final
    answer flag latches, any further ``data`` chunks dispatch as STREAM
    directly.
    """

    def test_data_event_buffers_until_classified(self) -> None:
        """A lone ``data`` event buffers — no frame is sent yet."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"data": "Here is the result..."}))

        mock_ws.send_json.assert_not_awaited()
        self.assertEqual(streamer._data_buffer, ["Here is the result..."])

    def test_empty_data_ignored(self) -> None:
        """Empty data string is ignored and does not buffer."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"data": ""}))

        mock_ws.send_json.assert_not_awaited()
        self.assertEqual(streamer._data_buffer, [])

    def test_data_after_final_answer_flag_sends_stream_directly(self) -> None:
        """Once ``_reached_final_answer`` latches, ``data`` dispatches as STREAM."""
        streamer, mock_ws, _ = _make_streamer()
        streamer._reached_final_answer = True

        _run(streamer._process_event({"data": "trailing-answer-text"}))

        mock_ws.send_json.assert_awaited_once_with({
            "type": BrowserMessageType.STREAM,
            "content": "trailing-answer-text",
        })
        self.assertEqual(streamer._data_buffer, [])


class TestDataClassification(unittest.TestCase):
    """Test the reasoning-vs-final-answer classifier — Issue 3.

    The classifier uses the content shape of the enclosing assistant
    ``message`` event to decide whether buffered ``data`` chunks were
    pre-tool narration (REASONING) or the final answer (STREAM).
    """

    def test_assistant_message_with_toolUse_flushes_buffer_as_reasoning(self) -> None:
        """Buffered data followed by an assistant message that calls a tool
        is pre-tool narration → flushes as REASONING."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"data": "I'll start by "}))
        _run(streamer._process_event({"data": "taking a screenshot."}))
        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "I'll start by taking a screenshot."},
                    {"toolUse": {"toolUseId": "tu_x", "name": "browser", "input": {}}},
                ],
            },
        }))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        reasoning_frames = [
            f for f in frames if f.get("type") == BrowserMessageType.REASONING
        ]
        self.assertEqual(len(reasoning_frames), 1)
        self.assertEqual(
            reasoning_frames[0]["content"],
            "I'll start by taking a screenshot.",
        )
        self.assertFalse(streamer._reached_final_answer)
        self.assertEqual(streamer._data_buffer, [])

    def test_assistant_message_text_only_flushes_buffer_as_stream(self) -> None:
        """Buffered data followed by a text-only assistant message is the
        final answer → flushes as STREAM and latches the final-answer flag."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"data": "The form has been "}))
        _run(streamer._process_event({"data": "submitted successfully."}))
        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "The form has been submitted successfully."},
                ],
            },
        }))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        stream_frames = [
            f for f in frames if f.get("type") == BrowserMessageType.STREAM
        ]
        self.assertEqual(len(stream_frames), 1)
        self.assertEqual(
            stream_frames[0]["content"],
            "The form has been submitted successfully.",
        )
        self.assertTrue(streamer._reached_final_answer)
        self.assertEqual(streamer._data_buffer, [])

    def test_user_message_does_not_flush_buffer(self) -> None:
        """A user-role message (e.g. tool result) does NOT trigger a flush."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({"data": "pending text"}))
        _run(streamer._process_event({
            "message": {
                "role": "user",
                "content": [{"toolResult": {"toolUseId": "tu_x", "content": []}}],
            },
        }))

        stream_or_reasoning = [
            c[0][0] for c in mock_ws.send_json.call_args_list
            if c[0][0].get("type") in (
                BrowserMessageType.STREAM, BrowserMessageType.REASONING,
            )
        ]
        self.assertEqual(stream_or_reasoning, [])
        self.assertEqual(streamer._data_buffer, ["pending text"])

    def test_empty_buffer_does_not_emit_empty_frame(self) -> None:
        """Classifier with no buffered data does not dispatch an empty frame."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [{"text": "hello"}],
            },
        }))

        stream_or_reasoning = [
            c[0][0] for c in mock_ws.send_json.call_args_list
            if c[0][0].get("type") in (
                BrowserMessageType.STREAM, BrowserMessageType.REASONING,
            )
        ]
        self.assertEqual(stream_or_reasoning, [])

    def test_multi_cycle_flow_produces_interleaved_reasoning_and_final_stream(self) -> None:
        """End-to-end: two pre-tool narration blocks + final text emit
        REASONING → REASONING → STREAM in order."""
        streamer, mock_ws, _ = _make_streamer()

        # Cycle 1: narrate, then call a tool
        _run(streamer._process_event({"data": "Let me navigate."}))
        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Let me navigate."},
                    {"toolUse": {"toolUseId": "t1", "name": "browser", "input": {}}},
                ],
            },
        }))

        # Tool result
        _run(streamer._process_event({
            "message": {
                "role": "user",
                "content": [{"toolResult": {"toolUseId": "t1", "content": []}}],
            },
        }))

        # Cycle 2: narrate, then call another tool
        _run(streamer._process_event({"data": "Now clicking submit."}))
        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Now clicking submit."},
                    {"toolUse": {"toolUseId": "t2", "name": "browser", "input": {}}},
                ],
            },
        }))

        # Tool result
        _run(streamer._process_event({
            "message": {
                "role": "user",
                "content": [{"toolResult": {"toolUseId": "t2", "content": []}}],
            },
        }))

        # Final cycle: final answer, no tool call
        _run(streamer._process_event({"data": "Done! "}))
        _run(streamer._process_event({"data": "Form submitted."}))
        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [{"text": "Done! Form submitted."}],
            },
        }))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        classified = [
            f for f in frames
            if f.get("type") in (
                BrowserMessageType.STREAM, BrowserMessageType.REASONING,
            )
        ]
        self.assertEqual(
            [(f["type"], f["content"]) for f in classified],
            [
                (BrowserMessageType.REASONING, "Let me navigate."),
                (BrowserMessageType.REASONING, "Now clicking submit."),
                (BrowserMessageType.STREAM, "Done! Form submitted."),
            ],
        )


class TestToolUseEvent(unittest.TestCase):
    """Test current_tool_use → BROWSER_ACTION_START — Requirements 9.4, 9.5."""

    def test_screenshot_tool_sends_action_start(self) -> None:
        """screenshot_for_vision tool sends BROWSER_ACTION_START."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {
                "name": "screenshot_for_vision",
                "toolUseId": "tu_001",
                "input": {"title": "homepage"},
            },
        }))

        mock_ws.send_json.assert_awaited_once()
        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.BROWSER_ACTION_START)
        self.assertEqual(frame["actionType"], "screenshot_for_vision")
        self.assertEqual(frame["stepNumber"], 1)

    def test_semantic_action_tool_sends_action_start(self) -> None:
        """semantic_action tool sends BROWSER_ACTION_START."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {
                "name": "semantic_action",
                "toolUseId": "tu_002",
                "input": {"semantic_input": {"action": "click"}},
            },
        }))

        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["actionType"], "semantic_action")
        self.assertEqual(frame["details"], "click")

    def test_browser_tool_sends_action_start(self) -> None:
        """browser tool sends BROWSER_ACTION_START."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {
                "name": "browser",
                "toolUseId": "tu_003",
                "input": {"action": "navigate"},
            },
        }))

        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["actionType"], "browser")
        self.assertEqual(frame["details"], "navigate")

    def test_step_counter_increments(self) -> None:
        """Step counter increments with each new tool invocation."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {"name": "browser", "toolUseId": "tu_001", "input": {}},
        }))
        _run(streamer._process_event({
            "current_tool_use": {"name": "browser", "toolUseId": "tu_002", "input": {}},
        }))

        calls = mock_ws.send_json.call_args_list
        self.assertEqual(calls[0][0][0]["stepNumber"], 1)
        self.assertEqual(calls[1][0][0]["stepNumber"], 2)

    def test_duplicate_tool_use_id_ignored(self) -> None:
        """Same toolUseId is not processed twice."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {"name": "browser", "toolUseId": "tu_001", "input": {}},
        }))
        _run(streamer._process_event({
            "current_tool_use": {"name": "browser", "toolUseId": "tu_001", "input": {}},
        }))

        self.assertEqual(mock_ws.send_json.await_count, 1)
        self.assertEqual(streamer.step_counter, 1)

    def test_unknown_tool_ignored(self) -> None:
        """Unknown tool names are ignored."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {"name": "unknown_tool", "toolUseId": "tu_999", "input": {}},
        }))

        mock_ws.send_json.assert_not_awaited()


class TestScreenshotFrame(unittest.TestCase):
    """Test screenshot frame emission — Requirement 9.3.

    Issue 2 contract: ``screenshot_for_vision`` results emit BOTH a
    ``BROWSER_SCREENSHOT`` frame (with the pre-signed URL) AND a
    ``BROWSER_ACTION_COMPLETE`` frame (with success/result) so the UI's
    step-card status flips from spinning to done. See
    ``.kiro/research/temp-browser-ui-issues-analysis.md``.
    """

    def _screenshot_frames(self, mock_ws) -> list:
        """Helper: filter captured frames for BROWSER_SCREENSHOT only."""
        return [
            c[0][0] for c in mock_ws.send_json.call_args_list
            if c[0][0].get("type") == BrowserMessageType.BROWSER_SCREENSHOT
        ]

    def test_screenshot_result_sends_browser_screenshot(self) -> None:
        """Screenshot tool result sends BROWSER_SCREENSHOT with screenshotPath."""
        streamer, mock_ws, _ = _make_streamer()

        # First set up pending tool tracking
        streamer._pending_tool_use_id = "tu_ss1"
        streamer._pending_tool_name = "screenshot_for_vision"
        streamer._pending_tool_input = {"title": "homepage"}
        streamer.step_counter = 1

        png_bytes = b"\x89PNG\r\n\x1a\nfake_image_data"

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_ss1",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {"bytes": png_bytes},
                            },
                        },
                        {
                            "text": "Screenshot saved: sessions/local/brws_test/screenshots/test.png",
                        },
                    ],
                },
            }],
        }))

        shots = self._screenshot_frames(mock_ws)
        self.assertEqual(len(shots), 1)
        frame = shots[0]
        self.assertEqual(frame["type"], BrowserMessageType.BROWSER_SCREENSHOT)
        self.assertEqual(
            frame["screenshotPath"],
            "sessions/local/brws_test/screenshots/test.png",
        )
        # screenshotUrl is empty for local paths (no S3)
        self.assertEqual(frame["screenshotUrl"], "")
        self.assertEqual(frame["title"], "homepage")
        self.assertEqual(frame["stepNumber"], 1)

    def test_screenshot_result_also_sends_action_complete(self) -> None:
        """Screenshot tool result sends BROWSER_ACTION_COMPLETE in addition
        to BROWSER_SCREENSHOT, in that order, sharing the same stepNumber.

        Regression guard for Issue 2 — the UI needs the COMPLETE to flip
        the step card's spinner to a check mark.
        """
        streamer, mock_ws, _ = _make_streamer()

        streamer._pending_tool_use_id = "tu_ss2"
        streamer._pending_tool_name = "screenshot_for_vision"
        streamer._pending_tool_input = {"title": "after-submit"}
        streamer.step_counter = 4

        png_bytes = b"\x89PNG\r\n\x1a\nfake"

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_ss2",
                    "content": [
                        {"image": {"format": "png", "source": {"bytes": png_bytes}}},
                        {"text": "Screenshot saved: sessions/local/brws_test/screenshots/a.png. Analyze visually to identify elements."},
                    ],
                },
            }],
        }))

        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        types_in_order = [f.get("type") for f in frames]
        self.assertIn(BrowserMessageType.BROWSER_SCREENSHOT, types_in_order)
        self.assertIn(BrowserMessageType.BROWSER_ACTION_COMPLETE, types_in_order)
        # Order matters: SCREENSHOT first, COMPLETE second.
        self.assertLess(
            types_in_order.index(BrowserMessageType.BROWSER_SCREENSHOT),
            types_in_order.index(BrowserMessageType.BROWSER_ACTION_COMPLETE),
        )

        complete_frames = [
            f for f in frames
            if f.get("type") == BrowserMessageType.BROWSER_ACTION_COMPLETE
        ]
        self.assertEqual(len(complete_frames), 1)
        self.assertEqual(complete_frames[0]["actionType"], "screenshot_for_vision")
        self.assertEqual(complete_frames[0]["stepNumber"], 4)
        self.assertTrue(complete_frames[0]["success"])

    def test_screenshot_path_strips_trailing_sentence(self) -> None:
        """Path must NOT include the ``. Analyze visually to identify elements.``
        suffix that ScreenshotTool appends to the text block.

        Regression: before the fix, ``split('Screenshot saved:')[-1].strip()``
        captured the trailing sentence as part of the path, producing a
        malformed S3 key like
        ``screenshots/x.png. Analyze visually to identify elements.`` which
        signed into a bogus pre-signed URL and caused the UI to render empty
        screenshots with S3 403/404 responses.
        """
        streamer, mock_ws, _ = _make_streamer()

        streamer._pending_tool_use_id = "tu_reg1"
        streamer._pending_tool_name = "screenshot_for_vision"
        streamer._pending_tool_input = {"title": "wikipedia-homepage"}
        streamer.step_counter = 1

        png_bytes = b"\x89PNG\r\n\x1a\nfake"
        s3_path = (
            "s3://amzn-s3-demo-session-bucket/"
            "browser-sessions/local/brws_abc/screenshots/"
            "2026-04-29T01-20-55-630_wikipedia-homepage.png"
        )
        confirmation = (
            f"Screenshot saved: {s3_path}. "
            "Analyze visually to identify elements."
        )

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_reg1",
                    "content": [
                        {"image": {"format": "png", "source": {"bytes": png_bytes}}},
                        {"text": confirmation},
                    ],
                },
            }],
        }))

        shots = self._screenshot_frames(mock_ws)
        self.assertEqual(len(shots), 1)
        frame = shots[0]
        self.assertEqual(frame["screenshotPath"], s3_path)
        self.assertNotIn("Analyze", frame["screenshotPath"])
        self.assertNotIn(" ", frame["screenshotPath"])


class TestActionCompleteFrame(unittest.TestCase):
    """Test BROWSER_ACTION_COMPLETE — Requirement 9.5."""

    def test_action_result_sends_action_complete(self) -> None:
        """Action tool result sends BROWSER_ACTION_COMPLETE."""
        streamer, mock_ws, _ = _make_streamer()

        streamer._pending_tool_use_id = "tu_act1"
        streamer._pending_tool_name = "semantic_action"
        streamer._pending_tool_input = {}
        streamer.step_counter = 2

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_act1",
                    "content": [{"text": "Clicked button successfully"}],
                },
            }],
        }))

        frame = mock_ws.send_json.call_args[0][0]
        self.assertEqual(frame["type"], BrowserMessageType.BROWSER_ACTION_COMPLETE)
        self.assertEqual(frame["actionType"], "semantic_action")
        self.assertTrue(frame["success"])
        self.assertEqual(frame["stepNumber"], 2)

    def test_error_result_sets_success_false(self) -> None:
        """Tool result containing 'error' sets success=False."""
        streamer, mock_ws, _ = _make_streamer()

        streamer._pending_tool_use_id = "tu_err1"
        streamer._pending_tool_name = "browser"
        streamer._pending_tool_input = {}
        streamer.step_counter = 1

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_err1",
                    "content": [{"text": "Error: element not found"}],
                },
            }],
        }))

        frame = mock_ws.send_json.call_args[0][0]
        self.assertFalse(frame["success"])


class TestHandoffNotRoutedThroughStreamer(unittest.TestCase):
    """The handoff_to_user tool emits BROWSER_HITL_PROMPT itself via
    HandoffToUserTool — the streamer must NOT special-case it.

    Regression guard: a previous revision of this file had a
    `_send_hitl_prompt` branch that treated the handoff tool's ToolResult as
    the prompt content. That was incorrect because by the time the result
    reaches the streamer, the user has already answered and the result is
    their response text. The correct flow is for `HandoffToUserTool` to emit
    the prompt frame when Claude first calls the tool, and for the streamer
    to treat the result like any other action result.
    """

    def test_handoff_tool_is_not_tracked_in_action_start(self) -> None:
        """A tool_use with name 'handoff_to_user' must not produce
        BROWSER_ACTION_START from the streamer."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "current_tool_use": {
                "name": "handoff_to_user",
                "toolUseId": "tu_handoff1",
                "input": {"message": "which option?"},
            },
        }))

        mock_ws.send_json.assert_not_awaited()
        self.assertEqual(streamer.step_counter, 0)

    def test_handoff_result_does_not_send_hitl_prompt(self) -> None:
        """A tool_result for handoff_to_user must NOT produce
        BROWSER_HITL_PROMPT from the streamer.
        """
        streamer, mock_ws, _ = _make_streamer()

        # Simulate tracking state that SHOULD have been skipped by
        # _handle_tool_use above, but assert again at result time just to
        # make the guard explicit even if future tracking logic drifts.
        streamer._pending_tool_use_id = "tu_handoff2"
        streamer._pending_tool_name = "handoff_to_user"
        streamer._pending_tool_input = {}

        _run(streamer._handle_tool_result({
            "content": [{
                "toolResult": {
                    "toolUseId": "tu_handoff2",
                    "content": [{"text": "User response: log in please"}],
                },
            }],
        }))

        # No frames of any kind — handoff is not in the streamer's tool
        # vocabulary.
        frames = [c[0][0] for c in mock_ws.send_json.call_args_list]
        prompt_frames = [
            f for f in frames
            if f.get("type") == BrowserMessageType.BROWSER_HITL_PROMPT
        ]
        self.assertEqual(prompt_frames, [])


class TestOrchestrationEnvelope(unittest.TestCase):
    """Test ORCHESTRATION_START/END envelope — Requirement 9.7."""

    def test_stream_events_wraps_in_orchestration(self) -> None:
        """stream_events sends ORCHESTRATION_START first and ORCHESTRATION_END last."""
        streamer, mock_ws, _ = _make_streamer()

        mock_agent = MagicMock()
        mock_agent.stream_async = MagicMock(
            return_value=_async_gen([{"data": "hello"}])
        )

        _run(streamer.stream_events(mock_agent, "test query"))

        calls = mock_ws.send_json.call_args_list
        first_frame = calls[0][0][0]
        last_frame = calls[-1][0][0]
        self.assertEqual(first_frame["type"], BrowserMessageType.ORCHESTRATION_START)
        self.assertEqual(last_frame["type"], BrowserMessageType.ORCHESTRATION_END)


class TestMetadataFinalization(unittest.TestCase):
    """Test METADATA frame — Requirement 9.6."""

    def test_finalize_sends_metadata(self) -> None:
        """_finalize sends METADATA with duration and steps."""
        streamer, mock_ws, _ = _make_streamer()
        streamer.step_counter = 5
        streamer.start_time = 1000.0

        with unittest.mock.patch("streaming.browser_streamer.time") as mock_time:
            mock_time.time.return_value = 1002.5
            _run(streamer._finalize())

        calls = mock_ws.send_json.call_args_list
        metadata_frames = [
            c[0][0] for c in calls
            if c[0][0].get("type") == BrowserMessageType.METADATA
        ]
        self.assertEqual(len(metadata_frames), 1)
        self.assertEqual(metadata_frames[0]["steps_completed"], 5)
        self.assertEqual(metadata_frames[0]["total_duration_ms"], 2500)


class TestErrorFrame(unittest.TestCase):
    """Test ERROR frame on streaming exception — Requirement 9.8."""

    def test_streaming_error_sends_error_frame(self) -> None:
        """Exception during streaming sends ERROR frame with recoverable=True."""
        streamer, mock_ws, _ = _make_streamer()

        async def _failing_gen():
            raise RuntimeError("Agent crashed")
            yield  # noqa: unreachable — makes this an async generator

        mock_agent = MagicMock()
        mock_agent.stream_async = MagicMock(return_value=_failing_gen())

        _run(streamer.stream_events(mock_agent, "test"))

        calls = mock_ws.send_json.call_args_list
        error_frames = [
            c[0][0] for c in calls
            if c[0][0].get("type") == BrowserMessageType.ERROR
        ]
        self.assertEqual(len(error_frames), 1)
        self.assertIn("Agent crashed", error_frames[0]["content"])
        self.assertTrue(error_frames[0]["recoverable"])


class TestNonDictEventIgnored(unittest.TestCase):
    """Test that non-dict events are silently ignored."""

    def test_string_event_ignored(self) -> None:
        """String event does not produce any frame."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event("not a dict"))

        mock_ws.send_json.assert_not_awaited()

    def test_none_event_ignored(self) -> None:
        """None event does not produce any frame."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event(None))

        mock_ws.send_json.assert_not_awaited()


class TestFinalAssistantTextCapture(unittest.TestCase):
    """Test ``final_assistant_text`` capture for resume fidelity — Issue 4.

    The handler persists the captured assistant text to ``conversation_history``
    after ``stream_events`` completes so resume shows both user and assistant
    turns. See ``.kiro/research/temp-browser-ui-issues-analysis.md``.
    """

    def test_initial_final_text_is_empty(self) -> None:
        """``final_assistant_text`` starts as an empty string."""
        streamer, _, _ = _make_streamer()
        self.assertEqual(streamer.final_assistant_text, "")

    def test_captures_text_from_result_event_with_agentresult_like_obj(self) -> None:
        """A ``result`` event with an AgentResult-like object captures its text."""
        streamer, _, _ = _make_streamer()

        class _FakeAgentResult:
            """Minimal AgentResult stand-in — only the attributes we read."""
            message = {
                "role": "assistant",
                "content": [{"text": "The form has been submitted successfully."}],
            }

        _run(streamer._process_event({"result": _FakeAgentResult()}))

        self.assertEqual(
            streamer.final_assistant_text,
            "The form has been submitted successfully.",
        )

    def test_captures_text_from_result_event_with_dict(self) -> None:
        """A ``result`` event whose value is a plain dict is also supported."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "result": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Here are the "},
                        {"text": "top headlines."},
                    ],
                },
            },
        }))

        self.assertEqual(
            streamer.final_assistant_text,
            "Here are the top headlines.",
        )

    def test_captures_text_from_terminal_assistant_message(self) -> None:
        """A text-only assistant ``message`` event captures its content."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [{"text": "Page loaded successfully."}],
            },
        }))

        self.assertEqual(
            streamer.final_assistant_text,
            "Page loaded successfully.",
        )

    def test_skips_intermediate_message_with_tool_use(self) -> None:
        """Assistant messages that include a ``toolUse`` block are skipped."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "I'll check the page first."},
                    {"toolUse": {"toolUseId": "tu_1", "name": "browser", "input": {}}},
                ],
            },
        }))

        self.assertEqual(streamer.final_assistant_text, "")

    def test_skips_user_messages(self) -> None:
        """User-role messages do not update final_assistant_text."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "user",
                "content": [{"text": "Go to example.com"}],
            },
        }))

        self.assertEqual(streamer.final_assistant_text, "")

    def test_result_event_overrides_earlier_message_capture(self) -> None:
        """A terminal ``result`` event overrides earlier message-level capture.

        This mirrors the event ordering Strands produces: a text-only
        ``message`` event may fire during the final cycle before the
        ``result`` event arrives. Since the ``result`` event carries the
        authoritative AgentResult, it must win.
        """
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [{"text": "intermediate final text"}],
            },
        }))
        self.assertEqual(streamer.final_assistant_text, "intermediate final text")

        _run(streamer._process_event({
            "result": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "authoritative final answer"}],
                },
            },
        }))
        self.assertEqual(
            streamer.final_assistant_text,
            "authoritative final answer",
        )

    def test_multiple_text_blocks_are_concatenated(self) -> None:
        """Multiple text blocks in the message content concatenate in order."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Chunk 1. "},
                    {"text": "Chunk 2. "},
                    {"text": "Chunk 3."},
                ],
            },
        }))

        self.assertEqual(
            streamer.final_assistant_text,
            "Chunk 1. Chunk 2. Chunk 3.",
        )

    def test_non_list_content_is_ignored(self) -> None:
        """Defensive: non-list ``content`` does not crash or update state."""
        streamer, _, _ = _make_streamer()

        _run(streamer._process_event({
            "message": {"role": "assistant", "content": "not a list"},
        }))

        self.assertEqual(streamer.final_assistant_text, "")

    def test_result_event_does_not_send_any_frame(self) -> None:
        """Capturing final text must not emit any WebSocket frame itself."""
        streamer, mock_ws, _ = _make_streamer()

        _run(streamer._process_event({
            "result": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "done"}],
                },
            },
        }))

        mock_ws.send_json.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
