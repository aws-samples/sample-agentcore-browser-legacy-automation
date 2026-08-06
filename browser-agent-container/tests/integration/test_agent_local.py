# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Local WebSocket protocol integration tests for the browser agent.

Tests the full BrowserHandler + BrowserStreamer pipeline using a StubWebSocket
that captures all outgoing frames. Uses real BrowserAgentFactory, real SessionStore,
and real ScreenshotStorage — no mocking.

Requires: AWS credentials, Bedrock model access, AgentCore Browser permissions.

Run: PYTHONPATH=src python -m pytest tests/integration/test_agent_local.py -v
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.integration.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import json
import os
import unittest
from logging import Logger
from typing import List, Optional, Tuple
from uuid import uuid4

from utils.logging_helper import get_logger

from agents.browser_agent import BrowserAgentFactory
from handlers.browser_handler import BrowserHandler
from handlers.session_store import (
    SessionRecord,
    SessionStoreBase,
    create_session_store,
)
from handlers.screenshot_storage import (
    ScreenshotStorageBase,
    create_screenshot_storage,
)
from models.websocket_message_types import BrowserMessageType


# ---------------------------------------------------------------------------
# StubWebSocket — captures all outgoing frames
# ---------------------------------------------------------------------------

class StubWebSocket:
    """In-process WebSocket stub that captures all sent frames.

    Implements the interface expected by BrowserHandler:
    send_json(), send(), closed, remote_address, close(), __aiter__/__anext__.

    All frames sent via send_json() or send() are appended to ``messages``.
    """

    def __init__(self) -> None:
        self.messages: List[dict] = []
        self._closed: bool = False
        self._incoming: asyncio.Queue = asyncio.Queue()

    @property
    def remote_address(self) -> Optional[Tuple[str, int]]:
        return ("127.0.0.1", 9999)

    @property
    def closed(self) -> bool:
        return self._closed

    async def send(self, data: str) -> None:
        """Capture a raw text message."""
        if self._closed:
            return
        try:
            parsed = json.loads(data)
            self.messages.append(parsed)
        except json.JSONDecodeError:
            self.messages.append({"_raw": data})

    async def send_json(self, data: dict) -> None:
        """Capture a JSON frame."""
        if self._closed:
            return
        self.messages.append(data)

    async def recv(self) -> str:
        """Return the next queued incoming message."""
        return await self._incoming.get()

    async def close(self, code: int = 1000) -> None:  # noqa: ARG002
        """Mark the socket as closed."""
        self._closed = True

    def inject(self, payload: dict) -> None:
        """Queue a message to be received by the handler."""
        self._incoming.put_nowait(json.dumps(payload))

    def inject_disconnect(self) -> None:
        """Signal end of iteration (WebSocket disconnect)."""
        self._incoming.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        msg = await self._incoming.get()
        if msg is None:
            raise StopAsyncIteration
        return msg


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def frames_of_type(messages: List[dict], frame_type: str) -> List[dict]:
    """Filter captured messages by frame type."""
    return [m for m in messages if m.get("type") == frame_type]


def frame_types(messages: List[dict]) -> List[str]:
    """Extract ordered list of frame types from captured messages."""
    return [m.get("type", "") for m in messages]


def _make_handler(
    user_id: str = "local",
    store_type: str = "memory",
    ws: Optional[StubWebSocket] = None,
    factory: Optional[BrowserAgentFactory] = None,
) -> Tuple[StubWebSocket, BrowserHandler, BrowserAgentFactory, SessionStoreBase, ScreenshotStorageBase]:
    """Create a BrowserHandler wired to a StubWebSocket with real dependencies.

    Returns:
        Tuple of (stub_ws, handler, factory, session_store, screenshot_storage).
    """
    stub_ws = ws or StubWebSocket()
    agent_factory = factory or BrowserAgentFactory()
    session_store: SessionStoreBase = create_session_store(store_type)
    screenshot_storage: ScreenshotStorageBase = create_screenshot_storage(store_type)

    handler = BrowserHandler(
        websocket=stub_ws,
        agent_factory=agent_factory,
        session_store=session_store,
        screenshot_storage=screenshot_storage,
        profile="browser",
        user_id=user_id,
    )
    return stub_ws, handler, agent_factory, session_store, screenshot_storage


SESSION_ID_PATTERN: str = r"^brws_\d{8}_\d{6}_[0-9a-f]{8}$"



# ===========================================================================
# TestLocalBrowserProtocol — connection, session management, protocol basics
# ===========================================================================

class TestLocalBrowserProtocol(unittest.TestCase):
    """Protocol-level tests: CONNECTION_ESTABLISHED, session CRUD, ID format.

    These tests exercise BrowserHandler methods directly (no real browser
    automation) to validate the WebSocket protocol layer.

    Validates: Requirements 18.2, 18.5
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalBrowserProtocol")

    def setUp(self) -> None:
        self.user_id: str = "integration-test-%s" % uuid4().hex[:8]
        self.ws, self.handler, self.factory, self.store, self.storage = _make_handler(
            user_id=self.user_id
        )

    def test_connection_established_fields(self) -> None:
        """CONNECTION_ESTABLISHED contains session_id and profile."""
        asyncio.get_event_loop().run_until_complete(
            self.handler._send_connection_established()
        )
        established = frames_of_type(
            self.ws.messages, BrowserMessageType.CONNECTION_ESTABLISHED
        )
        self.assertEqual(len(established), 1)
        frame = established[0]
        self.assertIn("session_id", frame)
        self.assertIn("profile", frame)
        self.assertEqual(frame["profile"], "browser")
        self.logger.info(
            "CONNECTION_ESTABLISHED: session_id=%s profile=%s",
            frame["session_id"], frame["profile"],
        )

    def test_session_id_format(self) -> None:
        """Session ID matches brws_YYYYMMDD_HHMMSS_hex8."""
        session_id = self.handler.session_id
        self.assertRegex(session_id, SESSION_ID_PATTERN)
        self.logger.info("Session ID format valid: %s", session_id)

    def test_new_session_creates_distinct_id(self) -> None:
        """NEW_SESSION produces SESSION_CREATED with a new distinct session_id."""
        original_id = self.handler.session_id
        asyncio.get_event_loop().run_until_complete(
            self.handler._handle_new_session({})
        )
        created = frames_of_type(
            self.ws.messages, BrowserMessageType.SESSION_CREATED
        )
        self.assertEqual(len(created), 1)
        new_id = created[0]["session_id"]
        self.assertNotEqual(original_id, new_id)
        self.assertRegex(new_id, SESSION_ID_PATTERN)
        self.logger.info(
            "New session: original=%s new=%s", original_id, new_id
        )

    def test_get_sessions_returns_sessions_loaded(self) -> None:
        """GET_SESSIONS responds with SESSIONS_LOADED containing sessions array."""
        asyncio.get_event_loop().run_until_complete(
            self.handler._handle_get_sessions({})
        )
        loaded = frames_of_type(
            self.ws.messages, BrowserMessageType.SESSIONS_LOADED
        )
        self.assertEqual(len(loaded), 1)
        self.assertIn("sessions", loaded[0])
        self.assertIsInstance(loaded[0]["sessions"], list)
        self.logger.info(
            "SESSIONS_LOADED: count=%d", len(loaded[0]["sessions"])
        )

    def test_get_sessions_payload_includes_profile_and_mode(self) -> None:
        """Every session in SESSIONS_LOADED carries ``profile`` and ``mode``.

        The frontend ``SessionList`` component keys its icon and resume-click
        routing off ``session.profile``, with ``mode`` as a fallback. Without
        these fields browser sessions fall through to the voice branch and
        render the microphone icon (Issue 1 of
        ``.kiro/research/temp-browser-ui-issues-analysis.md``).
        """
        # Seed two sessions so we are not asserting on an empty list
        loop = asyncio.get_event_loop()
        for suffix in ("aaaa1111", "bbbb2222"):
            record = SessionRecord(
                user_id=self.user_id,
                session_id="brws_20250101_000000_%s" % suffix,
                conversation_history=[{"role": "user", "content": "hello"}],
            )
            loop.run_until_complete(self.store.create(self.user_id, record))

        loop.run_until_complete(self.handler._handle_get_sessions({}))

        loaded = frames_of_type(
            self.ws.messages, BrowserMessageType.SESSIONS_LOADED
        )
        self.assertEqual(len(loaded), 1)
        sessions = loaded[0]["sessions"]
        self.assertGreaterEqual(len(sessions), 2)
        for session in sessions:
            self.assertIn("profile", session)
            self.assertIn("mode", session)
            self.assertEqual(session["profile"], "browser")
            self.assertEqual(session["mode"], "text")
        self.logger.info(
            "SESSIONS_LOADED payload shape verified: profile + mode present on all %d entries",
            len(sessions),
        )

    def test_delete_session(self) -> None:
        """Create a session, delete it, verify SESSION_DELETED."""
        loop = asyncio.get_event_loop()

        # Create a session record in the store
        record = SessionRecord(
            user_id=self.user_id,
            session_id="brws_20250101_120000_aabbccdd",
        )
        loop.run_until_complete(
            self.store.create(self.user_id, record)
        )

        # Delete it
        loop.run_until_complete(
            self.handler._handle_delete_session({
                "session_id": "brws_20250101_120000_aabbccdd"
            })
        )
        deleted = frames_of_type(
            self.ws.messages, BrowserMessageType.SESSION_DELETED
        )
        self.assertEqual(len(deleted), 1)
        self.assertEqual(
            deleted[0]["session_id"], "brws_20250101_120000_aabbccdd"
        )

        # Verify it's gone from the store
        result = loop.run_until_complete(
            self.store.get(self.user_id, "brws_20250101_120000_aabbccdd")
        )
        self.assertIsNone(result)
        self.logger.info("Session deleted and verified absent from store")



# ===========================================================================
# TestLocalBrowserAutomation — full agent automation through BrowserHandler
# ===========================================================================

class TestLocalBrowserAutomation(unittest.TestCase):
    """End-to-end browser automation tests through the BrowserHandler pipeline.

    Each test sends a CHAT_MESSAGE through the handler, which creates a real
    browser session, runs the Strands Agent, and streams frames via
    BrowserStreamer. Verifies the full frame sequence.

    Validates: Requirements 18.2, 18.4
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalBrowserAutomation")
    factory: BrowserAgentFactory = None

    @classmethod
    def setUpClass(cls) -> None:
        """Create shared BrowserAgentFactory for all automation tests."""
        cls.factory = BrowserAgentFactory()

    def _run_chat(self, instruction: str) -> Tuple[StubWebSocket, BrowserHandler]:
        """Send a CHAT_MESSAGE through a fresh handler and return captured frames.

        Creates a new handler per test to isolate browser sessions.
        """
        user_id = "integration-test-%s" % uuid4().hex[:8]
        ws, handler, _factory, _store, _storage = _make_handler(
            user_id=user_id, factory=self.__class__.factory
        )

        async def _execute() -> None:
            # Send CONNECTION_ESTABLISHED first
            await handler._send_connection_established()
            # Process CHAT_MESSAGE
            await handler._handle_chat_message({"content": instruction})

        asyncio.get_event_loop().run_until_complete(_execute())
        return ws, handler

    def _assert_frame_sequence(self, ws: StubWebSocket, context: str) -> None:
        """Verify the standard browser automation frame sequence.

        Expected: CONNECTION_ESTABLISHED, BROWSER_SESSION_STARTED (with liveViewUrl),
        ORCHESTRATION_START, ... browser frames ..., METADATA, ORCHESTRATION_END.
        At least one BROWSER_SCREENSHOT with a non-empty screenshotPath.

        Protocol note (v0.13.0): BROWSER_SCREENSHOT no longer carries inline
        base64 image bytes. The payload was changed to pre-signed S3 URLs to
        respect AgentCore's 32KB WebSocket frame limit. See:
          .kiro/specs/86-browser-agent-container-deployment/tasks.md (L485)
        The current shape is:
          { screenshotPath, screenshotUrl, timestamp, title, stepNumber }
        In memory-mode (local dev), ``screenshotUrl`` is empty and
        ``screenshotPath`` is a local filesystem path; in dynamodb/s3 mode,
        ``screenshotPath`` is an ``s3://`` URI and ``screenshotUrl`` is a
        pre-signed HTTPS GET URL.
        """
        types = frame_types(ws.messages)
        self.logger.info("Frame sequence for %s: %s", context, types)

        # CONNECTION_ESTABLISHED should be first
        self.assertEqual(
            types[0], BrowserMessageType.CONNECTION_ESTABLISHED,
            "First frame should be CONNECTION_ESTABLISHED",
        )

        # BROWSER_SESSION_STARTED
        started = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_SESSION_STARTED
        )
        self.assertGreaterEqual(
            len(started), 1,
            "Expected BROWSER_SESSION_STARTED frame",
        )
        self.assertIn("liveViewUrl", started[0])

        # ORCHESTRATION_START
        orch_start = frames_of_type(
            ws.messages, BrowserMessageType.ORCHESTRATION_START
        )
        self.assertGreaterEqual(
            len(orch_start), 1,
            "Expected ORCHESTRATION_START frame",
        )

        # Either a BROWSER_SCREENSHOT with a non-empty screenshotPath
        # (the agent successfully reached a page and captured it) OR a
        # BROWSER_HITL_PROMPT (the agent hit a site that resisted automation
        # — e.g. Gap Canada's HTTP/2 blocking — and correctly asked the
        # user what to do). Both are valid terminal states and both prove
        # the pipeline is working end-to-end.
        #
        # The frame no longer carries base64 bytes — see the docstring above.
        screenshots = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_SCREENSHOT
        )
        hitl_prompts = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_HITL_PROMPT
        )
        self.assertTrue(
            len(screenshots) >= 1 or len(hitl_prompts) >= 1,
            "Expected at least one BROWSER_SCREENSHOT or "
            "BROWSER_HITL_PROMPT frame for %s "
            "(got %d screenshots, %d HITL prompts)"
            % (context, len(screenshots), len(hitl_prompts)),
        )
        if len(screenshots) >= 1:
            first_shot = screenshots[0]
            self.assertIn(
                "screenshotPath", first_shot,
                "BROWSER_SCREENSHOT must carry a screenshotPath "
                "(v0.13.0 contract)",
            )
            self.assertTrue(
                first_shot.get("screenshotPath"),
                "BROWSER_SCREENSHOT should contain a non-empty screenshotPath",
            )
            self.assertIn(
                "screenshotUrl", first_shot,
                "BROWSER_SCREENSHOT must carry a screenshotUrl field "
                "(may be empty for memory-mode, non-empty for s3/dynamodb mode)",
            )
        if len(hitl_prompts) >= 1:
            # A HITL prompt must carry a promptId the handler can correlate
            # a BROWSER_HITL_RESPONSE back to.
            self.assertIn(
                "promptId", hitl_prompts[0],
                "BROWSER_HITL_PROMPT must carry a promptId",
            )
            self.assertTrue(
                hitl_prompts[0].get("promptId"),
                "BROWSER_HITL_PROMPT should contain a non-empty promptId",
            )
        # METADATA with usage/latency/model info
        metadata = frames_of_type(ws.messages, BrowserMessageType.METADATA)
        self.assertGreaterEqual(
            len(metadata), 1,
            "Expected METADATA frame",
        )

        # ORCHESTRATION_END should be last
        self.assertEqual(
            types[-1], BrowserMessageType.ORCHESTRATION_END,
            "Last frame should be ORCHESTRATION_END",
        )

    def test_wikipedia_via_handler(self) -> None:
        """Wikipedia search through BrowserHandler — verify full frame sequence."""
        self.logger.info("Starting Wikipedia via handler test")
        instruction = (
            "Navigate to https://en.wikipedia.org. "
            "Type 'Amazon Company' in the search field. "
            "Hit the 'Search' button. "
            "Click on AMZN."
        )
        ws, _handler = self._run_chat(instruction)
        self._assert_frame_sequence(ws, "Wikipedia search")

    def test_form_fill_via_handler(self) -> None:
        """httpbin form fill through BrowserHandler — verify full frame sequence."""
        self.logger.info("Starting form fill via handler test")
        instruction = (
            "Go to https://httpbin.org/forms/post. "
            "Enter 'Visual Worker' as customer name. "
            "Enter '555-555-5555' as phone number. "
            "Enter 'visual-worker@example.com' as email. "
            "Select 'Small' size Pizza. "
            "Check 'Mushroom' as topping. "
            "Enter 'Deliver to my front door.' as delivery instructions. "
            "Click Submit."
        )
        ws, _handler = self._run_chat(instruction)
        self._assert_frame_sequence(ws, "form fill")

    def test_amazon_navigation_via_handler(self) -> None:
        """Amazon.ca navigation through BrowserHandler — verify full frame sequence."""
        self.logger.info("Starting Amazon navigation via handler test")
        instruction = (
            "Navigate to https://www.amazon.ca. "
            "Dismiss any popups that appear. "
            "Click on AmazonBasics. "
            "Click on 'Amazon Resale'. "
            "Click on 'Laptops & Tablets'."
        )
        ws, _handler = self._run_chat(instruction)
        self._assert_frame_sequence(ws, "Amazon navigation")

    def test_gap_navigation_via_handler(self) -> None:
        """Gap Canada navigation through BrowserHandler — verify full frame sequence."""
        self.logger.info("Starting Gap navigation via handler test")
        instruction = (
            "Navigate to https://www.gapcanada.ca. "
            "Dismiss any popups that appear. "
            "Click on Men. "
            "Click on Jeans. "
            "Click on 'Straight'. "
            "Click on 'Straight Jeans' (best seller)."
        )
        ws, _handler = self._run_chat(instruction)
        self._assert_frame_sequence(ws, "Gap navigation")

    def test_nested_popups_via_handler(self) -> None:
        """Nested popups through BrowserHandler — verify full frame sequence."""
        self.logger.info("Starting nested popups via handler test")
        instruction = (
            "1. Go to https://d6xegnjz917v3.cloudfront.net/chatbot/auth/test_popup.html. "
            "2. In basic auth browser prompt type 'test' as username and 'admin1234' as password. "
            "3. Click on 'Open Modal Popup'. "
            "4. dismiss any popup. "
            "5. Click on 'Open Child Popup'. "
            "6. type 'hello from child popup' in 'child text input:' field. "
            "7. Click on 'Open Modal Popup'. "
            "8. dismiss any popup. "
            "9. click on 'Open Grandchild Popup'. "
            "10. Click on 'Open Modal Popup'. "
            "11. dismiss any popup. "
            "12. type 'hello from grandchild popup' in 'Grandchild Text Input:'. "
            "13. click OK. "
            "14. click OK."
        )
        ws, _handler = self._run_chat(instruction)
        self._assert_frame_sequence(ws, "nested popups")

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup shared browser factory."""
        if cls.factory:
            cls.factory.cleanup()



# ===========================================================================
# TestLocalBrowserStop — browser stop and session ended
# ===========================================================================

class TestLocalBrowserStop(unittest.TestCase):
    """Tests for BROWSER_STOP → BROWSER_SESSION_ENDED flow.

    Validates: Requirement 18.9
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalBrowserStop")

    def test_browser_stop_sends_session_ended(self) -> None:
        """BROWSER_STOP after starting automation sends BROWSER_SESSION_ENDED with reason 'stopped'."""
        user_id = "integration-test-%s" % uuid4().hex[:8]
        ws, handler, _factory, store, _storage = _make_handler(user_id=user_id)

        loop = asyncio.get_event_loop()

        # Simulate an active browser session by setting the session name
        handler.active_browser_session_name = handler.session_id

        # Create a session record so _terminate_browser_session can update it
        record = SessionRecord(
            user_id=user_id,
            session_id=handler.session_id,
            browser_session_id=handler.session_id,
            status="active",
        )
        loop.run_until_complete(store.create(user_id, record))

        # Send BROWSER_STOP
        loop.run_until_complete(handler._handle_browser_stop({}))

        ended = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_SESSION_ENDED
        )
        self.assertEqual(len(ended), 1)
        self.assertEqual(ended[0]["reason"], "stopped")
        self.assertEqual(ended[0]["session_id"], handler.session_id)
        self.logger.info(
            "BROWSER_SESSION_ENDED received: reason=%s", ended[0]["reason"]
        )

        # Verify session status updated in store
        updated = loop.run_until_complete(
            store.get(user_id, handler.session_id)
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "stopped")


# ===========================================================================
# TestLocalConcurrentRejection — concurrent message rejection
# ===========================================================================

class TestLocalConcurrentRejection(unittest.TestCase):
    """Tests for concurrent CHAT_MESSAGE rejection during automation.

    Validates: Requirement 18.10
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalConcurrentRejection")

    def test_concurrent_chat_rejected(self) -> None:
        """CHAT_MESSAGE while automation_in_progress returns ERROR with 'Automation in progress'."""
        user_id = "integration-test-%s" % uuid4().hex[:8]
        ws, handler, _factory, _store, _storage = _make_handler(user_id=user_id)

        # Simulate automation in progress
        handler.automation_in_progress = True

        # Concurrent-chat rejection lives in the dispatcher (`_dispatch`),
        # not in `_handle_chat_message` — the rejection has to be synchronous
        # before the chat task is spawned, so the body of the handler
        # never runs. Drive the test through the dispatcher to exercise the
        # real production path.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            handler._dispatch(
                BrowserMessageType.CHAT_MESSAGE,
                {"content": "Do something"},
            )
        )

        errors = frames_of_type(ws.messages, BrowserMessageType.ERROR)
        self.assertEqual(len(errors), 1)
        self.assertIn("Automation in progress", errors[0]["content"])
        self.assertTrue(errors[0].get("recoverable", False))
        self.logger.info(
            "Concurrent rejection: content=%s recoverable=%s",
            errors[0]["content"], errors[0]["recoverable"],
        )



# ===========================================================================
# TestLocalHITL — Human-In-The-Loop over WebSocket
# ===========================================================================

class TestLocalHITL(unittest.TestCase):
    """Tests for HITL prompt/response flow through BrowserHandler.

    Gap Canada navigation is known to trigger handoff_to_user when the agent
    encounters ambiguity (e.g., multiple 'Straight Jeans' options).

    Validates: Requirements 18.6, 18.7
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalHITL")
    factory: BrowserAgentFactory = None

    @classmethod
    def setUpClass(cls) -> None:
        """Create shared BrowserAgentFactory."""
        cls.factory = BrowserAgentFactory()

    def _run_chat_with_hitl(
        self, instruction: str, hitl_action: str = "stop"
    ) -> Tuple[StubWebSocket, BrowserHandler]:
        """Run a chat message that may trigger HITL, auto-responding with given action.

        Spawns a background task that monitors for BROWSER_HITL_PROMPT frames
        and sends a canned BROWSER_HITL_RESPONSE to unblock the agent.
        """
        user_id = "integration-test-%s" % uuid4().hex[:8]
        ws, handler, _factory, _store, _storage = _make_handler(
            user_id=user_id, factory=self.__class__.factory
        )

        async def _hitl_responder() -> None:
            """Monitor for HITL prompts and auto-respond."""
            while not ws.closed:
                await asyncio.sleep(0.5)
                hitl_prompts = frames_of_type(
                    ws.messages, BrowserMessageType.BROWSER_HITL_PROMPT
                )
                if hitl_prompts:
                    prompt_id = hitl_prompts[-1].get("promptId", "")
                    self.logger.info(
                        "HITL prompt detected, responding: promptId=%s action=%s",
                        prompt_id, hitl_action,
                    )
                    await handler._handle_hitl_response({
                        "type": BrowserMessageType.BROWSER_HITL_RESPONSE,
                        "promptId": prompt_id,
                        "action": hitl_action,
                        "value": "",
                    })
                    break

        async def _execute() -> None:
            await handler._send_connection_established()
            # Start HITL responder in background
            responder_task = asyncio.create_task(_hitl_responder())
            try:
                await handler._handle_chat_message({"content": instruction})
            finally:
                responder_task.cancel()
                try:
                    await responder_task
                except asyncio.CancelledError:
                    pass

        asyncio.get_event_loop().run_until_complete(_execute())
        return ws, handler

    def test_gap_navigation_triggers_hitl_prompt(self) -> None:
        """Gap Canada instruction produces BROWSER_HITL_PROMPT with promptId and question."""
        self.logger.info("Starting Gap HITL prompt test")
        instruction = (
            "Navigate to https://www.gapcanada.ca. "
            "Dismiss any popups that appear. "
            "Click on Men. "
            "Click on Jeans. "
            "Click on 'Straight'. "
            "Click on 'Straight Jeans' (best seller)."
        )
        ws, _handler = self._run_chat_with_hitl(instruction)

        hitl_prompts = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_HITL_PROMPT
        )
        # HITL may or may not trigger depending on agent behavior
        if hitl_prompts:
            prompt = hitl_prompts[0]
            self.assertIn("promptId", prompt)
            self.assertIn("question", prompt)
            self.assertIn("screenshotBase64", prompt)
            self.logger.info(
                "HITL prompt received: promptId=%s question_len=%d",
                prompt["promptId"], len(prompt.get("question", "")),
            )
        else:
            self.logger.info(
                "No HITL prompt triggered — agent completed without ambiguity"
            )

        # Verify orchestration completed regardless
        orch_end = frames_of_type(
            ws.messages, BrowserMessageType.ORCHESTRATION_END
        )
        self.assertGreaterEqual(len(orch_end), 1, "Expected ORCHESTRATION_END")

    def test_hitl_response_resumes_agent(self) -> None:
        """Canned HITL response with action 'stop' allows orchestration to complete."""
        self.logger.info("Starting HITL response resume test")
        instruction = (
            "Navigate to https://www.gapcanada.ca. "
            "Dismiss any popups that appear. "
            "Click on Men. "
            "Click on Jeans. "
            "Click on 'Straight'. "
            "Click on 'Straight Jeans' (best seller)."
        )
        ws, _handler = self._run_chat_with_hitl(instruction, hitl_action="stop")

        # Verify ORCHESTRATION_END follows (agent completed or stopped)
        types = frame_types(ws.messages)
        self.assertIn(
            BrowserMessageType.ORCHESTRATION_END, types,
            "ORCHESTRATION_END should appear after HITL response",
        )
        self.logger.info("Agent completed after HITL response")

    def test_hitl_prompt_contains_screenshot(self) -> None:
        """BROWSER_HITL_PROMPT includes screenshotBase64 field."""
        self.logger.info("Starting HITL screenshot test")
        instruction = (
            "Navigate to https://www.gapcanada.ca. "
            "Dismiss any popups that appear. "
            "Click on Men. "
            "Click on Jeans. "
            "Click on 'Straight'. "
            "Click on 'Straight Jeans' (best seller)."
        )
        ws, _handler = self._run_chat_with_hitl(instruction)

        hitl_prompts = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_HITL_PROMPT
        )
        if hitl_prompts:
            self.assertIn("screenshotBase64", hitl_prompts[0])
            self.logger.info(
                "HITL prompt screenshotBase64 present: len=%d",
                len(hitl_prompts[0].get("screenshotBase64", "")),
            )
        else:
            self.logger.info(
                "No HITL prompt triggered — skipping screenshot assertion"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup shared browser factory."""
        if cls.factory:
            cls.factory.cleanup()



# ===========================================================================
# TestLocalSessionPersistence — DynamoDB/S3 session persistence
# ===========================================================================

class TestLocalSessionPersistence(unittest.TestCase):
    """Tests for session persistence with DynamoDB + S3 backends.

    Requires:
    - BA_SESSION_STORE_TYPE=dynamodb
    - BA_SESSION_STORE_TABLE set to a valid DynamoDB table
    - BA_SESSION_STORE_BUCKET set to a valid S3 bucket
    - BA_SESSION_STORE_PREFIX=integration-tests

    Skips if BA_SESSION_STORE_TYPE is not 'dynamodb'.

    Validates: Requirements 18.8, 18.12
    """

    logger: Logger = get_logger(f"{__name__}.TestLocalSessionPersistence")
    factory: BrowserAgentFactory = None
    _created_sessions: List[Tuple[str, str]] = []

    @classmethod
    def setUpClass(cls) -> None:
        """Create shared factory and verify DynamoDB configuration."""
        store_type = os.environ.get("BA_SESSION_STORE_TYPE", "memory")
        if store_type != "dynamodb":
            raise unittest.SkipTest(
                "TestLocalSessionPersistence requires BA_SESSION_STORE_TYPE=dynamodb"
            )
        table = os.environ.get("BA_SESSION_STORE_TABLE", "")
        if not table:
            raise unittest.SkipTest(
                "TestLocalSessionPersistence requires BA_SESSION_STORE_TABLE"
            )
        bucket = os.environ.get("BA_SESSION_STORE_BUCKET", "")
        if not bucket:
            raise unittest.SkipTest(
                "TestLocalSessionPersistence requires BA_SESSION_STORE_BUCKET"
            )
        cls.factory = BrowserAgentFactory()
        cls._created_sessions = []

    def _make_ddb_handler(self) -> Tuple[StubWebSocket, BrowserHandler, SessionStoreBase, ScreenshotStorageBase, str]:
        """Create handler with DynamoDB session store."""
        user_id = "integration-test-%s" % uuid4().hex[:8]
        ws, handler, _factory, store, storage = _make_handler(
            user_id=user_id,
            store_type="dynamodb",
            factory=self.__class__.factory,
        )
        self.__class__._created_sessions.append((user_id, handler.session_id))
        return ws, handler, store, storage, user_id

    def _run_wikipedia_chat(
        self, _ws: StubWebSocket, handler: BrowserHandler
    ) -> None:
        """Send a Wikipedia instruction through the handler."""
        instruction = (
            "Navigate to https://en.wikipedia.org. "
            "Type 'Amazon Company' in the search field. "
            "Hit the 'Search' button."
        )

        async def _execute() -> None:
            await handler._send_connection_established()
            await handler._handle_chat_message({"content": instruction})

        asyncio.get_event_loop().run_until_complete(_execute())

    def test_chat_persists_session_to_dynamodb(self) -> None:
        """Chat message persists session record to DynamoDB with status and history."""
        self.logger.info("Starting DynamoDB persistence test")
        ws, handler, store, _storage, user_id = self._make_ddb_handler()
        self._run_wikipedia_chat(ws, handler)

        loop = asyncio.get_event_loop()
        record = loop.run_until_complete(
            store.get(user_id, handler.session_id)
        )
        self.assertIsNotNone(record, "Session record should exist in DynamoDB")
        self.assertIn(record.status, ["active", "completed", "stopped"])
        self.assertGreater(
            len(record.conversation_history), 0,
            "conversation_history should not be empty",
        )
        self.logger.info(
            "DynamoDB session: status=%s history_len=%d steps=%d",
            record.status, len(record.conversation_history),
            record.steps_completed,
        )

    def test_resume_session_loads_history(self) -> None:
        """Chat in session A, NEW_SESSION to B, RESUME_SESSION to A loads history."""
        self.logger.info("Starting resume session test")
        ws, handler, _store, _storage, user_id = self._make_ddb_handler()
        session_a_id = handler.session_id

        # Chat in session A
        self._run_wikipedia_chat(ws, handler)

        loop = asyncio.get_event_loop()

        # NEW_SESSION → creates session B
        loop.run_until_complete(handler._handle_new_session({}))
        session_b_id = handler.session_id
        self.__class__._created_sessions.append((user_id, session_b_id))
        self.assertNotEqual(session_a_id, session_b_id)

        # RESUME_SESSION → back to session A
        ws.messages.clear()
        loop.run_until_complete(
            handler._handle_resume_session({"session_id": session_a_id})
        )

        resumed = frames_of_type(
            ws.messages, BrowserMessageType.SESSION_RESUMED
        )
        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0]["session_id"], session_a_id)
        self.assertIsInstance(resumed[0]["conversation_history"], list)
        self.assertGreater(
            len(resumed[0]["conversation_history"]), 0,
            "Resumed session should have conversation history",
        )
        self.logger.info(
            "Session resumed: session_id=%s history_len=%d",
            session_a_id, len(resumed[0]["conversation_history"]),
        )

    def test_get_sessions_returns_persisted_sessions(self) -> None:
        """Chat in two sessions, GET_SESSIONS returns both sorted by created_at desc."""
        self.logger.info("Starting get sessions test")
        user_id = "integration-test-%s" % uuid4().hex[:8]

        # Session 1
        ws1, handler1, _factory, store, _storage = _make_handler(
            user_id=user_id, store_type="dynamodb", factory=self.__class__.factory
        )
        self.__class__._created_sessions.append((user_id, handler1.session_id))
        self._run_wikipedia_chat(ws1, handler1)
        session_1_id = handler1.session_id

        # Session 2 — use NEW_SESSION on same handler
        loop = asyncio.get_event_loop()
        loop.run_until_complete(handler1._handle_new_session({}))
        session_2_id = handler1.session_id
        self.__class__._created_sessions.append((user_id, session_2_id))

        # Create a record for session 2
        record2 = SessionRecord(
            user_id=user_id,
            session_id=session_2_id,
            status="active",
        )
        loop.run_until_complete(store.create(user_id, record2))

        # GET_SESSIONS
        ws1.messages.clear()
        loop.run_until_complete(handler1._handle_get_sessions({}))

        loaded = frames_of_type(
            ws1.messages, BrowserMessageType.SESSIONS_LOADED
        )
        self.assertEqual(len(loaded), 1)
        sessions = loaded[0]["sessions"]
        # Current session is excluded from list, so session_1 should appear
        session_ids = [s["session_id"] for s in sessions]
        self.assertIn(session_1_id, session_ids)
        self.logger.info(
            "GET_SESSIONS returned %d sessions: %s",
            len(sessions), session_ids,
        )

    def test_delete_session_removes_from_store(self) -> None:
        """Create and chat, delete via DELETE_SESSION, verify GET_SESSIONS excludes it."""
        self.logger.info("Starting delete session persistence test")
        ws, handler, store, _storage, user_id = self._make_ddb_handler()
        self._run_wikipedia_chat(ws, handler)
        target_id = handler.session_id

        loop = asyncio.get_event_loop()

        # Switch to new session so target is not the current session
        loop.run_until_complete(handler._handle_new_session({}))
        self.__class__._created_sessions.append((user_id, handler.session_id))

        # Delete the original session
        ws.messages.clear()
        loop.run_until_complete(
            handler._handle_delete_session({"session_id": target_id})
        )

        deleted = frames_of_type(
            ws.messages, BrowserMessageType.SESSION_DELETED
        )
        self.assertEqual(len(deleted), 1)

        # Verify it's gone from the store
        record = loop.run_until_complete(store.get(user_id, target_id))
        self.assertIsNone(record, "Deleted session should not exist in store")
        self.logger.info("Session %s deleted from DynamoDB", target_id)

    def test_screenshots_persisted_to_s3(self) -> None:
        """Wikipedia instruction persists screenshots to S3 at expected path."""
        self.logger.info("Starting S3 screenshot persistence test")
        ws, handler, _store, _storage, user_id = self._make_ddb_handler()
        self._run_wikipedia_chat(ws, handler)

        # Check for BROWSER_SCREENSHOT frames (indicates screenshots were captured)
        screenshots = frames_of_type(
            ws.messages, BrowserMessageType.BROWSER_SCREENSHOT
        )
        if screenshots:
            self.logger.info(
                "Screenshots captured: count=%d", len(screenshots)
            )
            # Verify S3 objects exist at expected prefix
            bucket = os.environ.get("BA_SESSION_STORE_BUCKET", "")
            prefix = os.environ.get("BA_SESSION_STORE_PREFIX", "integration-tests")
            expected_prefix = "%s/%s/%s/screenshots/" % (
                prefix, user_id, handler.session_id
            )

            from utils.session_helper import get_boto3_session, get_boto3_client_config
            s3_client = get_boto3_session().client(
                's3', config=get_boto3_client_config()
            )
            response = s3_client.list_objects_v2(
                Bucket=bucket, Prefix=expected_prefix
            )
            objects = response.get("Contents", [])
            self.assertGreater(
                len(objects), 0,
                "Expected screenshot objects in S3 at %s" % expected_prefix,
            )
            self.logger.info(
                "S3 screenshots: prefix=%s count=%d",
                expected_prefix, len(objects),
            )
        else:
            self.logger.info(
                "No BROWSER_SCREENSHOT frames — screenshots may not have been captured"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup: delete all sessions created during test run."""
        if not cls._created_sessions:
            return

        store_type = os.environ.get("BA_SESSION_STORE_TYPE", "memory")
        if store_type != "dynamodb":
            return

        store = create_session_store(store_type)
        loop = asyncio.get_event_loop()
        for user_id, session_id in cls._created_sessions:
            try:
                loop.run_until_complete(store.delete(user_id, session_id))
            except Exception as exc:
                get_logger(__name__).warning(
                    "Teardown cleanup failed: user=%s session=%s error=%s",
                    user_id, session_id, str(exc),
                )

        if cls.factory:
            cls.factory.cleanup()


if __name__ == "__main__":
    unittest.main()
