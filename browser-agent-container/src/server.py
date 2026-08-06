# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Browser Agent — Starlette + Uvicorn Entry Point.

ECS / local development entry point. Provides a health check endpoint and
WebSocket endpoint without the AgentCore Runtime wrapper.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

import os
from contextlib import asynccontextmanager
from logging import Logger
from typing import AsyncIterator, Optional

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from langmesh_common.logging_helper import get_logger

from agents.browser_agent import BrowserAgentFactory
from handlers.browser_handler import BrowserHandler
from handlers.screenshot_storage import (
    ScreenshotStorageBase,
    create_screenshot_storage,
)
from handlers.session_store import SessionStoreBase, create_session_store
from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter
from utils.config_validator import ConfigValidator

logger: Logger = get_logger(__name__)

_agent_factory: Optional[BrowserAgentFactory] = None
_session_store: Optional[SessionStoreBase] = None
_screenshot_storage: Optional[ScreenshotStorageBase] = None


async def startup() -> None:
    """Startup handler: validate config and create factory + stores."""
    global _agent_factory, _session_store, _screenshot_storage  # pylint: disable=global-statement

    logger.info("Starting Browser Agent (ECS/local mode)")
    ConfigValidator.validate_and_log()

    store_type: str = os.environ.get('BA_SESSION_STORE_TYPE', 'memory')
    _session_store = create_session_store(store_type)
    _screenshot_storage = create_screenshot_storage(store_type)
    _agent_factory = BrowserAgentFactory()

    logger.info(
        "Browser Agent ready (ECS/local mode): store_type=%s",
        store_type,
    )


async def health(request) -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSON response with status and service name.
    """
    return JSONResponse({
        "status": "healthy",
        "service": "browser-agent",
    })


async def ws_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for the browser protocol.

    Reads profile from query params (``?profile=browser``), creates a
    BrowserHandler, and delegates the full session lifecycle.
    """
    await websocket.accept()
    session_id = "pending"

    try:
        profile: str = websocket.query_params.get("profile", "browser")
        adapter = StarletteWebSocketAdapter(websocket)
        handler = BrowserHandler(
            websocket=adapter,
            agent_factory=_agent_factory,
            session_store=_session_store,
            screenshot_storage=_screenshot_storage,
            profile=profile,
            user_id="local",
        )
        session_id = handler.session_id

        logger.info(
            "WebSocket connected: session=%s profile=%s",
            session_id,
            profile,
        )

        await handler.handle_connection()

    except WebSocketDisconnect:
        logger.info("Client disconnected: session=%s", session_id)
    except Exception as exc:
        logger.error(
            "WebSocket error: session=%s error=%s", session_id, str(exc)
        )
    finally:
        logger.info("WebSocket closed: session=%s", session_id)


@asynccontextmanager
async def lifespan(_app: Starlette) -> AsyncIterator[None]:
    """Starlette lifespan handler.

    Replaces the deprecated/removed ``on_startup`` argument (Starlette
    1.0+). Delegates to :func:`startup` so unit tests can still exercise
    the startup logic directly.
    """
    await startup()
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health),
        WebSocketRoute("/ws", ws_endpoint),
    ],
)

if __name__ == "__main__":
    port: int = int(os.environ.get("PORT", "8081"))
    # Binding to all interfaces (0.0.0.0) is required inside the container so
    # the fronting ALB / AgentCore Runtime can reach the service. The bind
    # address is configurable via BA_SERVER_HOST for environments that need a
    # narrower interface (e.g. local development on 127.0.0.1).
    host: str = os.environ.get("BA_SERVER_HOST", "0.0.0.0")  # nosec B104
    uvicorn.run(app, host=host, port=port)
