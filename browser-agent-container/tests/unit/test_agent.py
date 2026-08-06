# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for src/agent.py — BedrockAgentCoreApp entry point.

Tests lifespan management, WebSocket handler, ping handler, entrypoint
handler, JWT extraction, user_id sanitization, and active session tracking.

Validates: Requirements 16.6
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthCheck(unittest.TestCase):
    """Tests for the ping handler."""

    def test_health_check_returns_healthy(self) -> None:
        """Ping handler always returns PingStatus.HEALTHY."""
        from agent import health_check
        from bedrock_agentcore.runtime import PingStatus

        result = health_check()
        self.assertEqual(result, PingStatus.HEALTHY)


class TestAgentInvocation(unittest.TestCase):
    """Tests for the entrypoint handler."""

    def test_entrypoint_returns_service_descriptor(self) -> None:
        """Entrypoint returns JSON with service name, version, ws url, status."""
        from agent import agent_invocation

        result = asyncio.get_event_loop().run_until_complete(
            agent_invocation(payload={}, context=None)
        )

        self.assertEqual(result["service"], "Browser Agent")
        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(result["websocket_url"], "/ws")
        self.assertEqual(result["status"], "ready")


class TestLifespan(unittest.TestCase):
    """Tests for the lifespan context manager."""

    @patch("agent.BrowserAgentFactory")
    @patch("agent.create_screenshot_storage")
    @patch("agent.create_session_store")
    @patch("agent.ConfigValidator")
    def test_lifespan_creates_factory_and_stores(
        self,
        mock_validator: MagicMock,
        mock_create_store: MagicMock,
        mock_create_screenshot: MagicMock,
        mock_factory_cls: MagicMock,
    ) -> None:
        """Lifespan validates config and creates factory + stores."""
        import agent as agent_module
        from agent import lifespan

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store
        mock_screenshot = MagicMock()
        mock_create_screenshot.return_value = mock_screenshot
        mock_factory = MagicMock()
        mock_factory_cls.return_value = mock_factory

        async def _run():
            async with lifespan(None):
                self.assertIs(agent_module._agent_factory, mock_factory)
                self.assertIs(agent_module._session_store, mock_store)
                self.assertIs(agent_module._screenshot_storage, mock_screenshot)

        asyncio.get_event_loop().run_until_complete(_run())
        mock_validator.validate_and_log.assert_called_once()
        mock_create_store.assert_called_once()
        mock_create_screenshot.assert_called_once()
        mock_factory_cls.assert_called_once()

    @patch("agent.BrowserAgentFactory")
    @patch("agent.create_screenshot_storage")
    @patch("agent.create_session_store")
    @patch("agent.ConfigValidator")
    def test_lifespan_cleanup_on_shutdown(
        self,
        mock_validator: MagicMock,
        mock_create_store: MagicMock,
        mock_create_screenshot: MagicMock,
        mock_factory_cls: MagicMock,
    ) -> None:
        """Lifespan calls factory.cleanup() on shutdown."""
        from agent import lifespan

        mock_factory = MagicMock()
        mock_factory_cls.return_value = mock_factory
        mock_create_store.return_value = MagicMock()
        mock_create_screenshot.return_value = MagicMock()

        async def _run():
            async with lifespan(None):
                pass
            # After context exits, cleanup should have been called
            mock_factory.cleanup.assert_called_once()

        asyncio.get_event_loop().run_until_complete(_run())


class TestWebsocketHandler(unittest.TestCase):
    """Tests for the websocket_handler function."""

    # Valid JWT with sub claim
    # Payload: {"sub": "user-123", "iss": "https://example.com"}
    _VALID_JWT = (
        "eyJhbGciOiJSUzI1NiJ9"
        ".eyJzdWIiOiJ1c2VyLTEyMyIsImlzcyI6Imh0dHBzOi8vZXhhbXBsZS5jb20ifQ"
        ".fake-signature"
    )

    @patch("agent.BrowserHandler")
    @patch("agent.StarletteWebSocketAdapter")
    def test_handler_creates_session(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """WebSocket handler creates adapter, handler, and delegates."""
        import agent as agent_module
        from agent import websocket_handler

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.headers = {
            "x-profile-id": "browser",
            "authorization": "Bearer %s" % self._VALID_JWT,
        }
        mock_ws.client = ("127.0.0.1", 9999)

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_handler = MagicMock()
        mock_handler.session_id = "brws_20260317_120000_abcd1234"
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        agent_module._agent_factory = MagicMock()
        agent_module._session_store = MagicMock()
        agent_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(
            websocket_handler(mock_ws, None)
        )

        mock_ws.accept.assert_awaited_once()
        mock_handler.handle_connection.assert_awaited_once()
        # Verify user_id was passed to BrowserHandler
        call_kwargs = mock_handler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get('user_id'), 'user-123')

    @patch("agent.BrowserHandler")
    @patch("agent.StarletteWebSocketAdapter")
    def test_handler_default_local_user_no_auth(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """WebSocket handler defaults user_id to 'local' when no Authorization header."""
        import agent as agent_module
        from agent import websocket_handler

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.headers = {"x-profile-id": "browser"}
        mock_ws.client = ("127.0.0.1", 9999)

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_handler = MagicMock()
        mock_handler.session_id = "brws_20260317_120000_abcd1234"
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        agent_module._agent_factory = MagicMock()
        agent_module._session_store = MagicMock()
        agent_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(
            websocket_handler(mock_ws, None)
        )

        call_kwargs = mock_handler_cls.call_args
        self.assertEqual(call_kwargs.kwargs.get('user_id'), 'local')

    def test_handler_closes_on_jwt_failure(self) -> None:
        """WebSocket is closed with 4001 when JWT has no user claims."""
        import agent as agent_module
        from agent import websocket_handler

        # JWT with no sub/oid/uid claims
        payload = base64.urlsafe_b64encode(
            json.dumps({"iss": "https://example.com"}).encode()
        ).rstrip(b'=').decode()
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b'=').decode()
        bad_jwt = "%s.%s.fake-sig" % (header, payload)

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.headers = {
            "x-profile-id": "browser",
            "authorization": "Bearer %s" % bad_jwt,
        }
        mock_ws.client = ("127.0.0.1", 9999)

        agent_module._agent_factory = MagicMock()
        agent_module._session_store = MagicMock()
        agent_module._screenshot_storage = MagicMock()

        asyncio.get_event_loop().run_until_complete(
            websocket_handler(mock_ws, None)
        )

        mock_ws.close.assert_awaited_once()
        close_args = mock_ws.close.call_args
        self.assertEqual(close_args.kwargs.get('code'), 4001)

    @patch("agent.BrowserHandler")
    @patch("agent.StarletteWebSocketAdapter")
    def test_active_sessions_tracking(
        self, mock_adapter_cls: MagicMock, mock_handler_cls: MagicMock
    ) -> None:
        """Active sessions set tracks and removes session IDs."""
        import agent as agent_module
        from agent import websocket_handler

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.headers = {
            "x-profile-id": "browser",
            "authorization": "Bearer %s" % self._VALID_JWT,
        }
        mock_ws.client = ("127.0.0.1", 9999)

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        captured_session_id = "brws_20260317_120000_abcd1234"
        mock_handler = MagicMock()
        mock_handler.session_id = captured_session_id
        mock_handler.handle_connection = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        agent_module._agent_factory = MagicMock()
        agent_module._session_store = MagicMock()
        agent_module._screenshot_storage = MagicMock()
        agent_module._active_sessions.clear()

        asyncio.get_event_loop().run_until_complete(
            websocket_handler(mock_ws, None)
        )

        # After handler completes, session should be removed from active set
        self.assertNotIn(captured_session_id, agent_module._active_sessions)


class TestExtractUserIdFromJwt(unittest.TestCase):
    """Tests for _extract_user_id_from_jwt across IdP claim formats."""

    def _make_jwt(self, payload: dict) -> str:
        """Build a fake JWT with the given payload dict."""
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b'=').decode()
        body = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        return "%s.%s.fake-sig" % (header, body)

    def test_cognito_sub_claim(self) -> None:
        """Cognito JWT: sub is a UUID."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    def test_auth0_sub_claim(self) -> None:
        """Auth0 JWT: sub is provider|id format, sanitized."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"sub": "auth0|507f1f77bcf86cd799439011"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "auth0_507f1f77bcf86cd799439011")

    def test_entra_id_oid_preferred_over_sub(self) -> None:
        """Entra ID JWT: oid takes precedence over pairwise sub."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({
            "sub": "pairwise-app-specific-id",
            "oid": "00000000-0000-0000-c000-000000000046",
        })
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "00000000-0000-0000-c000-000000000046")

    def test_okta_sub_claim(self) -> None:
        """Okta JWT: sub is email, sanitized (@ and . replaced)."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"sub": "user@example.com"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "user_example_com")

    def test_okta_uid_fallback(self) -> None:
        """Okta JWT: uid used when sub and oid are absent."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"uid": "00u1abcdef"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "00u1abcdef")

    def test_default_local_on_empty_header(self) -> None:
        """Returns 'local' when Authorization header is empty."""
        from agent import _extract_user_id_from_jwt
        result = _extract_user_id_from_jwt("")
        self.assertEqual(result, "local")

    def test_default_local_on_bearer_only(self) -> None:
        """Returns 'local' when header is 'Bearer ' with no token."""
        from agent import _extract_user_id_from_jwt
        result = _extract_user_id_from_jwt("Bearer ")
        self.assertEqual(result, "local")

    def test_raises_on_malformed_jwt(self) -> None:
        """Raises ValueError when JWT has fewer than 2 parts."""
        from agent import _extract_user_id_from_jwt
        with self.assertRaises(ValueError):
            _extract_user_id_from_jwt("Bearer not-a-jwt")

    def test_raises_on_no_user_claims(self) -> None:
        """Raises ValueError when JWT has no sub, oid, or uid."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"iss": "https://example.com", "aud": "my-app"})
        with self.assertRaises(ValueError):
            _extract_user_id_from_jwt("Bearer %s" % jwt)

    def test_sanitization_replaces_special_chars(self) -> None:
        """Sanitization replaces non-alphanumeric chars (except -, _, /) with _."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"sub": "user@domain.com#special!chars"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "user_domain_com_special_chars")

    def test_sanitization_preserves_allowed_chars(self) -> None:
        """Sanitization preserves alphanumeric, dash, underscore, slash."""
        from agent import _extract_user_id_from_jwt
        jwt = self._make_jwt({"sub": "user-123_test/path"})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, "user-123_test/path")


if __name__ == "__main__":
    unittest.main()
