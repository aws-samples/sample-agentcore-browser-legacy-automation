# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Deployed WebSocket integration tests for the Browser Agent on AgentCore Runtime.

Tests WebSocket connectivity, browser protocol, session management, browser
automation, HITL, and session persistence against a real AgentCore deployment.

Authentication:
    Uses JWT Bearer token only (no SigV4). AgentCore is configured with
    JWT/OIDC authorization — the static WebSocket URL + JWT is sufficient.
    This mirrors the production NGINX → AgentCore path.

    AgentCore requires the client to send a message before it starts
    relaying frames from the container. The test sends CONNECTION_INIT
    after connecting to trigger the relay.

Configuration:
    Create tests/integration/.env.dev with:
        TEST_AGENTCORE_WS_URL=wss://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3A.../ws
        TEST_OIDC_TOKEN_ENDPOINT=https://your-provider/oauth2/{serverId}/v1/token
        TEST_OIDC_CLIENT_ID=your-m2m-client-id
        TEST_OIDC_CLIENT_SECRET=your-m2m-client-secret
        TEST_OIDC_SCOPE=agent.invoke
        TEST_OIDC_AUTH_METHOD=client_secret_post
        AWS_REGION=us-west-2

Usage:
    PYTHONPATH=src python -m pytest tests/integration/test_agent_deployed.py -v
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.integration.__setup__
# pylint: enable=import-error,unused-import

import os
import re
import json
import asyncio
import unittest
from typing import List, Dict, Any
from pathlib import Path
from logging import Logger

import websockets
import requests
from dotenv import load_dotenv

from utils.logging_helper import get_logger

from models.websocket_message_types import BrowserMessageType

# Load integration test .env — prefer .env.dev (gitignored, real values) over .env (template)
_integration_dir = Path(__file__).resolve().parent
_integration_env_dev = _integration_dir / ".env.dev"
_integration_env = _integration_dir / ".env"
if _integration_env_dev.exists():
    load_dotenv(_integration_env_dev, override=True)
elif _integration_env.exists():
    load_dotenv(_integration_env, override=True)

logger: Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WS_URL: str = os.environ.get("TEST_AGENTCORE_WS_URL", "")
AWS_REGION: str = os.environ.get("AWS_REGION", "us-west-2")

SESSION_ID_PATTERN = re.compile(r"^brws_\d{8}_\d{6}_[0-9a-f]{8}$")
WS_URL_PATTERN = re.compile(r"^wss?://.+/ws$")

CONNECTION_TIMEOUT = 60.0
MESSAGE_TIMEOUT = 120.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_deployed() -> bool:
    """Return True when a deployment URL is configured."""
    return bool(WS_URL)


def get_m2m_token() -> str:
    """Obtain a JWT from the configured OIDC provider using M2M client_credentials grant."""
    token_endpoint: str = os.environ.get("TEST_OIDC_TOKEN_ENDPOINT", "")
    client_id: str = os.environ.get("TEST_OIDC_CLIENT_ID", "")
    client_secret: str = os.environ.get("TEST_OIDC_CLIENT_SECRET", "")
    audience: str = os.environ.get("TEST_OIDC_AUDIENCE", "")
    scope: str = os.environ.get("TEST_OIDC_SCOPE", "")
    auth_method: str = os.environ.get("TEST_OIDC_AUTH_METHOD", "client_secret_post")

    if not all([token_endpoint, client_id, client_secret]):
        raise EnvironmentError(
            "OIDC M2M credentials not fully configured. "
            "Set TEST_OIDC_TOKEN_ENDPOINT, TEST_OIDC_CLIENT_ID, "
            "and TEST_OIDC_CLIENT_SECRET."
        )

    import base64

    if auth_method == "client_secret_basic":
        credentials = "%s:%s" % (client_id, client_secret)
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic %s" % encoded,
        }
        data = {"grant_type": "client_credentials"}
        if scope:
            data["scope"] = scope
        if audience:
            data["audience"] = audience
        response = requests.post(token_endpoint, headers=headers, data=data, timeout=30)
    else:
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:
            data["scope"] = scope
        if audience:
            data["audience"] = audience
        response = requests.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

    response.raise_for_status()
    return response.json()["access_token"]


async def _connect_ws(jwt_token: str) -> "websockets.WebSocketClientProtocol":
    """Open a JWT-authenticated WebSocket connection to AgentCore.

    Uses the static WebSocket URL with JWT Bearer header — no SigV4,
    no presigned URL. This mirrors the production NGINX → AgentCore path.

    Sends CONNECTION_INIT after connecting to trigger AgentCore's frame
    relay (AgentCore only relays container frames after the client sends
    the first message).
    """
    headers = {"Authorization": "Bearer %s" % jwt_token}
    ws = await asyncio.wait_for(
        websockets.connect(WS_URL, additional_headers=headers, open_timeout=CONNECTION_TIMEOUT,
                           ping_interval=None),
        timeout=CONNECTION_TIMEOUT,
    )
    await ws.send(json.dumps({"type": BrowserMessageType.CONNECTION_INIT}))
    return ws


async def _recv_json(ws, timeout: float = MESSAGE_TIMEOUT) -> Dict[str, Any]:
    """Receive and parse a single JSON frame."""
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def _recv_type(ws, msg_type: str, timeout: float = MESSAGE_TIMEOUT) -> Dict[str, Any]:
    """Receive frames until one with the given type is found."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        msg = await _recv_json(ws, timeout=remaining)
        if msg.get("type") == msg_type:
            return msg
    raise TimeoutError("Did not receive '%s' within %ds" % (msg_type, timeout))


async def _collect_frames_until(ws, stop_type: str, timeout: float = 180.0) -> List[Dict[str, Any]]:
    """Collect frames until a frame with the given type is received (inclusive)."""
    frames: List[Dict[str, Any]] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        frame = await _recv_json(ws, timeout=remaining)
        frames.append(frame)
        if frame.get("type") == stop_type:
            break
    return frames


# ---------------------------------------------------------------------------
# TestDeployedConfiguration — always runs
# ---------------------------------------------------------------------------

class TestDeployedConfiguration(unittest.TestCase):
    """Validate deployment configuration variables."""

    def test_ws_url_format(self) -> None:
        """Verify TEST_AGENTCORE_WS_URL matches wss?://.+/ws pattern."""
        if not WS_URL:
            self.skipTest("TEST_AGENTCORE_WS_URL not set")
        self.assertRegex(WS_URL, WS_URL_PATTERN)

    def test_aws_region_is_set(self) -> None:
        """Verify AWS_REGION matches region code pattern."""
        region = os.environ.get("AWS_REGION", "")
        self.assertTrue(bool(region), "AWS_REGION must be set")
        self.assertRegex(region, r"^[a-z]{2}-[a-z]+-\d+$")


# ---------------------------------------------------------------------------
# TestDeployedConnectivity — requires deployment
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedConnectivity(unittest.TestCase):
    """Verify WebSocket connectivity to the deployed browser agent."""

    def test_websocket_connection(self) -> None:
        """Connect with JWT, send CONNECTION_INIT, verify CONNECTION_ESTABLISHED."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                msg = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                self.assertEqual(msg["type"], BrowserMessageType.CONNECTION_ESTABLISHED)
                logger.info("Connected: session=%s", msg.get("session_id"))
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# TestDeployedBrowserProtocol — requires deployment
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedBrowserProtocol(unittest.TestCase):
    """Verify browser-specific WebSocket protocol against deployed agent."""

    def test_connection_established_fields(self) -> None:
        """Verify CONNECTION_ESTABLISHED contains session_id and profile."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                msg = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                self.assertIn("session_id", msg)
                self.assertIn("profile", msg)
                self.assertRegex(msg["session_id"], SESSION_ID_PATTERN)
                logger.info(
                    "CONNECTION_ESTABLISHED: session=%s profile=%s",
                    msg["session_id"], msg["profile"],
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_chat_message_produces_browser_frames(self) -> None:
        """Send Wikipedia instruction, verify ORCHESTRATION_START → browser frames → ORCHESTRATION_END."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_id = established["session_id"]

                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Navigate to https://en.wikipedia.org. "
                        "Type 'Amazon Company' in the search field. "
                        "Hit the 'Search' button."
                    ),
                    "session_id": session_id,
                }))

                frames = await _collect_frames_until(ws, BrowserMessageType.ORCHESTRATION_END)
                ftypes = [f.get("type") for f in frames]

                logger.info("Browser frame types: %s", ftypes)

                # BROWSER_SESSION_STARTED should appear before orchestration
                started = [f for f in frames if f.get("type") == BrowserMessageType.BROWSER_SESSION_STARTED]
                self.assertGreaterEqual(
                    len(started), 1,
                    "Expected BROWSER_SESSION_STARTED, got types: %s" % ftypes,
                )
                self.assertIn("liveViewUrl", started[0])

                # ORCHESTRATION_START should be present
                self.assertIn(BrowserMessageType.ORCHESTRATION_START, ftypes)

                # At least one BROWSER_SCREENSHOT with screenshotUrl
                screenshots = [f for f in frames if f.get("type") == BrowserMessageType.BROWSER_SCREENSHOT]
                self.assertGreaterEqual(
                    len(screenshots), 1,
                    "Expected at least one BROWSER_SCREENSHOT, got types: %s" % ftypes,
                )
                self.assertTrue(
                    screenshots[0].get("screenshotUrl"),
                    "BROWSER_SCREENSHOT should contain non-empty screenshotUrl",
                )

                # METADATA with usage/latency/model
                metadata = [f for f in frames if f.get("type") == BrowserMessageType.METADATA]
                self.assertGreaterEqual(len(metadata), 1, "Expected METADATA frame")

                # ORCHESTRATION_END should be last
                self.assertEqual(ftypes[-1], BrowserMessageType.ORCHESTRATION_END)

                logger.info(
                    "Browser automation: %d frames, screenshots=%d",
                    len(frames), len(screenshots),
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_graceful_disconnect(self) -> None:
        """Connect, receive CONNECTION_ESTABLISHED, then close cleanly."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
            finally:
                await ws.close()
            logger.info("Graceful disconnect completed")

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# TestDeployedSessionManagement — requires deployment
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedSessionManagement(unittest.TestCase):
    """Verify session management operations against deployed agent."""

    def test_multiple_sessions_get_distinct_ids(self) -> None:
        """Two concurrent connections receive distinct session IDs."""

        async def _run() -> None:
            token = get_m2m_token()
            ws1 = await _connect_ws(token)
            ws2 = await _connect_ws(token)
            try:
                msg1 = await _recv_type(ws1, BrowserMessageType.CONNECTION_ESTABLISHED)
                msg2 = await _recv_type(ws2, BrowserMessageType.CONNECTION_ESTABLISHED)
                self.assertNotEqual(msg1["session_id"], msg2["session_id"])
                logger.info("Sessions: %s, %s", msg1["session_id"], msg2["session_id"])
            finally:
                await ws1.close()
                await ws2.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_session_id_format(self) -> None:
        """Session ID matches brws_YYYYMMDD_HHMMSS_hex8 format."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                msg = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                self.assertRegex(msg["session_id"], SESSION_ID_PATTERN)
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_new_session_creates_distinct_session(self) -> None:
        """Send NEW_SESSION and verify SESSION_CREATED with a distinct session_id."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                initial_session_id = established["session_id"]

                await ws.send(json.dumps({"type": BrowserMessageType.NEW_SESSION}))
                created = await _recv_type(ws, BrowserMessageType.SESSION_CREATED)

                self.assertEqual(created["type"], BrowserMessageType.SESSION_CREATED)
                self.assertIn("session_id", created)
                self.assertRegex(created["session_id"], SESSION_ID_PATTERN)
                self.assertNotEqual(
                    created["session_id"], initial_session_id,
                    "NEW_SESSION must produce a session_id different from the initial one",
                )
                logger.info(
                    "NEW_SESSION: initial=%s new=%s",
                    initial_session_id, created["session_id"],
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_get_sessions_returns_sessions_loaded(self) -> None:
        """Send GET_SESSIONS and verify SESSIONS_LOADED response with sessions array."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)

                await ws.send(json.dumps({"type": BrowserMessageType.GET_SESSIONS}))
                loaded = await _recv_type(ws, BrowserMessageType.SESSIONS_LOADED)

                self.assertEqual(loaded["type"], BrowserMessageType.SESSIONS_LOADED)
                self.assertIn("sessions", loaded)
                self.assertIsInstance(loaded["sessions"], list)
                logger.info("GET_SESSIONS: %d sessions returned", len(loaded["sessions"]))
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# TestDeployedBrowserAutomation — requires deployment
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedBrowserAutomation(unittest.TestCase):
    """Verify browser automation end-to-end against deployed agent.

    Each test sends a CHAT_MESSAGE with a browser instruction and verifies
    the full frame sequence: BROWSER_SESSION_STARTED, ORCHESTRATION_START,
    browser action frames, BROWSER_SCREENSHOT, METADATA, ORCHESTRATION_END.
    """

    def _assert_browser_frame_sequence(
        self, frames: List[Dict[str, Any]], context: str
    ) -> None:
        """Verify the standard browser automation frame sequence."""
        ftypes = [f.get("type") for f in frames]
        logger.info("Frame sequence for %s: %s", context, ftypes)

        # BROWSER_SESSION_STARTED
        started = [f for f in frames if f.get("type") == BrowserMessageType.BROWSER_SESSION_STARTED]
        self.assertGreaterEqual(
            len(started), 1,
            "Expected BROWSER_SESSION_STARTED for %s" % context,
        )
        self.assertIn("liveViewUrl", started[0])

        # ORCHESTRATION_START
        self.assertIn(
            BrowserMessageType.ORCHESTRATION_START, ftypes,
            "Expected ORCHESTRATION_START for %s" % context,
        )

        # At least one BROWSER_SCREENSHOT with screenshotUrl
        screenshots = [f for f in frames if f.get("type") == BrowserMessageType.BROWSER_SCREENSHOT]
        self.assertGreaterEqual(
            len(screenshots), 1,
            "Expected at least one BROWSER_SCREENSHOT for %s" % context,
        )
        self.assertTrue(
            screenshots[0].get("screenshotUrl"),
            "BROWSER_SCREENSHOT should contain non-empty screenshotUrl",
        )

        # METADATA
        metadata = [f for f in frames if f.get("type") == BrowserMessageType.METADATA]
        self.assertGreaterEqual(len(metadata), 1, "Expected METADATA for %s" % context)

        # ORCHESTRATION_END should be last
        self.assertEqual(
            ftypes[-1], BrowserMessageType.ORCHESTRATION_END,
            "Last frame should be ORCHESTRATION_END for %s" % context,
        )

    def test_wikipedia_search(self) -> None:
        """Full Wikipedia instruction via WebSocket — verify frame sequence."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_id = established["session_id"]

                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Navigate to https://en.wikipedia.org. "
                        "Type 'Amazon Company' in the search field. "
                        "Hit the 'Search' button. "
                        "Click on AMZN."
                    ),
                    "session_id": session_id,
                }))

                frames = await _collect_frames_until(ws, BrowserMessageType.ORCHESTRATION_END)
                self._assert_browser_frame_sequence(frames, "Wikipedia search")
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_form_fill(self) -> None:
        """Full httpbin form fill via WebSocket — verify frame sequence."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_id = established["session_id"]

                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Go to https://httpbin.org/forms/post. "
                        "Enter 'Visual Worker' as customer name. "
                        "Enter '555-555-5555' as phone number. "
                        "Enter 'visual-worker@example.com' as email. "
                        "Select 'Small' size Pizza. "
                        "Check 'Mushroom' as topping. "
                        "Enter 'Deliver to my front door.' as delivery instructions. "
                        "Click Submit."
                    ),
                    "session_id": session_id,
                }))

                frames = await _collect_frames_until(ws, BrowserMessageType.ORCHESTRATION_END)
                self._assert_browser_frame_sequence(frames, "form fill")
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_browser_stop(self) -> None:
        """Start automation, send BROWSER_STOP, verify BROWSER_SESSION_ENDED."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_id = established["session_id"]

                # Start a long-running automation
                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Navigate to https://en.wikipedia.org. "
                        "Type 'Amazon Company' in the search field. "
                        "Hit the 'Search' button. "
                        "Click on AMZN."
                    ),
                    "session_id": session_id,
                }))

                # Wait for BROWSER_SESSION_STARTED to confirm browser is active
                await _recv_type(ws, BrowserMessageType.BROWSER_SESSION_STARTED, timeout=60.0)

                # Send BROWSER_STOP
                await ws.send(json.dumps({"type": BrowserMessageType.BROWSER_STOP}))

                # Collect remaining frames — expect BROWSER_SESSION_ENDED
                frames = await _collect_frames_until(
                    ws, BrowserMessageType.BROWSER_SESSION_ENDED, timeout=60.0
                )
                ended = [f for f in frames if f.get("type") == BrowserMessageType.BROWSER_SESSION_ENDED]
                self.assertGreaterEqual(len(ended), 1, "Expected BROWSER_SESSION_ENDED")
                self.assertEqual(ended[0]["reason"], "stopped")
                logger.info("BROWSER_STOP: session ended with reason=%s", ended[0]["reason"])
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# TestDeployedHITL — requires deployment
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedHITL(unittest.TestCase):
    """Verify HITL prompt/response round-trip against deployed agent.

    Gap Canada navigation is known to trigger handoff_to_user when the agent
    encounters ambiguity (e.g., multiple 'Straight Jeans' options).
    """

    def test_gap_navigation_hitl_over_websocket(self) -> None:
        """Full HITL round-trip: prompt → canned 'stop' response → orchestration end."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_id = established["session_id"]

                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Navigate to https://www.gapcanada.ca. "
                        "Dismiss any popups that appear. "
                        "Click on Men. "
                        "Click on Jeans. "
                        "Click on 'Straight'. "
                        "Click on 'Straight Jeans' (best seller)."
                    ),
                    "session_id": session_id,
                }))

                # Collect frames, watching for HITL prompt or orchestration end
                frames: List[Dict[str, Any]] = []
                deadline = asyncio.get_event_loop().time() + 180.0
                hitl_responded = False

                while asyncio.get_event_loop().time() < deadline:
                    remaining = deadline - asyncio.get_event_loop().time()
                    try:
                        frame = await _recv_json(ws, timeout=remaining)
                    except (asyncio.TimeoutError, TimeoutError):
                        break
                    frames.append(frame)

                    # If we get a HITL prompt, respond with "stop"
                    if frame.get("type") == BrowserMessageType.BROWSER_HITL_PROMPT and not hitl_responded:
                        prompt_id = frame.get("promptId", "")
                        self.assertIn("question", frame)
                        self.assertIn("screenshotBase64", frame)
                        logger.info(
                            "HITL prompt received: promptId=%s question=%s",
                            prompt_id, str(frame.get("question", ""))[:100],
                        )

                        await ws.send(json.dumps({
                            "type": BrowserMessageType.BROWSER_HITL_RESPONSE,
                            "promptId": prompt_id,
                            "action": "stop",
                            "value": "",
                        }))
                        hitl_responded = True

                    # Stop collecting once we see ORCHESTRATION_END
                    if frame.get("type") == BrowserMessageType.ORCHESTRATION_END:
                        break

                ftypes = [f.get("type") for f in frames]
                logger.info(
                    "HITL test: %d frames, hitl_responded=%s, types=%s",
                    len(frames), hitl_responded, ftypes,
                )

                # Orchestration should complete regardless of HITL
                self.assertIn(
                    BrowserMessageType.ORCHESTRATION_END, ftypes,
                    "Expected ORCHESTRATION_END after HITL round-trip",
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# TestDeployedSessionPersistence — requires deployment with session store
# ---------------------------------------------------------------------------

@unittest.skipUnless(is_deployed(), "Set TEST_AGENTCORE_WS_URL to run deployed tests")
class TestDeployedSessionPersistence(unittest.TestCase):
    """Verify session persistence operations against deployed agent.

    Tests resume session with conversation history and GET_SESSIONS listing.
    These tests exercise the deployed SessionStore (DynamoDB) through the
    WebSocket protocol.
    """

    def test_resume_session_returns_history(self) -> None:
        """Chat in session A, NEW_SESSION to B, RESUME_SESSION to A — verify history."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                established = await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)
                session_a = established["session_id"]

                # Send a message in session A so it has conversation history
                await ws.send(json.dumps({
                    "type": BrowserMessageType.CHAT_MESSAGE,
                    "content": (
                        "Navigate to https://en.wikipedia.org. "
                        "Type 'Amazon Company' in the search field. "
                        "Hit the 'Search' button."
                    ),
                    "session_id": session_a,
                }))
                await _collect_frames_until(ws, BrowserMessageType.ORCHESTRATION_END)

                # Create session B
                await ws.send(json.dumps({"type": BrowserMessageType.NEW_SESSION}))
                created = await _recv_type(ws, BrowserMessageType.SESSION_CREATED)
                session_b = created["session_id"]
                self.assertNotEqual(session_a, session_b)

                # Resume session A
                await ws.send(json.dumps({
                    "type": BrowserMessageType.RESUME_SESSION,
                    "session_id": session_a,
                }))
                resumed = await _recv_type(ws, BrowserMessageType.SESSION_RESUMED, timeout=60.0)

                self.assertEqual(resumed["type"], BrowserMessageType.SESSION_RESUMED)
                self.assertIn("conversation_history", resumed)
                self.assertIsInstance(resumed["conversation_history"], list)
                self.assertGreaterEqual(
                    len(resumed["conversation_history"]), 1,
                    "Expected at least one conversation turn after chatting in session A",
                )
                logger.info(
                    "RESUME_SESSION: session_a=%s history_len=%d",
                    session_a, len(resumed["conversation_history"]),
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_get_sessions_returns_sessions_loaded(self) -> None:
        """Send GET_SESSIONS and verify SESSIONS_LOADED with sessions array."""

        async def _run() -> None:
            token = get_m2m_token()
            ws = await _connect_ws(token)
            try:
                await _recv_type(ws, BrowserMessageType.CONNECTION_ESTABLISHED)

                await ws.send(json.dumps({"type": BrowserMessageType.GET_SESSIONS}))
                loaded = await _recv_type(ws, BrowserMessageType.SESSIONS_LOADED)

                self.assertEqual(loaded["type"], BrowserMessageType.SESSIONS_LOADED)
                self.assertIn("sessions", loaded)
                self.assertIsInstance(loaded["sessions"], list)
                logger.info(
                    "GET_SESSIONS: %d sessions returned", len(loaded["sessions"])
                )
            finally:
                await ws.close()

        asyncio.get_event_loop().run_until_complete(_run())


if __name__ == "__main__":
    unittest.main()
