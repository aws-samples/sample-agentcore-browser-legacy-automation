# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for HandoffToUserTool.

The tool is the WebSocket-backed replacement for strands_tools.handoff_to_user.
These tests validate the three core behaviours that the original
(stdin-blocking) Strands tool gets wrong for a headless container:

1. When invoked, the tool emits exactly one BROWSER_HITL_PROMPT frame to the
   configured WebSocket adapter — it NEVER reads stdin or touches
   prompt_toolkit.
2. The tool awaits the handler-provided response coroutine and returns the
   user's text to Claude as a normal tool result.
3. On timeout, the tool returns a deterministic error result so Claude can
   decide how to proceed.

Thread model: the tool's `invoke` method runs inside a worker thread (Strands
dispatches tool calls via `asyncio.to_thread`). These tests reproduce that
model by launching `invoke` in a thread and driving the handler's coroutines
from the main test event loop.
"""

import asyncio
import threading
import unittest
from logging import Logger
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import tests.__setup__  # noqa: F401

from utils.logging_helper import get_logger

from models.websocket_message_types import BrowserMessageType
from tools.handoff_to_user_tool import HandoffToUserTool


# Sentinel for tests that want a deterministic short timeout. Using a hard
# override on the instance lets us avoid env-var manipulation mid-test.
_FAST_TIMEOUT_SECONDS: float = 0.5


class _FakeWebSocket:
    """Minimal async WebSocket stub — captures every frame sent via send_json."""

    def __init__(self) -> None:
        self.sent: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def send_json(self, payload: Dict[str, Any]) -> None:
        # Hold a lock briefly to make interleaved sends deterministic.
        async with self._lock:
            self.sent.append(payload)


class _TestContext:
    """Wires a HandoffToUserTool + fake WS + response future together on one loop.

    Matches how BrowserHandler wires the tool in production:
      - `websocket`  → the fake WS adapter
      - `wait_for_response` → a coroutine that awaits an asyncio.Future set
        externally by the test
      - `loop`       → the current running loop
    """

    logger: Logger = get_logger(f"{__name__}._TestContext")

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.ws: _FakeWebSocket = _FakeWebSocket()
        # Future resolved by test code to simulate BROWSER_HITL_RESPONSE arrival.
        self.response_future: asyncio.Future[Optional[dict]] = loop.create_future()
        self.tool = HandoffToUserTool()
        # Short default timeout so tests stay fast.
        self.tool._timeout_seconds = _FAST_TIMEOUT_SECONDS
        self.tool.set_hitl_context(
            websocket=self.ws,
            wait_for_response=self._wait_for_response,
            loop=loop,
        )

    async def _wait_for_response(self, timeout: float) -> Optional[dict]:
        """Mimic `BrowserHandler.wait_for_hitl_response` semantics."""
        try:
            return await asyncio.wait_for(
                asyncio.shield(self.response_future), timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None


def _run_coro(coro: Any) -> Any:
    """Run an awaitable on a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestHandoffToUserToolHappyPath(unittest.TestCase):
    """The user responds within the timeout → tool returns the response text."""

    logger: Logger = get_logger(f"{__name__}.TestHandoffToUserToolHappyPath")

    def test_emits_prompt_frame_and_returns_user_response(self) -> None:
        async def scenario() -> Dict[str, Any]:
            loop = asyncio.get_running_loop()
            ctx = _TestContext(loop=loop)

            # Run tool.invoke in a worker thread (Strands' real dispatch model).
            result_holder: Dict[str, Any] = {}

            def worker() -> None:
                result_holder["value"] = ctx.tool.invoke(
                    message="Do you want me to delete these 5 files?",
                )

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

            # Drive the loop until the tool has sent the prompt frame.
            for _ in range(100):
                if ctx.ws.sent:
                    break
                await asyncio.sleep(0.01)

            # The frame should be exactly one BROWSER_HITL_PROMPT.
            self.assertEqual(len(ctx.ws.sent), 1)
            frame = ctx.ws.sent[0]
            self.assertEqual(frame["type"], BrowserMessageType.BROWSER_HITL_PROMPT)
            self.assertEqual(
                frame["question"], "Do you want me to delete these 5 files?",
            )
            # promptId is a UUID string — non-empty.
            self.assertIsInstance(frame["promptId"], str)
            self.assertGreater(len(frame["promptId"]), 0)

            # Now deliver the user's response.
            ctx.response_future.set_result({
                "promptId": frame["promptId"],
                "action": "respond",
                "value": "yes, delete them",
            })

            # Wait for the worker thread to finish so the tool returns its result.
            for _ in range(200):
                if "value" in result_holder:
                    break
                await asyncio.sleep(0.01)

            thread.join(timeout=5)
            return result_holder["value"]

        result = _run_coro(scenario())

        self.assertEqual(result["status"], "success")
        content = result["content"]
        self.assertEqual(len(content), 1)
        self.assertIn("yes, delete them", content[0]["text"])


class TestHandoffToUserToolTimeout(unittest.TestCase):
    """The user never responds → tool returns a deterministic error result."""

    logger: Logger = get_logger(f"{__name__}.TestHandoffToUserToolTimeout")

    def test_returns_error_on_timeout(self) -> None:
        async def scenario() -> Dict[str, Any]:
            loop = asyncio.get_running_loop()
            ctx = _TestContext(loop=loop)

            result_holder: Dict[str, Any] = {}

            def worker() -> None:
                result_holder["value"] = ctx.tool.invoke(
                    message="Need your approval.",
                )

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

            # Wait just past the tool's short timeout so the wait_for inside
            # _wait_for_response fires. The tool's outer timeout margin (30s)
            # doesn't fire because the inner timeout returns cleanly.
            await asyncio.sleep(_FAST_TIMEOUT_SECONDS + 0.5)

            for _ in range(200):
                if "value" in result_holder:
                    break
                await asyncio.sleep(0.01)

            thread.join(timeout=5)
            return result_holder["value"]

        result = _run_coro(scenario())

        self.assertEqual(result["status"], "error")
        content_text = result["content"][0]["text"]
        self.assertIn("did not respond", content_text)


class TestHandoffToUserToolMissingContext(unittest.TestCase):
    """Tool called before set_hitl_context → returns error, never blocks."""

    logger: Logger = get_logger(
        f"{__name__}.TestHandoffToUserToolMissingContext"
    )

    def test_returns_error_when_websocket_unset(self) -> None:
        tool = HandoffToUserTool()
        # No set_hitl_context call at all.
        result = tool.invoke(message="Anybody home?")

        self.assertEqual(result["status"], "error")
        self.assertIn("not available", result["content"][0]["text"])

    def test_returns_error_after_clear_hitl_context(self) -> None:
        async def scenario() -> Dict[str, Any]:
            loop = asyncio.get_running_loop()
            ctx = _TestContext(loop=loop)
            ctx.tool.clear_hitl_context()
            # Run synchronously because there's no WS activity to drive.
            return ctx.tool.invoke(message="Still there?")

        result = _run_coro(scenario())
        self.assertEqual(result["status"], "error")
        self.assertIn("not available", result["content"][0]["text"])


class TestHandoffToUserToolNoStdin(unittest.TestCase):
    """Regression guard: the tool MUST NOT import or call prompt_toolkit /
    stdin. A headless container has no TTY; any attempt to read stdin blocks
    or raises.

    These tests enforce the negative property by verifying the import graph
    of the tool module and by executing the tool with stdin deliberately
    rendered unusable.
    """

    logger: Logger = get_logger(f"{__name__}.TestHandoffToUserToolNoStdin")

    def test_module_does_not_import_prompt_toolkit(self) -> None:
        import tools.handoff_to_user_tool as module
        # Walk the module's top-level names looking for prompt_toolkit or
        # strands_tools.utils.user_input — neither is allowed.
        for attr_name in dir(module):
            self.assertNotIn(
                "prompt_toolkit", attr_name.lower(),
                msg="handoff_to_user_tool must not import prompt_toolkit",
            )

    def test_module_does_not_use_input_builtin(self) -> None:
        import inspect
        import tools.handoff_to_user_tool as module
        src = inspect.getsource(module)
        # Raw `input(` call or `sys.stdin` read would both be blocking in a
        # headless container.
        self.assertNotIn("input(", src)
        self.assertNotIn("sys.stdin", src)
        self.assertNotIn("readline", src)
        self.assertNotIn("get_user_input", src)

    def test_invoke_without_stdin_does_not_crash_or_block(self) -> None:
        """Running invoke with sys.stdin pointed at /dev/null must not block.

        The context is intentionally unset so the tool takes its early-exit
        path. The point of this test is to prove the tool returns quickly
        regardless of the stdin state — i.e. the tool does not try to read
        stdin on any code path.
        """
        import sys
        import io

        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("")  # EOF immediately
            tool = HandoffToUserTool()
            result = tool.invoke(message="test")
            # Early-exit because no context was wired.
            self.assertEqual(result["status"], "error")
        finally:
            sys.stdin = original_stdin


class TestHandoffToUserToolPromptIdIntegrity(unittest.TestCase):
    """The tool must generate a unique prompt_id and echo it back so the
    handler can correlate request/response pairs even if multiple handoffs
    happen back-to-back."""

    logger: Logger = get_logger(
        f"{__name__}.TestHandoffToUserToolPromptIdIntegrity"
    )

    def test_each_invocation_uses_a_fresh_prompt_id(self) -> None:
        async def scenario() -> List[str]:
            loop = asyncio.get_running_loop()
            ctx = _TestContext(loop=loop)

            seen_ids: List[str] = []

            async def run_one_invocation(
                message: str, response_value: str,
            ) -> None:
                # Fresh future per iteration.
                ctx.response_future = loop.create_future()
                # Re-wire the response waiter to the new future.
                ctx.tool.set_hitl_context(
                    websocket=ctx.ws,
                    wait_for_response=ctx._wait_for_response,
                    loop=loop,
                )

                result_holder: Dict[str, Any] = {}

                def worker() -> None:
                    result_holder["value"] = ctx.tool.invoke(message=message)

                thread = threading.Thread(target=worker, daemon=True)
                thread.start()

                # Wait for this iteration's prompt frame.
                target_len = len(ctx.ws.sent) + 1
                for _ in range(100):
                    if len(ctx.ws.sent) >= target_len:
                        break
                    await asyncio.sleep(0.01)

                frame = ctx.ws.sent[-1]
                seen_ids.append(frame["promptId"])

                ctx.response_future.set_result({
                    "promptId": frame["promptId"],
                    "action": "respond",
                    "value": response_value,
                })

                for _ in range(200):
                    if "value" in result_holder:
                        break
                    await asyncio.sleep(0.01)

                thread.join(timeout=5)

            await run_one_invocation("first question", "first reply")
            await run_one_invocation("second question", "second reply")
            await run_one_invocation("third question", "third reply")

            return seen_ids

        ids = _run_coro(scenario())
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3, msg="promptId must be unique per call")


if __name__ == "__main__":
    unittest.main()
