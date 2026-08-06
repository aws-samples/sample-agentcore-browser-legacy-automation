# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""HandoffToUserTool — WebSocket-backed replacement for strands_tools.handoff_to_user.

The Strands built-in `handoff_to_user` tool calls `prompt_toolkit.PromptSession`
to read a response from stdin with a literal "Your response:" prompt. That is
correct for a desktop Strands app but catastrophic inside a headless container:
the blocking stdin read either hangs forever or EOFs — and during local dev it
popped up a terminal prompt, blocking the entire agent event loop on the
developer's TTY.

This tool replaces that behaviour with the correct headless pattern:

    1. Claude calls `handoff_to_user(message=...)` from within a tool worker
       thread (Strands dispatches tool calls via `asyncio.to_thread`).
    2. The tool marshals a `BROWSER_HITL_PROMPT` frame onto the handler's main
       asyncio event loop and emits it to the WebSocket client.
    3. The tool then waits — still from the worker thread — for the handler to
       receive a `BROWSER_HITL_RESPONSE` frame and set the handler's
       `hitl_event`. The browser microVM session stays alive the whole time
       because no close is issued.
    4. When the response arrives, the tool returns the user's text to Claude as
       a normal tool result string, and the ReAct loop continues naturally.
    5. On timeout (`BA_HITL_TIMEOUT_SECONDS`, default 300s), the tool returns a
       deterministic error string to Claude so the agent can decide whether to
       retry, give up, or try a different approach. The handler has already
       emitted `BROWSER_HITL_TIMEOUT` to the client as part of its
       `wait_for_hitl_response` bookkeeping.

The `breakout_of_loop` parameter from the Strands schema is accepted for prompt
compatibility but treated as False — this tool always waits for the response
because the WebSocket chat flow depends on Claude resuming with the answer.

This module has ZERO stdin, stdout, or `prompt_toolkit` dependencies.
"""

import asyncio
import os
import uuid
from logging import Logger
from typing import Any, Dict, Optional

from utils.logging_helper import get_logger

from models.websocket_message_types import BrowserMessageType


class HandoffToUserTool:
    """Drop-in replacement for `strands_tools.handoff_to_user` that talks WebSocket.

    The tool is composed onto `VisualBrowserTool` and exposes a single
    `@tool`-decorated method (`handoff_to_user`). Before the first tool call
    the `BrowserHandler` must invoke `set_hitl_context(...)` to wire the tool
    to the WebSocket adapter, the main event loop, and the handler-provided
    `wait_for_hitl_response` coroutine.

    Thread model:
        - `set_hitl_context` runs on the handler's main event loop. It captures
          the running loop so the tool can schedule coroutines onto it later.
        - `handoff_to_user` runs inside a Strands tool worker thread. It uses
          `asyncio.run_coroutine_threadsafe` to jump back to the main loop.

    Attributes:
        logger: Module-level logger.
        _websocket: WebSocket adapter — set by `set_hitl_context`. None when
            the tool is called outside of an active chat session (a programming
            error — the tool will return an error result, not crash).
        _wait_for_response: Bound coroutine on the handler that awaits
            `BROWSER_HITL_RESPONSE`. Returns the payload dict or None on
            timeout.
        _loop: The handler's main asyncio event loop. Captured in
            `set_hitl_context` via `asyncio.get_running_loop()`.
    """

    logger: Logger = get_logger(f"{__name__}.HandoffToUserTool")

    def __init__(self) -> None:
        self._websocket: Optional[Any] = None
        self._wait_for_response: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._timeout_seconds: float = float(
            os.environ.get("BA_HITL_TIMEOUT_SECONDS", "300")
        )

    def set_hitl_context(
        self,
        websocket: Any,
        wait_for_response: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Wire the tool to the handler's WebSocket + response waiter.

        Args:
            websocket: The handler's WebSocket adapter. Must expose
                `send_json(dict) -> Awaitable[None]`.
            wait_for_response: Coroutine function on the handler that awaits
                `BROWSER_HITL_RESPONSE` and returns the payload dict (or None
                on timeout). Signature: `async def (timeout: float) -> dict | None`.
            loop: Optional event loop to target. Defaults to the currently
                running loop at call time. The caller is responsible for
                invoking this from a context that has a running event loop
                (i.e., from inside the handler's async code).
        """
        self._websocket = websocket
        self._wait_for_response = wait_for_response
        if loop is not None:
            self._loop = loop
        else:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
                self.logger.warning(
                    "set_hitl_context called without a running event loop; "
                    "handoff_to_user will fail until the loop is set."
                )

    def clear_hitl_context(self) -> None:
        """Drop the cached WebSocket / loop references.

        Called by the handler when the browser session terminates so the tool
        doesn't hold stale references across sessions.
        """
        self._websocket = None
        self._wait_for_response = None
        self._loop = None

    def invoke(
        self, message: str, breakout_of_loop: bool = False,
    ) -> Dict[str, Any]:
        """Hand off control to the human user and wait for their response.

        This is the real implementation. The `@tool`-decorated wrapper lives
        on `VisualBrowserTool.handoff_to_user` and simply delegates here, so
        Strands owns a single tool definition and this class stays decorator-
        free.

        Args:
            message: The question or instruction to present to the user.
            breakout_of_loop: Accepted for prompt-compat; always treated as
                False (see module docstring).

        Returns:
            A tool result dict with `status="success"` and the user's response
            text, or `status="error"` with an explanation on missing wiring or
            timeout.
        """
        # breakout_of_loop is deliberately unused — documented above.
        del breakout_of_loop

        if (
            self._websocket is None
            or self._wait_for_response is None
            or self._loop is None
        ):
            self.logger.error(
                "handoff_to_user invoked without HITL context; "
                "set_hitl_context must be called before the first tool call."
            )
            return {
                "status": "error",
                "content": [
                    {
                        "text": (
                            "HITL is not available in this context. "
                            "The browser session is not attached to an "
                            "interactive client."
                        )
                    }
                ],
            }

        prompt_id: str = str(uuid.uuid4())
        self.logger.info(
            "HITL handoff requested: prompt_id=%s message_preview=%s",
            prompt_id,
            (message or "")[:120],
        )

        # Step 1: emit BROWSER_HITL_PROMPT on the main event loop.
        prompt_payload: Dict[str, Any] = {
            "type": BrowserMessageType.BROWSER_HITL_PROMPT,
            "promptId": prompt_id,
            "question": message,
            "options": [],
            "context": "",
            "screenshotBase64": "",
        }
        try:
            send_future = asyncio.run_coroutine_threadsafe(
                self._websocket.send_json(prompt_payload), self._loop,
            )
            # Small timeout — this is just scheduling the send, not waiting
            # for the user.
            send_future.result(timeout=10)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to send BROWSER_HITL_PROMPT: prompt_id=%s error=%s",
                prompt_id,
                str(exc),
            )
            return {
                "status": "error",
                "content": [
                    {"text": "Failed to deliver HITL prompt: %s" % str(exc)}
                ],
            }

        # Step 2: await BROWSER_HITL_RESPONSE via the handler's coroutine.
        try:
            wait_future = asyncio.run_coroutine_threadsafe(
                self._wait_for_response(self._timeout_seconds), self._loop,
            )
            # Add a grace margin so the inner asyncio.wait_for timeout wins
            # over this thread-side wait. If the handler's timeout fires, its
            # coroutine returns None cleanly; we should never hit this outer
            # timeout unless the loop is stuck.
            response_payload: Optional[dict] = wait_future.result(
                timeout=self._timeout_seconds + 30,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(
                "HITL wait failed: prompt_id=%s error=%s",
                prompt_id,
                str(exc),
            )
            return {
                "status": "error",
                "content": [
                    {
                        "text": (
                            "Error while waiting for user response: %s" % str(exc)
                        )
                    }
                ],
            }

        if response_payload is None:
            self.logger.warning(
                "HITL timed out with no response: prompt_id=%s timeout=%ss",
                prompt_id,
                self._timeout_seconds,
            )
            return {
                "status": "error",
                "content": [
                    {
                        "text": (
                            "The user did not respond within %d seconds. "
                            "Decide whether to retry, try a different "
                            "approach, or give up."
                            % int(self._timeout_seconds)
                        )
                    }
                ],
            }

        response_text: str = str(response_payload.get("value", "")).strip()
        response_action: str = str(response_payload.get("action", "")).strip()
        response_prompt_id: str = str(response_payload.get("promptId", "")).strip()

        if response_prompt_id and response_prompt_id != prompt_id:
            self.logger.warning(
                "HITL response promptId mismatch: expected=%s received=%s",
                prompt_id,
                response_prompt_id,
            )

        self.logger.info(
            "HITL response received: prompt_id=%s action=%s len=%d",
            prompt_id,
            response_action or "<unset>",
            len(response_text),
        )

        if not response_text:
            # The user either clicked an option without typing, or sent an
            # empty message. Fall back to the action name so Claude still has
            # something to work with.
            response_text = response_action or "(empty response)"

        return {
            "status": "success",
            "content": [{"text": "User response: %s" % response_text}],
        }
