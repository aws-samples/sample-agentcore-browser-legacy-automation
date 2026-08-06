# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Browser Agent — BedrockAgentCoreApp Entry Point.

Primary entry point when deployed to AgentCore Runtime. Provides WebSocket
handler, ping (HEALTHY), entrypoint descriptor, lifespan management with
ConfigValidator + BrowserAgentFactory + SessionStore + ScreenshotStorage.

Logging: ``utils.logging_config.configure_agentcore_logging()`` is called
after all imports to fix AgentCore Runtime's stderr capture issue.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 1.4,
           10b.1, 10b.2, 10b.3, 10b.4, 10b.5, 10b.6
"""

import base64
import json as json_module
import os
import re
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any, AsyncGenerator, Dict, Optional, Set

from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from utils.logging_helper import get_logger

from agents.browser_agent import BrowserAgentFactory
from handlers.browser_handler import BrowserHandler
from handlers.screenshot_storage import (
    ScreenshotStorageBase,
    create_screenshot_storage,
)
from handlers.session_store import SessionStoreBase, create_session_store
from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter
from utils.config_validator import ConfigValidator
from utils.logging_config import configure_agentcore_logging

# Apply AgentCore logging fix — must run after all imports so that
# utils.logging_helper's basicConfig(force=True) has already executed.
configure_agentcore_logging()

logger: Logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_active_sessions: Set[str] = set()
_agent_factory: Optional[BrowserAgentFactory] = None
_session_store: Optional[SessionStoreBase] = None
_screenshot_storage: Optional[ScreenshotStorageBase] = None


# =============================================================================
# Application Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(_app) -> AsyncGenerator:  # pylint: disable=unused-argument
    """Application lifespan context manager.

    Startup:
        1. Validate BA_ configuration via ConfigValidator
        2. Create BrowserAgentFactory, SessionStore, ScreenshotStorage

    Shutdown:
        Cleanup factory resources and log shutdown.

    Args:
        _app: BedrockAgentCoreApp instance (required by Starlette).

    Validates: Requirements 2.2
    """
    global _agent_factory, _session_store, _screenshot_storage  # pylint: disable=global-statement

    logger.info("Starting Browser Agent Runtime")

    # 1. Validate BA_ configuration
    ConfigValidator.validate_and_log()

    # 2. Create factory + stores
    store_type: str = os.environ.get('BA_SESSION_STORE_TYPE', 'memory')
    _session_store = create_session_store(store_type)
    _screenshot_storage = create_screenshot_storage(store_type)
    _agent_factory = BrowserAgentFactory()

    logger.info(
        "Browser Agent Runtime ready: store_type=%s",
        store_type,
    )
    yield

    # Shutdown
    if _agent_factory:
        _agent_factory.cleanup()

    logger.info("Shutting down Browser Agent Runtime")


# =============================================================================
# BedrockAgentCoreApp with CORS middleware
# =============================================================================

app = BedrockAgentCoreApp(
    lifespan=lifespan,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)


# =============================================================================
# WebSocket Handler
# =============================================================================


@app.websocket
async def websocket_handler(websocket, context):
    """WebSocket endpoint for the browser protocol.

    Accepts the connection, extracts JWT user_id, creates a
    BrowserHandler, and delegates the full session lifecycle.

    Validates: Requirements 2.3, 2.7, 10b.4, 10b.5, 10b.6
    """
    await websocket.accept()
    session_id = "pending"

    try:
        profile: str = websocket.headers.get("x-profile-id", "browser")
        authorization: str = websocket.headers.get("authorization", "")

        try:
            user_id: str = _extract_user_id_from_jwt(authorization)
        except ValueError as jwt_err:
            logger.error("JWT user extraction failed: %s", str(jwt_err))
            await websocket.close(code=4001, reason=str(jwt_err))
            return

        adapter = StarletteWebSocketAdapter(websocket)
        handler = BrowserHandler(
            websocket=adapter,
            agent_factory=_agent_factory,
            session_store=_session_store,
            screenshot_storage=_screenshot_storage,
            profile=profile,
            user_id=user_id,
        )
        session_id = handler.session_id
        _active_sessions.add(session_id)

        logger.info(
            "WebSocket connected: session=%s profile=%s user=%s remote=%s",
            session_id,
            profile,
            user_id,
            websocket.client,
        )

        await handler.handle_connection()

    except WebSocketDisconnect:
        logger.info("Client disconnected: session=%s", session_id)
    except Exception as exc:
        logger.error(
            "WebSocket error: session=%s error=%s", session_id, str(exc)
        )
    finally:
        _active_sessions.discard(session_id)
        logger.info("WebSocket closed: session=%s", session_id)


def _extract_user_id_from_jwt(authorization_header: str) -> str:
    """Extract user identity from a JWT Bearer token (IdP-agnostic).

    Base64-decodes the JWT payload without signature verification —
    AgentCore Runtime has already validated the token.

    Checks claims in priority order:
        1. ``oid`` — Entra ID immutable object ID (cross-app unique)
        2. ``sub`` — standard OIDC subject claim
        3. ``uid`` — Okta user ID

    If ``oid`` is present it takes precedence over ``sub`` because
    Entra ID's ``sub`` is pairwise per-app while ``oid`` is the true
    cross-application user identifier.

    When no Authorization header is present (local development), defaults
    to ``"local"``.

    Args:
        authorization_header: The ``Authorization: Bearer <JWT>`` header value.

    Returns:
        The sanitized user identity string.

    Raises:
        ValueError: If the JWT is present but malformed or contains no
            identifiable user claim.

    Validates: Requirements 10b.1, 10b.2, 10b.3, 10b.6
    """
    if not authorization_header or not authorization_header.strip():
        return "local"

    token: str = authorization_header.replace("Bearer ", "").strip()
    if not token:
        return "local"

    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError(
            "Malformed JWT (expected 3 parts, got %d)" % len(parts)
        )

    # Base64-decode the payload (second segment), adding padding as needed
    payload_b64: str = parts[1]
    padding: int = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    payload_bytes: bytes = base64.urlsafe_b64decode(payload_b64)
    payload: Dict[str, Any] = json_module.loads(payload_bytes)

    # Priority: oid (Entra ID cross-app) > sub (standard OIDC) > uid (Okta)
    oid: str = payload.get("oid", "")
    sub: str = payload.get("sub", "")
    uid: str = payload.get("uid", "")

    user_id: str = oid or sub or uid

    if not user_id:
        raise ValueError(
            "JWT payload contains no identifiable user claim "
            "(checked oid, sub, uid)"
        )

    # Sanitize for DDB/S3 key safety:
    # Replace non-alphanumeric characters (except -, _, /) with _
    user_id = re.sub(r'[^a-zA-Z0-9\-_/]', '_', user_id)

    return user_id


# =============================================================================
# Ping Handler — HEALTHY_BUSY when processing, HEALTHY when idle
# =============================================================================


@app.ping
def health_check():
    """Return HEALTHY_BUSY when active sessions exist, HEALTHY otherwise.

    AgentCore pings this endpoint to monitor instance health. Returning
    HEALTHY_BUSY tells AgentCore the instance is alive but processing a
    request — preventing it from terminating/replacing the instance during
    long-running browser automations.

    Validates: Requirement 2.4
    """
    if _active_sessions:
        return PingStatus.HEALTHY_BUSY
    return PingStatus.HEALTHY


# =============================================================================
# Entrypoint Handler — service descriptor
# =============================================================================


@app.entrypoint
async def agent_invocation(payload, context):
    """Return a JSON service descriptor for the browser agent.

    Validates: Requirement 2.5
    """
    return {
        "service": "Browser Agent",
        "version": "1.0.0",
        "websocket_url": "/ws",
        "status": "ready",
    }


if __name__ == "__main__":
    app.run()
