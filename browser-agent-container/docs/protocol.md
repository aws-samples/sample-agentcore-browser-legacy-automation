# WebSocket Protocol — Browser Agent Container

The browser protocol carries 9 client-to-server frame types and 19 server-to-client frame types across a single WebSocket per session. The backend constants live in [`src/models/websocket_message_types.py`](../src/models/websocket_message_types.py); the UI mirror lives in [`chat-bot-ui/src/types/browser.types.ts`](../../chat-bot-ui/src/types/browser.types.ts). Both must stay in lockstep.

## Frame census

**Client → Server (9)**: `CONNECTION_INIT`, `CHAT_MESSAGE`, `BROWSER_STOP`, `BROWSER_HITL_RESPONSE`, `BROWSER_LIVE_VIEW_REQUEST`, `NEW_SESSION`, `RESUME_SESSION`, `GET_SESSIONS`, `DELETE_SESSION`.

**Server → Client (19)**: 11 shared (`CONNECTION_ESTABLISHED`, `SESSION_CREATED`, `SESSION_RESUMED`, `SESSIONS_LOADED`, `SESSION_DELETED`, `ORCHESTRATION_START`, `ORCHESTRATION_END`, `REASONING`, `STREAM`, `METADATA`, `ERROR`) + 8 browser-specific (`BROWSER_SESSION_STARTED`, `BROWSER_ACTION_START`, `BROWSER_SCREENSHOT`, `BROWSER_ACTION_COMPLETE`, `BROWSER_HITL_PROMPT`, `BROWSER_HITL_TIMEOUT`, `BROWSER_LIVE_VIEW_URL`, `BROWSER_SESSION_ENDED`).

## Invariants

- **ACTION_START/COMPLETE pairing**: every `BROWSER_ACTION_START` is followed by exactly one `BROWSER_ACTION_COMPLETE` with the same `stepNumber`. Timeouts emit a synthetic COMPLETE with `success=false`.
- **32 KB frame limit**: AgentCore Runtime enforces a 32 KB WebSocket frame-size ceiling. `StarletteWebSocketAdapter.send_json` checks the serialized payload and raises if oversized before the send. Screenshots travel as pre-signed S3 URLs, never as inline bytes, to keep under this limit.
- **REASONING / STREAM ordering**: reasoning chunks and streaming answer tokens are classified by the buffered-data classifier in `BrowserStreamer`. Reasoning is append-only before the final answer starts streaming; the STREAM sequence is a single contiguous run ending with `METADATA`.
- **Session and history persistence**: every user turn and agent response is appended to `SessionRecord.conversation_history` in the configured `SessionStore` (memory / DynamoDB / S3). Resume via `RESUME_SESSION` replays the history before any new frames.
- **Background-task dispatch**: `CHAT_MESSAGE` is dispatched as `asyncio.create_task(_run_chat(...))` so the handler's main loop can continue accepting frames (HITL responses, stop requests) mid-stream without blocking.
- **Session ID format**: `brws_{YYYYMMDD}_{HHMMSS}_{hex8}` generated at session creation. The prefix disambiguates browser sessions from other profile types in shared storage.
- **JWT claim priority**: `user_id` resolves from `oid → sub → uid` claim order. Sanitized to `^[A-Za-z0-9_-]+$` before use as a DynamoDB partition key or S3 prefix segment.

For annotated code snippets and sequence diagrams, see the companion AWS blog post ([published post](TODO: add published blog URL)).

## Source of truth

- Backend constants: `src/models/websocket_message_types.py` — `BrowserMessageType` class carries all 28 frame type strings.
- Frontend mirror: `chat-bot-ui/src/types/browser.types.ts` — discriminated unions + payload interfaces (kept byte-for-byte in sync with the backend names).

When this doc disagrees with the code, the code wins. Open an issue and update the doc.

## Dispatcher / streamer entry points

- `BrowserHandler._dispatch` (`src/handlers/browser_handler.py`) — routes incoming client frames by type to 9 handler methods. `CHAT_MESSAGE` is the only frame that dispatches as a background task so HITL responses can arrive mid-stream.
- `BrowserStreamer._process_event` (`src/streaming/browser_streamer.py`) — maps Strands events to outgoing server frames.
- `HandoffToUserTool.invoke` (`src/tools/handoff_to_user_tool.py`) — emits `BROWSER_HITL_PROMPT` and blocks on `BROWSER_HITL_RESPONSE` via `asyncio.run_coroutine_threadsafe`.

## Adding or changing a frame type

1. Add the constant to `src/models/websocket_message_types.py`.
2. Mirror it into `chat-bot-ui/src/types/browser.types.ts` (add to `BrowserMessageType` object + discriminated union + payload interface).
3. Wire dispatch in `BrowserHandler._dispatch` (if client-bound) or in `BrowserStreamer` / `HandoffToUserTool` (if server-bound).
4. Wire handling in `useBrowserChatSession` (`chat-bot-ui/src/hooks/useBrowserChatSession.ts`) `handleServerMessage` switch.
5. Add unit tests on both sides (`tests/unit/streaming/test_browser_streamer.py` or `tests/unit/handlers/test_browser_handler.py` + `tests/unit/hooks/useBrowserChatSession.test.ts`).
6. Update this doc's frame census and invariants sections above.
