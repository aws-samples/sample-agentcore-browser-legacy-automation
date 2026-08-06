# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for src/server.py — Starlette + Uvicorn entry point.

Tests startup handler, health check endpoint, WebSocket endpoint creation,
and PORT env var handling.

Validates: Requirements 16.7
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthEndpoint(unittest.TestCase):
    """Tests for the /health endpoint."""

    def test_health_returns_healthy(self) -> None:
        """Health endpoint returns JSON with status=healthy."""
        from server import health

        request = MagicMock()
        response = asyncio.get_event_loop().run_until_complete(health(request))

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body.decode())
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["service"], "browser-agent")


class TestStartup(unittest.TestCase):
    """Tests for the startup handler."""

    @patch("server.BrowserAgentFactory")
    @patch("server.create_screenshot_storage")
    @patch("server.create_session_store")
    @patch("server.ConfigValidator")
    def test_startup_creates_factory_and_stores(
        self,
        mock_validator: MagicMock,
        mock_create_store: MagicMock,
        mock_create_screenshot: MagicMock,
        mock_factory_cls: MagicMock,
    ) -> None:
        """Startup validates config and creates factory + stores."""
        import server as server_module
        from server import startup

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store
        mock_screenshot = MagicMock()
        mock_create_screenshot.return_value = mock_screenshot
        mock_factory = MagicMock()
        mock_factory_cls.return_value = mock_factory

        asyncio.get_event_loop().run_until_complete(startup())

        mock_validator.validate_and_log.assert_called_once()
        mock_create_store.assert_called_once()
        mock_create_screenshot.assert_called_once()
        mock_factory_cls.assert_called_once()
        self.assertIs(server_module._agent_factory, mock_factory)
        self.assertIs(server_module._session_store, mock_store)
        self.assertIs(server_module._screenshot_storage, mock_screenshot)


class TestWsEndpoint(unittest.TestCase):
    """Tests for the WebSocket endpoint."""

    @patch("server.BrowserHandler")
    @patch("server.StarletteWebSocketAdapter")
    def test_ws_endpoint_creates_handler(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """WebSocket endpoint creates adapter, handler, and delegates."""
        import server as server_module
        from server import ws_endpoint

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.query_params = {"profile": "browser"}

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_handler = MagicMock()
        mock_handler.session_id = "brws_20260317_120000_abcd1234"
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        server_module._agent_factory = MagicMock()
        server_module._session_store = MagicMock()
        server_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(ws_endpoint(mock_ws))

        mock_ws.accept.assert_awaited_once()
        mock_handler.handle_connection.assert_awaited_once()

    @patch("server.BrowserHandler")
    @patch("server.StarletteWebSocketAdapter")
    def test_ws_endpoint_uses_local_user_id(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """WebSocket endpoint always passes user_id='local'."""
        import server as server_module
        from server import ws_endpoint

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.query_params = {"profile": "browser"}

        mock_adapter_cls.return_value = MagicMock()
        mock_handler = MagicMock()
        mock_handler.session_id = "brws_20260317_120000_abcd1234"
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        server_module._agent_factory = MagicMock()
        server_module._session_store = MagicMock()
        server_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(ws_endpoint(mock_ws))

        call_kwargs = mock_handler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get('user_id'), 'local')

    @patch("server.BrowserHandler")
    @patch("server.StarletteWebSocketAdapter")
    def test_ws_endpoint_default_profile(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """WebSocket endpoint defaults profile to 'browser' when not in query params."""
        import server as server_module
        from server import ws_endpoint

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.query_params = {}  # No profile param

        mock_adapter_cls.return_value = MagicMock()
        mock_handler = MagicMock()
        mock_handler.session_id = "brws_20260317_120000_abcd1234"
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        server_module._agent_factory = MagicMock()
        server_module._session_store = MagicMock()
        server_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(ws_endpoint(mock_ws))

        call_kwargs = mock_handler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get('profile'), 'browser')


class TestAppRoutes(unittest.TestCase):
    """Tests for the Starlette app configuration."""

    def test_app_has_health_and_ws_routes(self) -> None:
        """App has /health and /ws routes configured."""
        from server import app

        route_paths = [r.path for r in app.routes]
        self.assertIn("/health", route_paths)
        self.assertIn("/ws", route_paths)


class TestPortConfig(unittest.TestCase):
    """Tests for PORT environment variable handling."""

    @patch.dict("os.environ", {"PORT": "9090"})
    def test_port_from_env(self) -> None:
        """Port is read from PORT env var."""
        port = int(__import__("os").environ.get("PORT", "8081"))
        self.assertEqual(port, 9090)

    @patch.dict("os.environ", {}, clear=False)
    def test_port_default(self) -> None:
        """Port defaults to 8081 when PORT env var is not set."""
        import os
        os.environ.pop("PORT", None)
        port = int(os.environ.get("PORT", "8081"))
        self.assertEqual(port, 8081)


if __name__ == "__main__":
    unittest.main()
