# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Starlette WebSocket Adapter for the Browser Agent.

Bridges Starlette WebSocket to the interface expected by BrowserHandler,
providing a consistent async WebSocket API for both AgentCore Runtime
and local Starlette development server entry points.

Includes a 32KB frame size guardrail to prevent oversized frames from
reaching the AgentCore relay, which terminates the WebSocket connection
without a close frame when a frame exceeds the limit.

Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html
Table: "AgentCore Runtime Service Quotas → Invocation limits → WebSocket frame size: 32 KB"

Mirrors concierge-agent-container adapter pattern.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

import json as json_module
from logging import Logger
from typing import Optional, Tuple

from starlette.websockets import WebSocket, WebSocketDisconnect

from utils.logging_helper import get_logger

# AgentCore Runtime WebSocket frame size limit (bytes). Not adjustable.
# Exceeding this causes the relay to terminate the connection silently.
# Source: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html
AGENTCORE_WS_FRAME_LIMIT: int = 32 * 1024  # 32 KB


class StarletteWebSocketAdapter:
    """Adapter bridging Starlette WebSocket to BrowserHandler interface.

    Provides: remote_address, send(), recv(), send_json(), close(),
              __aiter__/__anext__, closed property.
    """

    logger: Logger = get_logger(f"{__name__}.StarletteWebSocketAdapter")

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket: WebSocket = websocket
        self._closed: bool = False

    @property
    def remote_address(self) -> Optional[Tuple[str, int]]:
        """Return the remote client address as (host, port) tuple."""
        return self.websocket.client

    @property
    def closed(self) -> bool:
        """Return whether the WebSocket connection has been closed."""
        return self._closed

    async def send(self, data: str) -> None:
        """Send a text message over the WebSocket."""
        if self._closed:
            self.logger.warning("Attempted send on closed WebSocket")
            return
        await self.websocket.send_text(data)

    async def send_json(self, data: dict) -> None:
        """Send a JSON-serializable dict over the WebSocket.

        Enforces the AgentCore 32KB WebSocket frame size limit as a guardrail.
        If the serialized payload exceeds the limit, the oversized frame is
        blocked and an ERROR frame is sent to the client instead. This
        prevents the AgentCore relay from silently terminating the connection.

        The blocked frame's type and size are logged at ERROR level for
        debugging. The WebSocket connection remains alive.
        """
        if self._closed:
            self.logger.warning("Attempted send_json on closed WebSocket")
            return

        serialized: str = json_module.dumps(data)
        frame_size: int = len(serialized.encode('utf-8'))

        if frame_size > AGENTCORE_WS_FRAME_LIMIT:
            frame_type: str = data.get('type', 'unknown')
            self.logger.error(
                "BLOCKED oversized WebSocket frame: type=%s size=%d bytes (%.1f KB), "
                "limit=%d bytes (32 KB). Frame not sent — connection preserved. "
                "See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html",
                frame_type, frame_size, frame_size / 1024, AGENTCORE_WS_FRAME_LIMIT,
            )
            # Send a small error frame instead so the client knows what happened
            error_frame: str = json_module.dumps({
                'type': 'ERROR',
                'content': (
                    "Frame type '%s' blocked: %d bytes exceeds 32KB AgentCore "
                    "WebSocket frame limit. Data was not sent."
                    % (frame_type, frame_size)
                ),
                'recoverable': True,
            })
            await self.websocket.send_text(error_frame)
            return

        await self.websocket.send_json(data)

    async def recv(self) -> str:
        """Receive a text message from the WebSocket."""
        try:
            return await self.websocket.receive_text()
        except WebSocketDisconnect:
            self._closed = True
            raise

    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection."""
        if not self._closed:
            self._closed = True
            try:
                await self.websocket.close(code=code)
            except Exception as exc:
                self.logger.warning("Error closing WebSocket: %s", str(exc))

    def __aiter__(self):
        """Return self as an async iterator."""
        return self

    async def __anext__(self) -> str:
        """Yield the next text message, raising StopAsyncIteration on disconnect."""
        try:
            return await self.websocket.receive_text()
        except WebSocketDisconnect as exc:
            self._closed = True
            raise StopAsyncIteration from exc
