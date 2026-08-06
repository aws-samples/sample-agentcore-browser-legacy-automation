# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
BrowserHandler — WebSocket message router for the browser automation protocol.

Routes incoming WebSocket messages to the appropriate handler method, manages
browser session lifecycle, concurrent message rejection, HITL over WebSocket,
disconnect grace period, and session name validation.

Lifecycle:
    1. Generate session_id on construction
    2. Defer CONNECTION_ESTABLISHED until first client message
    3. Loop: receive messages → dispatch by type (9 handlers)
    4. Grace period on disconnect → terminate browser session

Validates: Requirements 5.1–5.10, 6.1–6.8, 7.1–7.2, 8.2–8.5
"""

import asyncio
import json
import os
import secrets
from datetime import datetime, timezone
from logging import Logger
from typing import Any, Dict, List, Optional

from utils.logging_helper import get_logger

from handlers.session_store import SessionRecord, SessionStoreBase
from handlers.screenshot_storage import ScreenshotStorageBase
from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter
from models.websocket_message_types import BrowserMessageType


class BrowserHandler:
    """WebSocket message router for the browser automation protocol.

    Generates a server-side session ID on construction, defers
    ``CONNECTION_ESTABLISHED`` until the first client message,
    dispatches incoming messages by type to 9 handler methods,
    and manages browser session lifecycle including HITL blocking,
    concurrent message rejection, and disconnect grace period.

    Attributes:
        ws: WebSocket adapter instance.
        agent_factory: BrowserAgentFactory for creating Strands Agents.
        session_store: Pluggable session persistence backend.
        screenshot_storage: Pluggable screenshot storage backend.
        profile: Active profile name (default ``browser``).
        user_id: Authenticated user identity from JWT.
        session_id: Server-generated session identifier.
        automation_in_progress: Flag for concurrent message rejection.
        active_browser_session_name: Current browser microVM session name.
        hitl_event: asyncio.Event for HITL blocking.
        hitl_response: Payload from BROWSER_HITL_RESPONSE.
        disconnect_grace_task: Pending grace period task.
    """

    logger: Logger = get_logger(f"{__name__}.BrowserHandler")

    def __init__(
        self,
        websocket: StarletteWebSocketAdapter,
        agent_factory: Any,
        session_store: SessionStoreBase,
        screenshot_storage: ScreenshotStorageBase,
        profile: str = "browser",
        user_id: str = "local",
    ) -> None:
        self.ws: StarletteWebSocketAdapter = websocket
        self.agent_factory: Any = agent_factory
        self.session_store: SessionStoreBase = session_store
        self.screenshot_storage: ScreenshotStorageBase = screenshot_storage
        self.profile: str = profile
        self.user_id: str = user_id
        self.session_id: str = self._generate_session_id()
        self.automation_in_progress: bool = False
        self.active_browser_session_name: Optional[str] = None
        self.hitl_event: Optional[asyncio.Event] = None
        self.hitl_response: Optional[dict] = None
        self.disconnect_grace_task: Optional[asyncio.Task] = None
        self._agent: Optional[Any] = None
        self._browser_tool: Optional[Any] = None
        # ``CHAT_MESSAGE`` runs as a background task so the main receive
        # loop stays responsive to ``BROWSER_HITL_RESPONSE`` frames while
        # the agent is streaming (see
        # ``.kiro/research/temp-browser-ui-issues-analysis.md`` Issue 5).
        self._chat_task: Optional[asyncio.Task] = None

    @staticmethod
    def _generate_session_id() -> str:
        """Generate server-side session ID: ``brws_{YYYYMMDD}_{HHMMSS}_{hex8}``.

        Returns:
            A session ID string matching the format
            ``^brws_\\d{8}_\\d{6}_[0-9a-f]{8}$``.

        Validates: Requirement 17.2
        """
        now: datetime = datetime.now(timezone.utc)
        return "brws_%s_%s_%s" % (
            now.strftime('%Y%m%d'),
            now.strftime('%H%M%S'),
            secrets.token_hex(4),
        )

    async def handle_connection(self) -> None:
        """Main connection loop.

        Defers ``CONNECTION_ESTABLISHED`` until after the first client message
        arrives, because AgentCore's WebSocket proxy only starts relaying
        container frames after the client sends the first message.

        Validates: Requirements 4.3, 5.1
        """
        connection_established_sent: bool = False

        async for raw_message in self.ws:
            try:
                payload: dict = json.loads(raw_message)
                msg_type: str = payload.get('type', '')

                if not connection_established_sent:
                    await self._send_connection_established()
                    connection_established_sent = True

                await self._dispatch(msg_type, payload)
            except json.JSONDecodeError:
                await self._send_error("Invalid JSON message")
            except Exception as exc:
                self.logger.error(
                    "Message handling error: session=%s error=%s",
                    self.session_id, str(exc),
                )
                await self._send_error(str(exc))

        # Wait for any in-flight chat task to complete before running the
        # disconnect handler. This ensures the grace-period task and any
        # final bookkeeping do not race with the chat body, and lets tests
        # observe the full streaming outcome after the message queue drains.
        await self._await_chat_task()

        # WebSocket disconnected — start grace period
        await self._handle_disconnect()

    async def _await_chat_task(self) -> None:
        """If a CHAT_MESSAGE task is in flight, wait for it to finish.

        Swallows CancelledError (raised when ``_handle_disconnect`` cancelled
        the task) and any exception surfaced by the task — those are
        already logged by the task wrapper.
        """
        if self._chat_task is None:
            return
        try:
            await self._chat_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug(
                "Chat task completed with error: session=%s error=%s",
                self.session_id, str(exc),
            )

    async def _dispatch(self, msg_type: str, payload: dict) -> None:
        """Dispatch a message to the appropriate handler by type.

        Routes to 9 handler methods via BrowserMessageType constants.
        Unknown types produce an ERROR frame.

        ``CHAT_MESSAGE`` is dispatched as a background task so the main
        receive loop stays free to read subsequent frames — specifically
        ``BROWSER_HITL_RESPONSE`` frames that need to dispatch while the
        agent is mid-stream. Without this, the receive loop would block
        inside the streaming call and HITL responses would queue up until
        the 300 s timeout fired (Issue 5 in
        ``.kiro/research/temp-browser-ui-issues-analysis.md``).

        Concurrent-chat protection: ``automation_in_progress`` is set
        synchronously here before the task is spawned, so a rapid second
        ``CHAT_MESSAGE`` sees the flag and is rejected with an ERROR.

        Validates: Requirements 5.1–5.10
        """
        handlers: Dict[str, Any] = {
            BrowserMessageType.CONNECTION_INIT: self._handle_connection_init,
            BrowserMessageType.BROWSER_STOP: self._handle_browser_stop,
            BrowserMessageType.BROWSER_HITL_RESPONSE: self._handle_hitl_response,
            BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST: self._handle_live_view_request,
            BrowserMessageType.NEW_SESSION: self._handle_new_session,
            BrowserMessageType.RESUME_SESSION: self._handle_resume_session,
            BrowserMessageType.GET_SESSIONS: self._handle_get_sessions,
            BrowserMessageType.DELETE_SESSION: self._handle_delete_session,
        }
        self.logger.debug(
            "Dispatching message: session=%s type=%s", self.session_id, msg_type
        )

        if msg_type == BrowserMessageType.CHAT_MESSAGE:
            # Reject concurrent chats synchronously — we cannot rely on the
            # handler body to set automation_in_progress before the next
            # frame arrives, because the body runs on a separate task.
            if self.automation_in_progress:
                await self._send_error(
                    "Automation in progress", recoverable=True
                )
                return
            self.automation_in_progress = True
            self._chat_task = asyncio.create_task(
                self._run_chat_message_task(payload)
            )
            return

        handler = handlers.get(msg_type)
        if handler:
            await handler(payload)
        else:
            await self._send_error("Unknown message type: %s" % msg_type)

    async def _run_chat_message_task(self, payload: dict) -> None:
        """Background wrapper around ``_handle_chat_message``.

        The caller set ``automation_in_progress = True`` synchronously
        before spawning this task. We leave the body of
        ``_handle_chat_message`` responsible for clearing the flag in its
        ``finally`` block (so streaming errors still clear it), plus we
        catch anything that escapes here so a silent task failure cannot
        leave the handler stuck with the flag latched.
        """
        try:
            await self._handle_chat_message(payload)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(
                "Chat task crashed: session=%s error=%s",
                self.session_id, str(exc),
            )
            # Safety net — the body normally clears this in its own finally.
            self.automation_in_progress = False
            try:
                await self._send_error(str(exc), recoverable=True)
            except Exception:  # pylint: disable=broad-except
                # WebSocket may already be closed; swallow to avoid looping.
                pass

    async def _handle_connection_init(self, _payload: dict) -> None:
        """Handle CONNECTION_INIT — no-op.

        The handshake response (CONNECTION_ESTABLISHED) is sent by
        ``handle_connection`` before dispatching the first message.
        This handler exists so CONNECTION_INIT is recognized as a
        valid message type and does not produce an error.

        Validates: Requirement 5.1
        """

    async def _handle_chat_message(self, payload: dict) -> None:
        """Process a chat message: create browser session, run agent, stream response.

        Concurrent-chat rejection and the ``automation_in_progress`` flag are
        handled by ``_dispatch`` BEFORE this body runs — this method assumes
        the flag is already ``True`` on entry and is responsible for clearing
        it in its ``finally`` block. Directly invoking this method (instead
        of going through ``_dispatch``) bypasses the flag management and is
        therefore only appropriate in tests.

        Creates browser session on first CHAT_MESSAGE. Delegates to
        BrowserStreamer for event-to-frame mapping.

        Validates: Requirements 5.2, 6.1, 6.2, 7.1, 7.2
        """
        content: str = payload.get('content', '')
        self.logger.debug(
            "Chat message: session=%s content_len=%d",
            self.session_id, len(content),
        )

        # Create browser session on first CHAT_MESSAGE if none active
        if self.active_browser_session_name is None:
            try:
                agent = self.agent_factory.create_agent()
                self._agent = agent
                self._browser_tool = self.agent_factory.browser_tool

                # Set screenshot context and storage backend
                if self._browser_tool and hasattr(self._browser_tool, '_screenshot_tool'):
                    self._browser_tool._screenshot_tool.set_context(
                        self.user_id, self.session_id, self.screenshot_storage
                    )

                # Wire HITL tool to the WebSocket adapter + response waiter.
                # Must happen BEFORE the agent starts streaming so the first
                # handoff_to_user call has a live context. The captured loop
                # is the handler's main loop (we're inside its async code).
                if self._browser_tool and hasattr(self._browser_tool, '_handoff_tool'):
                    self._browser_tool._handoff_tool.set_hitl_context(
                        websocket=self.ws,
                        wait_for_response=self.wait_for_hitl_response,
                    )

                self.active_browser_session_name = self.session_id

                # Generate live view URL from the stored BrowserClient
                live_view_url: str = ""
                if self._browser_tool and hasattr(self._browser_tool, 'get_live_view_url'):
                    live_view_url = self._browser_tool.get_live_view_url()

                # Create session record
                session_record = SessionRecord(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    browser_session_id=self.active_browser_session_name,
                    status="active",
                    live_view_url=live_view_url,
                )
                await self.session_store.create(self.user_id, session_record)

                await self.ws.send_json({
                    'type': BrowserMessageType.BROWSER_SESSION_STARTED,
                    'session_id': self.session_id,
                    'liveViewUrl': live_view_url,
                })
                self.logger.info(
                    "Browser session started: session=%s", self.session_id
                )
            except Exception as exc:
                self.logger.error(
                    "Failed to create browser session: %s", str(exc)
                )
                await self._send_error(
                    "Failed to create browser session: %s" % str(exc)
                )
                return

        # Update conversation history with the user turn. The assistant turn
        # is persisted AFTER streaming completes so the stored history
        # reflects both sides of the conversation on resume (see Issue 4 in
        # ``.kiro/research/temp-browser-ui-issues-analysis.md``).
        await self.session_store.update(self.user_id, self.session_id, {
            'conversation_history': await self._get_updated_history(
                'user', content
            ),
        })

        # Stream agent response. ``automation_in_progress`` is set by
        # ``_dispatch`` before this task is spawned; clear it in finally.
        try:
            # Import here to avoid circular imports
            from streaming.browser_streamer import BrowserStreamer

            streamer = BrowserStreamer(
                websocket=self.ws,
                session_store=self.session_store,
                screenshot_storage=self.screenshot_storage,
                user_id=self.user_id,
                session_id=self.session_id,
            )
            await streamer.stream_events(self._agent, content)

            # Persist the assistant's final text turn for resume fidelity.
            # The streamer captures this from Strands' terminal
            # ``{"result": AgentResult}`` event (preferred) or from the
            # last text-only assistant message (fallback). An empty string
            # is still persisted so the turn count stays balanced between
            # user and assistant roles even for automation-only sessions.
            assistant_text: str = streamer.final_assistant_text
            await self.session_store.update(self.user_id, self.session_id, {
                'conversation_history': await self._get_updated_history(
                    'assistant', assistant_text,
                ),
            })
        except Exception as exc:
            self.logger.error(
                "Streaming error: session=%s error=%s",
                self.session_id, str(exc),
            )
            await self._send_error(str(exc), recoverable=True)
        finally:
            self.automation_in_progress = False

    async def _handle_browser_stop(self, _payload: dict) -> None:
        """Terminate the active browser session immediately.

        Validates: Requirements 5.3, 6.3
        """
        await self._terminate_browser_session("stopped")
        await self.ws.send_json({
            'type': BrowserMessageType.BROWSER_SESSION_ENDED,
            'session_id': self.session_id,
            'reason': 'stopped',
        })
        self.logger.info("Browser session stopped: session=%s", self.session_id)

    async def _handle_hitl_response(self, payload: dict) -> None:
        """Pass HITL response to the blocked agent loop.

        Validates: Requirements 5.4, 8.3
        """
        self.hitl_response = payload
        if self.hitl_event is not None:
            self.hitl_event.set()

        # Update session status back to active
        await self.session_store.update(self.user_id, self.session_id, {
            'status': 'active',
        })
        self.logger.info(
            "HITL response received: session=%s prompt_id=%s",
            self.session_id, payload.get('promptId', ''),
        )

    async def _handle_live_view_request(self, _payload: dict) -> None:
        """Generate a fresh pre-signed live view URL and send to client.

        Generates a new URL on each request (pre-signed URLs expire after
        max 300s), so the frontend can refresh the live view for long-running
        sessions.

        Validates: Requirement 5.9
        """
        live_view_url: str = ""
        if self._browser_tool and hasattr(self._browser_tool, 'get_live_view_url'):
            live_view_url = self._browser_tool.get_live_view_url()

        await self.ws.send_json({
            'type': BrowserMessageType.BROWSER_LIVE_VIEW_URL,
            'session_id': self.session_id,
            'liveViewUrl': live_view_url,
        })

    async def _handle_new_session(self, _payload: dict) -> None:
        """Terminate active browser session, generate new session_id, reset state.

        Validates: Requirements 5.5, 6.4
        """
        # Terminate existing browser session if active
        if self.active_browser_session_name is not None:
            await self._terminate_browser_session("stopped")

        # Generate new session
        self.session_id = self._generate_session_id()
        self.automation_in_progress = False
        self.hitl_event = None
        self.hitl_response = None
        self._agent = None
        self._browser_tool = None

        await self.ws.send_json({
            'type': BrowserMessageType.SESSION_CREATED,
            'session_id': self.session_id,
        })
        self.logger.info("New session created: session=%s", self.session_id)

    async def _handle_resume_session(self, payload: dict) -> None:
        """Load conversation history from SessionStore and respond.

        Does NOT reconnect to browser microVM (ephemeral).

        Validates: Requirement 5.6
        """
        target_session_id: str = payload.get('session_id', '')
        self.session_id = target_session_id

        self.logger.debug("Resuming session: %s", target_session_id)

        conversation_history: List[dict] = []
        if target_session_id:
            session_record = await self.session_store.get(
                self.user_id, target_session_id
            )
            if session_record:
                conversation_history = session_record.conversation_history

        await self.ws.send_json({
            'type': BrowserMessageType.SESSION_RESUMED,
            'session_id': self.session_id,
            'conversation_history': conversation_history,
        })
        self.logger.info(
            "Session resumed: session=%s turns=%d",
            self.session_id, len(conversation_history),
        )

    async def _handle_get_sessions(self, _payload: dict) -> None:
        """List sessions from SessionStore and respond.

        Each returned session dict carries `profile` (e.g. ``"browser"``) and
        `mode` (always ``"text"`` for the browser profile) so the shared
        frontend ``SessionList`` component can route per-profile icons and
        resume callbacks without collapsing everything to text-or-voice.

        Validates: Requirement 5.7
        """
        try:
            records: List[SessionRecord] = await self.session_store.list_sessions(
                self.user_id
            )
            sessions: List[dict] = []
            for rec in records:
                # Skip current active session
                if rec.session_id == self.session_id:
                    continue
                first_preview: str = ""
                if rec.conversation_history:
                    for msg in rec.conversation_history:
                        if msg.get('role') == 'user':
                            first_preview = msg.get('content', '')[:80]
                            break
                sessions.append({
                    'session_id': rec.session_id,
                    'profile': self.profile,
                    'mode': 'text',
                    'created_at': rec.created_at,
                    'message_count': len(rec.conversation_history),
                    'first_message_preview': first_preview,
                    'status': rec.status,
                })

            await self.ws.send_json({
                'type': BrowserMessageType.SESSIONS_LOADED,
                'sessions': sessions,
            })
        except Exception as exc:
            self.logger.error(
                "Failed to load sessions: session=%s error=%s",
                self.session_id, str(exc),
            )
            await self.ws.send_json({
                'type': BrowserMessageType.SESSIONS_LOADED,
                'sessions': [],
            })

    async def _handle_delete_session(self, payload: dict) -> None:
        """Remove session from SessionStore and respond.

        Validates: Requirement 5.8
        """
        target_session_id: str = payload.get('session_id', '')
        if target_session_id:
            await self.session_store.delete(self.user_id, target_session_id)

        await self.ws.send_json({
            'type': BrowserMessageType.SESSION_DELETED,
            'session_id': target_session_id,
        })
        self.logger.info(
            "Session deleted: session=%s", target_session_id
        )

    def _validate_session_name(self, name: str) -> str:
        """Map any Claude session name to the active browser session.

        Since only one browser session is active per connection, any
        session name from Claude is mapped to the active session.

        Validates: Requirement 6.8
        """
        if self.active_browser_session_name is not None:
            return self.active_browser_session_name
        return name

    async def _handle_disconnect(self) -> None:
        """Start grace period before terminating browser session.

        Also cancels any in-flight CHAT_MESSAGE task so the streaming loop
        does not keep running (and writing to a closed WebSocket) after the
        client disconnects. If HITL is pending, we first set the event so
        the blocked waiter returns promptly with None, then cancel the task
        as a belt-and-suspenders measure.

        Validates: Requirements 6.5, 6.6, 8.5
        """
        grace_seconds: int = int(
            os.environ.get('BA_DISCONNECT_GRACE_SECONDS', '30')
        )

        # If HITL is pending, use grace period instead of HITL timeout
        if self.hitl_event is not None and not self.hitl_event.is_set():
            self.hitl_event.set()  # Unblock the agent loop

        # Cancel the in-flight chat task (if any) so it doesn't keep trying
        # to send frames to a closed socket. The task may still finish its
        # finally block; that is fine — any late sends will simply raise
        # and be swallowed by the task's exception handler.
        if self._chat_task is not None and not self._chat_task.done():
            self._chat_task.cancel()

        if self.active_browser_session_name is None:
            return

        self.logger.info(
            "WebSocket disconnected, starting grace period: session=%s seconds=%d",
            self.session_id, grace_seconds,
        )

        async def _grace_period() -> None:
            await asyncio.sleep(grace_seconds)
            self.logger.info(
                "Grace period expired, terminating: session=%s",
                self.session_id,
            )
            await self._terminate_browser_session("completed")

        self.disconnect_grace_task = asyncio.create_task(_grace_period())

    async def _send_connection_established(self) -> None:
        """Send CONNECTION_ESTABLISHED with session_id and profile.

        Validates: Requirement 5.1
        """
        await self.ws.send_json({
            'type': BrowserMessageType.CONNECTION_ESTABLISHED,
            'session_id': self.session_id,
            'profile': self.profile,
        })
        self.logger.info(
            "Connection established: session=%s profile=%s",
            self.session_id, self.profile,
        )

    async def _send_error(
        self,
        content: str,
        recoverable: bool = True,
    ) -> None:
        """Send an error frame to the client.

        Validates: Requirement 5.10
        """
        await self.ws.send_json({
            'type': BrowserMessageType.ERROR,
            'content': content,
            'recoverable': recoverable,
        })

    async def _terminate_browser_session(self, reason: str) -> None:
        """Terminate the active browser session and update session record.

        Validates: Requirements 6.3, 6.4
        """
        # Drop HITL wiring before cleaning up the tool — prevents stale
        # WebSocket/loop references from bleeding into a future session
        # reused on this connection.
        if self._browser_tool is not None and hasattr(
            self._browser_tool, '_handoff_tool'
        ):
            self._browser_tool._handoff_tool.clear_hitl_context()

        if self._browser_tool is not None:
            try:
                self.agent_factory.cleanup()
            except Exception as exc:
                self.logger.warning("Browser cleanup error: %s", str(exc))

        self.active_browser_session_name = None
        self._agent = None
        self._browser_tool = None

        # Update session status
        await self.session_store.update(self.user_id, self.session_id, {
            'status': reason,
        })

    async def wait_for_hitl_response(self, timeout: Optional[float] = None) -> Optional[dict]:
        """Block until HITL response is received or timeout expires.

        Called by BrowserStreamer when handoff_to_user is detected.

        Args:
            timeout: Seconds to wait. Defaults to BA_HITL_TIMEOUT_SECONDS.

        Returns:
            The HITL response payload, or None on timeout.

        Validates: Requirements 8.2, 8.3, 8.4
        """
        if timeout is None:
            timeout = float(
                os.environ.get('BA_HITL_TIMEOUT_SECONDS', '300')
            )

        self.hitl_event = asyncio.Event()
        self.hitl_response = None

        # Update session status to paused_hitl
        await self.session_store.update(self.user_id, self.session_id, {
            'status': 'paused_hitl',
        })

        try:
            await asyncio.wait_for(self.hitl_event.wait(), timeout=timeout)
            return self.hitl_response
        except asyncio.TimeoutError:
            self.logger.warning(
                "HITL timeout: session=%s timeout=%ss",
                self.session_id, timeout,
            )
            # Send timeout notification
            await self.ws.send_json({
                'type': BrowserMessageType.BROWSER_HITL_TIMEOUT,
                'session_id': self.session_id,
            })
            # Restore active status
            await self.session_store.update(self.user_id, self.session_id, {
                'status': 'active',
            })
            return None
        finally:
            self.hitl_event = None

    async def _get_updated_history(
        self, role: str, content: str
    ) -> List[Dict[str, str]]:
        """Append a message to conversation history and return the updated list."""
        session_record = await self.session_store.get(
            self.user_id, self.session_id
        )
        history: List[Dict[str, str]] = []
        if session_record:
            history = list(session_record.conversation_history)
        history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        return history
