# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
BrowserStreamer — Maps Strands Agent events to browser-specific WebSocket frames.

Bridges the Strands Agent streaming event model to the browser WebSocket
protocol, emitting typed frames following the orchestration lifecycle:

    ORCHESTRATION_START → [REASONING] → [BROWSER_ACTION_START → BROWSER_SCREENSHOT
    → BROWSER_ACTION_COMPLETE]* → [STREAM]* → METADATA → ORCHESTRATION_END

Event mapping:
    reasoningText       → REASONING frame
    data                → STREAM frame
    current_tool_use    → BROWSER_ACTION_START (stepNumber incremented)
    message/toolResult  → BROWSER_SCREENSHOT or BROWSER_ACTION_COMPLETE
    finalize            → METADATA + ORCHESTRATION_END

HITL note: BROWSER_HITL_PROMPT / BROWSER_HITL_TIMEOUT frames are emitted by
`HandoffToUserTool` directly, not by this streamer. The handoff_to_user tool
is a blocking tool call — it sends the prompt, awaits the client's response
through `BrowserHandler.wait_for_hitl_response`, and returns the user's text
back to Claude as a normal tool result. This streamer therefore does not
special-case handoff_to_user; it flows through the standard
ACTION_START → ACTION_COMPLETE envelope like any other tool.

Validates: Requirements 8.1, 9.1–9.8
"""

import os
import time
from logging import Logger
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from utils.logging_helper import get_logger
from utils.session_helper import get_boto3_session, get_boto3_client_config

from handlers.session_store import SessionStoreBase
from handlers.screenshot_storage import ScreenshotStorageBase
from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter
from models.websocket_message_types import BrowserMessageType

# Tool names from browser agent tools. The handoff_to_user tool is NOT routed
# here — it emits BROWSER_HITL_PROMPT / awaits BROWSER_HITL_RESPONSE directly
# via `HandoffToUserTool` because it needs to block on the response, which the
# streamer's one-shot event mapping cannot express.
_SCREENSHOT_TOOL: str = "screenshot_for_vision"
_SEMANTIC_ACTION_TOOL: str = "semantic_action"
_BROWSER_TOOL: str = "browser"
_ACCESSIBILITY_TOOL: str = "accessibility_snapshot"


class BrowserStreamer:
    """Maps Strands Agent events to browser-specific WebSocket frames.

    Event mapping (Strands ``stream_async`` dict keys):
        ``current_tool_use``  → BROWSER_ACTION_START with stepNumber
        ``reasoningText``     → REASONING frame
        ``data``              → STREAM frame
        ``message``           → intercept toolResult for screenshots + action completes

    HITL frames (BROWSER_HITL_PROMPT, BROWSER_HITL_TIMEOUT) are emitted by
    ``HandoffToUserTool`` directly, not by this streamer.

    Validates: Requirements 8.1, 9.1–9.8
    """

    logger: Logger = get_logger(f"{__name__}.BrowserStreamer")

    def __init__(
        self,
        websocket: StarletteWebSocketAdapter,
        session_store: SessionStoreBase,
        screenshot_storage: ScreenshotStorageBase,
        user_id: str,
        session_id: str,
    ) -> None:
        self.ws: StarletteWebSocketAdapter = websocket
        self.session_store: SessionStoreBase = session_store
        self.screenshot_storage: ScreenshotStorageBase = screenshot_storage
        self.user_id: str = user_id
        self.session_id: str = session_id
        self.step_counter: int = 0
        self.start_time: float = 0.0
        self._pending_tool_name: Optional[str] = None
        self._pending_tool_input: Optional[dict] = None
        self._pending_tool_use_id: Optional[str] = None
        # Accumulated assistant text for conversation-history persistence.
        # The handler reads ``final_assistant_text`` after ``stream_events``
        # returns and writes it back to the session store so resume brings
        # back both sides of the conversation (Issue 4 in
        # ``.kiro/research/temp-browser-ui-issues-analysis.md``).
        self.final_assistant_text: str = ""
        # Buffered ``data`` chunks awaiting classification as REASONING vs
        # STREAM (Issue 3 in the same research doc). Strands emits ``data``
        # text chunks for BOTH pre-tool narration and the final answer, so
        # we buffer them until the enclosing assistant ``message`` event
        # arrives and tells us which kind it was (toolUse present → pre-tool
        # narration → REASONING; text-only → final answer → STREAM).
        self._data_buffer: List[str] = []
        self._reached_final_answer: bool = False

    async def stream_events(self, agent: Any, query: str) -> None:
        """Stream orchestration events from a Strands Agent invocation.

        Emits the full orchestration lifecycle to the WebSocket:
        ORCHESTRATION_START → events → METADATA → ORCHESTRATION_END.

        Validates: Requirement 9.7
        """
        self.start_time = time.time()
        # Reset per-turn state so back-to-back chats on the same connection
        # don't carry over buffered text or the final-answer flag.
        self._data_buffer = []
        self._reached_final_answer = False
        self.final_assistant_text = ""

        await self.ws.send_json({
            "type": BrowserMessageType.ORCHESTRATION_START,
        })

        try:
            async for event in agent.stream_async(query):
                await self._process_event(event)
        except Exception as exc:
            self.logger.error("Streaming error: %s", str(exc))
            await self.ws.send_json({
                "type": BrowserMessageType.ERROR,
                "content": str(exc),
                "recoverable": True,
            })

        # Drain any unclassified buffer before finalizing. If we got here
        # with buffered data that was never paired with a message event,
        # treat it as STREAM (best guess — late text after the last tool).
        await self._flush_data_buffer_as(BrowserMessageType.STREAM)

        await self._finalize()

    async def _process_event(self, event: dict) -> None:
        """Route a single Strands event to the appropriate UI frame.

        Validates: Requirements 9.1–9.5
        """
        if not isinstance(event, dict):
            return

        # Tool use streaming — detect browser tool invocations
        current_tool_use: Optional[dict] = event.get("current_tool_use")
        if current_tool_use is not None:
            await self._handle_tool_use(current_tool_use)
            return

        # Reasoning events (extended-thinking models only — Sonnet without
        # thinking budget does NOT emit these; those models surface
        # reasoning prose through ``data`` chunks which we classify via
        # the buffered-data path below).
        reasoning_text: Optional[str] = event.get("reasoningText")
        if reasoning_text:
            await self._handle_reasoning(reasoning_text)
            return

        # Agent completion — Strands emits a terminal event with a
        # ``result`` key holding the AgentResult. Capture the final
        # assistant text so the handler can persist it to the session
        # store for resume-fidelity (see docstring on ``final_assistant_text``).
        result_obj: Any = event.get("result")
        if result_obj is not None:
            self._capture_final_text_from_result(result_obj)
            return

        # Message events — intercept toolResult for screenshots/actions/HITL
        # AND classify any buffered ``data`` chunks based on the message's
        # content shape (toolUse block → REASONING; text-only → STREAM).
        message: Optional[dict] = event.get("message")
        if message is not None:
            self._capture_final_text_from_message(message)
            await self._classify_buffered_data_for_message(message)
            await self._handle_tool_result(message)
            return

        # Text data events — buffer until the enclosing ``message`` event
        # tells us how to classify them (Issue 3 in
        # ``.kiro/research/temp-browser-ui-issues-analysis.md``).
        data: str = event.get("data", "")
        if data:
            await self._handle_data(data)

    async def _classify_buffered_data_for_message(self, message: dict) -> None:
        """Classify pending ``_data_buffer`` contents based on message shape.

        Called for every assistant ``message`` event that arrives during
        streaming. The buffer accumulates ``data`` chunks that preceded
        this message; the message's content shape determines how those
        chunks were intended:

        - ``role='assistant'`` with any ``toolUse`` block → this cycle ended
          with a tool call, so the buffered text was pre-tool narration.
          Flush as REASONING.
        - ``role='assistant'`` with only text blocks → this was the final
          assistant message. Flush the buffered text as STREAM and set
          ``_reached_final_answer`` so subsequent ``data`` chunks (a rare
          trailing-text case) dispatch as STREAM immediately.
        - Any other message role (e.g. ``user`` toolResult) → do nothing;
          the buffered data belongs to a different cycle we haven't seen
          the boundary message for yet.

        Issue 3 rationale: Strands does not distinguish between reasoning
        prose and final answer at the ``data``-event level for models
        without extended thinking. The assistant ``message`` event — which
        Strands emits AFTER its text-content cycle completes — is the
        reliable structural boundary we use to classify.
        """
        if not isinstance(message, dict):
            return
        if message.get("role") != "assistant":
            return

        content: Any = message.get("content")
        if not isinstance(content, list):
            return

        has_tool_use: bool = any(
            isinstance(block, dict) and "toolUse" in block for block in content
        )

        if has_tool_use:
            # Pre-tool narration — flush buffer as REASONING.
            await self._flush_data_buffer_as(BrowserMessageType.REASONING)
        else:
            # Final assistant message — flush buffer as STREAM and latch the
            # flag. Any trailing ``data`` chunks emitted after this message
            # (rare but possible) will dispatch as STREAM directly.
            await self._flush_data_buffer_as(BrowserMessageType.STREAM)
            self._reached_final_answer = True

    async def _flush_data_buffer_as(self, frame_type: str) -> None:
        """Dispatch the accumulated ``_data_buffer`` as a single typed frame
        and clear the buffer.

        The buffer is flushed as one concatenated frame (not per-chunk) so
        the network overhead is predictable. The UI accumulates frame
        content into the current assistant message either way — REASONING
        into ``agentMetadata.browser.reasoning``, STREAM into
        ``message.content``.
        """
        if not self._data_buffer:
            return
        combined: str = "".join(self._data_buffer)
        self._data_buffer = []
        if not combined:
            return
        await self.ws.send_json({
            "type": frame_type,
            "content": combined,
        })

    def _capture_final_text_from_result(self, result_obj: Any) -> None:
        """Extract final assistant text from a Strands AgentResult event.

        Called when Strands yields its terminal ``{"result": AgentResult}``
        event. The AgentResult's ``message`` attribute holds the final
        assistant turn as a Bedrock-style dict with a ``content`` list of
        text blocks. We concatenate text blocks and store the result on
        ``self.final_assistant_text`` — the most authoritative answer text
        available, and preferred over the incremental capture from
        ``_capture_final_text_from_message``.
        """
        message: Any = None
        if hasattr(result_obj, "message"):
            message = getattr(result_obj, "message")
        elif isinstance(result_obj, dict):
            message = result_obj.get("message")

        if isinstance(message, dict):
            extracted = self._extract_text_from_message(message)
            if extracted:
                self.final_assistant_text = extracted

    def _capture_final_text_from_message(self, message: dict) -> None:
        """Update ``final_assistant_text`` from a terminal assistant message.

        A terminal assistant message has role ``assistant`` and content
        blocks that are all plain ``text`` — no ``toolUse`` blocks. Intermediate
        assistant messages (the ones announcing tool calls) contain
        ``toolUse`` blocks and are skipped. This captures the running
        "best guess" at the final text even if the Strands runtime never
        emits a ``result`` event (defensive fallback).
        """
        if message.get("role") != "assistant":
            return

        content: Any = message.get("content")
        if not isinstance(content, list):
            return

        # Skip messages that contain tool_use blocks — those are
        # intermediate tool-calling turns.
        for block in content:
            if isinstance(block, dict) and "toolUse" in block:
                return

        extracted = self._extract_text_from_message(message)
        if extracted:
            self.final_assistant_text = extracted

    @staticmethod
    def _extract_text_from_message(message: dict) -> str:
        """Concatenate all ``text`` blocks in a Bedrock-style message's content."""
        content: Any = message.get("content")
        if not isinstance(content, list):
            return ""
        parts: List[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            text_value = block.get("text")
            if isinstance(text_value, str) and text_value:
                parts.append(text_value)
        return "".join(parts)

    async def _handle_tool_use(self, tool_use: dict) -> None:
        """Detect browser tool invocation and send BROWSER_ACTION_START.

        Increments stepNumber on each new tool invocation. Tracks the
        pending tool name and input for result correlation.

        Validates: Requirements 9.4, 9.5
        """
        tool_name: str = tool_use.get("name", "")
        tool_use_id: str = tool_use.get("toolUseId", "")

        # Skip if we already processed this tool invocation
        if self._pending_tool_use_id == tool_use_id:
            return

        # Only track browser-related tools
        if tool_name not in (
            _SCREENSHOT_TOOL, _SEMANTIC_ACTION_TOOL,
            _BROWSER_TOOL, _ACCESSIBILITY_TOOL,
        ):
            return

        self._pending_tool_use_id = tool_use_id
        self._pending_tool_name = tool_name
        self._pending_tool_input = tool_use.get("input", {})
        if isinstance(self._pending_tool_input, str):
            self._pending_tool_input = {}

        self.step_counter += 1

        # Determine action type and details
        action_type: str = tool_name
        details: str = ""
        if isinstance(self._pending_tool_input, dict):
            if tool_name == _SEMANTIC_ACTION_TOOL:
                semantic_input = self._pending_tool_input.get(
                    "semantic_input", {}
                )
                if isinstance(semantic_input, dict):
                    details = semantic_input.get("action", "")
            elif tool_name == _BROWSER_TOOL:
                details = self._pending_tool_input.get("action", "")
            elif tool_name == _SCREENSHOT_TOOL:
                details = self._pending_tool_input.get("title", "")

        await self.ws.send_json({
            "type": BrowserMessageType.BROWSER_ACTION_START,
            "actionType": action_type,
            "details": details,
            "stepNumber": self.step_counter,
        })

    async def _handle_tool_result(self, message: dict) -> None:
        """Process tool results: screenshots and action completions.

        HITL tool results (from ``handoff_to_user``) are handled inline by
        ``HandoffToUserTool`` — by the time Claude sees the tool result, the
        prompt has already been delivered and the response has been returned
        as the tool's content. No streamer-level routing required.

        Validates: Requirements 9.3, 9.5
        """
        content: list = message.get("content", [])
        if not isinstance(content, list):
            return

        for block in content:
            if not isinstance(block, dict):
                continue

            tool_result: Optional[dict] = block.get("toolResult")
            if tool_result is None:
                continue

            result_id: str = tool_result.get("toolUseId", "")
            result_content: list = tool_result.get("content", [])

            # Determine which tool this result belongs to
            tool_name: str = self._pending_tool_name or ""
            if result_id != self._pending_tool_use_id:
                tool_name = ""

            if tool_name == _SCREENSHOT_TOOL:
                await self._send_screenshot_frame(result_content)
                await self._send_action_complete(result_content, tool_name)
            elif tool_name in (_SEMANTIC_ACTION_TOOL, _BROWSER_TOOL, _ACCESSIBILITY_TOOL):
                await self._send_action_complete(result_content, tool_name)

            # Clear pending tool tracking after processing
            if result_id == self._pending_tool_use_id:
                self._pending_tool_use_id = None
                self._pending_tool_name = None
                self._pending_tool_input = None

    async def _send_screenshot_frame(self, result_content: list) -> None:
        """Extract screenshot info from tool result and send BROWSER_SCREENSHOT.

        IMPORTANT: The screenshot bytes are NOT sent inline. A viewport PNG
        screenshot is typically 100-500KB raw (130-670KB base64-encoded),
        which exceeds AgentCore Runtime's 32KB WebSocket frame size limit.
        Sending the base64 image inline causes the relay to terminate the
        connection without a close frame.

        Instead, we send the S3 path and a pre-signed URL so the UI can
        fetch the image directly from S3 without AWS credentials.

        Pre-signed URL expiry is controlled by BA_SCREENSHOT_URL_EXPIRY_MINUTES
        (default: 240 = 4 hours).

        Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html
        Table: "AgentCore Runtime Service Quotas → Invocation limits → WebSocket frame size: 32 KB"

        Validates: Requirement 9.3
        """
        title: str = ""
        if self._pending_tool_input and isinstance(self._pending_tool_input, dict):
            title = self._pending_tool_input.get("title", "")

        # Extract the saved path from the text content (ScreenshotTool returns
        # "Screenshot saved: {path}. Analyze visually to identify elements.").
        # Split on whitespace and take the first token after the marker so the
        # trailing sentence doesn't get glued onto the path.
        saved_path: str = ""
        for item in result_content:
            if not isinstance(item, dict):
                continue
            text: str = item.get("text", "")
            if "Screenshot saved:" in text:
                after_marker: str = text.split("Screenshot saved:", 1)[1]
                tokens = after_marker.split(None, 1)
                if tokens:
                    saved_path = tokens[0].rstrip(".").strip()
                break

        # Check if there's an image block and log its size (but don't send it)
        for item in result_content:
            if not isinstance(item, dict):
                continue
            image_block = item.get("image")
            if image_block and isinstance(image_block, dict):
                source = image_block.get("source", {})
                raw_bytes: bytes = source.get("bytes", b"")
                if raw_bytes:
                    self.logger.info(
                        "Screenshot captured: %d bytes (%.1f KB base64) — sending pre-signed URL, not inline image",
                        len(raw_bytes), len(raw_bytes) * 4 / 3 / 1024,
                    )
                break

        # Generate pre-signed URL for S3 screenshots
        screenshot_url: str = ""
        if saved_path.startswith("s3://"):
            screenshot_url = self._generate_presigned_url(saved_path)

        await self.ws.send_json({
            "type": BrowserMessageType.BROWSER_SCREENSHOT,
            "screenshotPath": saved_path,
            "screenshotUrl": screenshot_url,
            "timestamp": time.time(),
            "title": title,
            "stepNumber": self.step_counter,
        })

    def _generate_presigned_url(self, s3_path: str) -> str:
        """Generate a pre-signed GET URL for an S3 object.

        Args:
            s3_path: Full S3 URI (s3://amzn-s3-demo-bucket/key).

        Returns:
            Pre-signed HTTPS URL, or empty string on failure.
        """
        expiry_minutes: int = int(
            os.environ.get('BA_SCREENSHOT_URL_EXPIRY_MINUTES', '240')
        )
        try:
            parsed = urlparse(s3_path)
            bucket: str = parsed.netloc
            key: str = parsed.path.lstrip('/')

            session = get_boto3_session()
            s3_client = session.client('s3', config=get_boto3_client_config())
            url: str = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiry_minutes * 60,
            )
            self.logger.debug(
                "Pre-signed URL generated: expiry=%dm path=%s",
                expiry_minutes, s3_path,
            )
            return url
        except Exception as exc:
            self.logger.warning(
                "Failed to generate pre-signed URL for %s: %s",
                s3_path, str(exc),
            )
            return ""

    async def _send_action_complete(
        self, result_content: list, tool_name: str
    ) -> None:
        """Send BROWSER_ACTION_COMPLETE frame.

        Validates: Requirement 9.5
        """
        result_text: str = ""
        success: bool = True

        for item in result_content:
            if not isinstance(item, dict):
                continue
            text: str = item.get("text", "")
            if text:
                result_text = text
                break

        if "error" in result_text.lower():
            success = False

        await self.ws.send_json({
            "type": BrowserMessageType.BROWSER_ACTION_COMPLETE,
            "actionType": tool_name,
            "result": result_text,
            "success": success,
            "stepNumber": self.step_counter,
            "currentUrl": "",
        })

    async def _handle_reasoning(self, reasoning_text: str) -> None:
        """Emit a REASONING frame.

        Validates: Requirement 9.1
        """
        await self.ws.send_json({
            "type": BrowserMessageType.REASONING,
            "content": reasoning_text,
        })

    async def _handle_data(self, data: str) -> None:
        """Buffer or dispatch a text chunk based on the final-answer flag.

        Before the final-answer flag flips (we haven't seen a text-only
        assistant message yet), accumulate chunks into ``_data_buffer`` so
        they can be classified together when the enclosing assistant
        ``message`` event arrives.

        After the flag flips, dispatch directly as STREAM — the buffer is
        empty by construction, and any trailing text is part of the
        final answer.

        Validates: Requirement 9.2 (post-fix semantics)
        """
        if self._reached_final_answer:
            await self.ws.send_json({
                "type": BrowserMessageType.STREAM,
                "content": data,
            })
        else:
            self._data_buffer.append(data)

    async def _finalize(self) -> None:
        """Emit closing frames: METADATA + ORCHESTRATION_END.

        Validates: Requirements 9.6, 9.7
        """
        duration_ms: int = int((time.time() - self.start_time) * 1000)

        await self.ws.send_json({
            "type": BrowserMessageType.METADATA,
            "total_duration_ms": duration_ms,
            "steps_completed": self.step_counter,
        })

        # Update session record with steps completed
        await self.session_store.update(self.user_id, self.session_id, {
            'steps_completed': self.step_counter,
        })

        await self.ws.send_json({
            "type": BrowserMessageType.ORCHESTRATION_END,
        })
