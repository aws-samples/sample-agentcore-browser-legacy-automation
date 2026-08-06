# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""WebSocket message type constants for the browser automation protocol."""


class BrowserMessageType:
    """Centralized WebSocket message type constants.

    Each constant value matches its attribute name exactly.
    Organized by direction: client→server, server→client (connection/session,
    orchestration, browser-specific), and error.
    """

    # Client → Server
    CONNECTION_INIT: str = "CONNECTION_INIT"
    CHAT_MESSAGE: str = "CHAT_MESSAGE"
    BROWSER_STOP: str = "BROWSER_STOP"
    BROWSER_HITL_RESPONSE: str = "BROWSER_HITL_RESPONSE"
    BROWSER_LIVE_VIEW_REQUEST: str = "BROWSER_LIVE_VIEW_REQUEST"
    NEW_SESSION: str = "NEW_SESSION"
    RESUME_SESSION: str = "RESUME_SESSION"
    GET_SESSIONS: str = "GET_SESSIONS"
    DELETE_SESSION: str = "DELETE_SESSION"

    # Server → Client: Connection & Session
    CONNECTION_ESTABLISHED: str = "CONNECTION_ESTABLISHED"
    SESSION_CREATED: str = "SESSION_CREATED"
    SESSION_RESUMED: str = "SESSION_RESUMED"
    SESSIONS_LOADED: str = "SESSIONS_LOADED"
    SESSION_DELETED: str = "SESSION_DELETED"

    # Server → Client: Orchestration Streaming
    ORCHESTRATION_START: str = "ORCHESTRATION_START"
    ORCHESTRATION_END: str = "ORCHESTRATION_END"
    REASONING: str = "REASONING"
    STREAM: str = "STREAM"
    METADATA: str = "METADATA"

    # Server → Client: Browser-Specific
    BROWSER_SESSION_STARTED: str = "BROWSER_SESSION_STARTED"
    BROWSER_ACTION_START: str = "BROWSER_ACTION_START"
    BROWSER_SCREENSHOT: str = "BROWSER_SCREENSHOT"
    BROWSER_ACTION_COMPLETE: str = "BROWSER_ACTION_COMPLETE"
    BROWSER_HITL_PROMPT: str = "BROWSER_HITL_PROMPT"
    BROWSER_LIVE_VIEW_URL: str = "BROWSER_LIVE_VIEW_URL"
    BROWSER_SESSION_ENDED: str = "BROWSER_SESSION_ENDED"
    BROWSER_HITL_TIMEOUT: str = "BROWSER_HITL_TIMEOUT"

    # Error
    ERROR: str = "ERROR"
