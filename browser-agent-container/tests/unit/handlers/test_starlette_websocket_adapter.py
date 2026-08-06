# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for StarletteWebSocketAdapter.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.websockets import WebSocketDisconnect

from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter


class TestSendMethod(unittest.TestCase):
    """Test send() method — Requirement 4.1."""

    def setUp(self) -> None:
        self.ws = MagicMock()
        self.ws.send_text = AsyncMock()
        self.adapter = StarletteWebSocketAdapter(self.ws)

    def test_send_delegates_to_send_text(self) -> None:
        """send() calls websocket.send_text with the data."""
        asyncio.get_event_loop().run_until_complete(
            self.adapter.send("hello")
        )
        self.ws.send_text.assert_awaited_once_with("hello")

    def test_send_on_closed_socket_logs_warning_no_raise(self) -> None:
        """send() on closed socket logs warning and returns without raising — Req 4.5."""
        self.adapter._closed = True
        with patch.object(StarletteWebSocketAdapter, "logger") as mock_logger:
            asyncio.get_event_loop().run_until_complete(
                self.adapter.send("data")
            )
            mock_logger.warning.assert_called_once()
        self.ws.send_text.assert_not_awaited()


class TestSendJsonMethod(unittest.TestCase):
    """Test send_json() method — Requirement 4.1."""

    def setUp(self) -> None:
        self.ws = MagicMock()
        self.ws.send_json = AsyncMock()
        self.adapter = StarletteWebSocketAdapter(self.ws)

    def test_send_json_delegates_to_websocket(self) -> None:
        """send_json() calls websocket.send_json with the dict."""
        payload = {"type": "test", "data": "value"}
        asyncio.get_event_loop().run_until_complete(
            self.adapter.send_json(payload)
        )
        self.ws.send_json.assert_awaited_once_with(payload)

    def test_send_json_on_closed_socket_logs_warning(self) -> None:
        """send_json() on closed socket logs warning — Req 4.5."""
        self.adapter._closed = True
        with patch.object(StarletteWebSocketAdapter, "logger") as mock_logger:
            asyncio.get_event_loop().run_until_complete(
                self.adapter.send_json({"type": "test"})
            )
            mock_logger.warning.assert_called_once()
        self.ws.send_json.assert_not_awaited()


class TestRecvMethod(unittest.TestCase):
    """Test recv() method — Requirement 4.1."""

    def setUp(self) -> None:
        self.ws = MagicMock()
        self.ws.receive_text = AsyncMock(return_value='{"type":"ping"}')
        self.adapter = StarletteWebSocketAdapter(self.ws)

    def test_recv_returns_text(self) -> None:
        """recv() returns the text from websocket.receive_text."""
        result = asyncio.get_event_loop().run_until_complete(
            self.adapter.recv()
        )
        self.assertEqual(result, '{"type":"ping"}')

    def test_recv_sets_closed_on_disconnect(self) -> None:
        """recv() sets _closed=True and re-raises WebSocketDisconnect."""
        self.ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        with self.assertRaises(WebSocketDisconnect):
            asyncio.get_event_loop().run_until_complete(
                self.adapter.recv()
            )
        self.assertTrue(self.adapter.closed)


class TestCloseMethod(unittest.TestCase):
    """Test close() method — Requirement 4.1."""

    def setUp(self) -> None:
        self.ws = MagicMock()
        self.ws.close = AsyncMock()
        self.adapter = StarletteWebSocketAdapter(self.ws)

    def test_close_delegates_to_websocket(self) -> None:
        """close() calls websocket.close with the code."""
        asyncio.get_event_loop().run_until_complete(
            self.adapter.close(code=1001)
        )
        self.ws.close.assert_awaited_once_with(code=1001)
        self.assertTrue(self.adapter.closed)

    def test_close_default_code_1000(self) -> None:
        """close() defaults to code 1000."""
        asyncio.get_event_loop().run_until_complete(
            self.adapter.close()
        )
        self.ws.close.assert_awaited_once_with(code=1000)

    def test_close_idempotent(self) -> None:
        """Calling close() twice does not call websocket.close again."""
        asyncio.get_event_loop().run_until_complete(
            self.adapter.close()
        )
        asyncio.get_event_loop().run_until_complete(
            self.adapter.close()
        )
        self.ws.close.assert_awaited_once()

    def test_close_handles_exception_gracefully(self) -> None:
        """close() logs warning if websocket.close raises."""
        self.ws.close = AsyncMock(side_effect=RuntimeError("already closed"))
        with patch.object(StarletteWebSocketAdapter, "logger") as mock_logger:
            asyncio.get_event_loop().run_until_complete(
                self.adapter.close()
            )
            mock_logger.warning.assert_called_once()
        self.assertTrue(self.adapter.closed)


class TestRemoteAddressProperty(unittest.TestCase):
    """Test remote_address property — Requirement 4.2."""

    def test_returns_client_tuple(self) -> None:
        """remote_address returns websocket.client."""
        ws = MagicMock()
        ws.client = ("127.0.0.1", 8080)
        adapter = StarletteWebSocketAdapter(ws)
        self.assertEqual(adapter.remote_address, ("127.0.0.1", 8080))

    def test_returns_none_when_no_client(self) -> None:
        """remote_address returns None when websocket.client is None."""
        ws = MagicMock()
        ws.client = None
        adapter = StarletteWebSocketAdapter(ws)
        self.assertIsNone(adapter.remote_address)


class TestClosedProperty(unittest.TestCase):
    """Test closed property — Requirement 4.3."""

    def test_initially_false(self) -> None:
        """closed is False on fresh adapter."""
        ws = MagicMock()
        adapter = StarletteWebSocketAdapter(ws)
        self.assertFalse(adapter.closed)

    def test_true_after_close(self) -> None:
        """closed is True after close() is called."""
        ws = MagicMock()
        ws.close = AsyncMock()
        adapter = StarletteWebSocketAdapter(ws)
        asyncio.get_event_loop().run_until_complete(adapter.close())
        self.assertTrue(adapter.closed)


class TestAsyncIteration(unittest.TestCase):
    """Test __aiter__/__anext__ — Requirement 4.4."""

    def test_aiter_returns_self(self) -> None:
        """__aiter__ returns the adapter itself."""
        ws = MagicMock()
        adapter = StarletteWebSocketAdapter(ws)
        self.assertIs(adapter.__aiter__(), adapter)

    def test_anext_returns_message(self) -> None:
        """__anext__ returns text from receive_text."""
        ws = MagicMock()
        ws.receive_text = AsyncMock(return_value="msg1")
        adapter = StarletteWebSocketAdapter(ws)
        result = asyncio.get_event_loop().run_until_complete(
            adapter.__anext__()
        )
        self.assertEqual(result, "msg1")

    def test_anext_raises_stop_on_disconnect(self) -> None:
        """__anext__ raises StopAsyncIteration on WebSocketDisconnect."""
        ws = MagicMock()
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        adapter = StarletteWebSocketAdapter(ws)
        with self.assertRaises(StopAsyncIteration):
            asyncio.get_event_loop().run_until_complete(
                adapter.__anext__()
            )
        self.assertTrue(adapter.closed)

    def test_async_for_iteration(self) -> None:
        """Adapter works with async for loop, yielding messages until disconnect."""
        ws = MagicMock()
        ws.receive_text = AsyncMock(
            side_effect=["msg1", "msg2", WebSocketDisconnect()]
        )
        adapter = StarletteWebSocketAdapter(ws)

        async def collect() -> list:
            messages = []
            async for msg in adapter:
                messages.append(msg)
            return messages

        result = asyncio.get_event_loop().run_until_complete(collect())
        self.assertEqual(result, ["msg1", "msg2"])
        self.assertTrue(adapter.closed)


if __name__ == "__main__":
    unittest.main()
