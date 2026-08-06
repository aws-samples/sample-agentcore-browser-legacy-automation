# Architecture — Browser Agent Container

Deep-dive on class relationships, request lifecycle, event loop, and HITL threading. For the cross-project protocol and the UI side, see [`../../../.kiro/research/agentcore-browser-tool-reference.md`](../../../.kiro/research/agentcore-browser-tool-reference.md).

## Class / component relationships

```
                                ┌──────────────────────────────┐
                                │ agent.py (BedrockAgentCoreApp)│   server.py (Starlette)
                                │  @app.websocket              │    WebSocketRoute("/ws")
                                │  @app.ping → HEALTHY_BUSY    │
                                │  @app.entrypoint             │
                                └────────────┬─────────────────┘
                                             │
                                             ▼ StarletteWebSocket
                                ┌─────────────────────────────────────────┐
                                │ StarletteWebSocketAdapter                │
                                │  · 32 KB frame guardrail                 │
                                │  · send_json / send / recv / close       │
                                │  · __aiter__ over incoming text frames   │
                                └────────────┬─────────────────────────────┘
                                             │
                                             ▼
                                ┌─────────────────────────────────────────────────────┐
                                │ BrowserHandler (main event loop)                    │
                                │  · handle_connection → async for raw_message in ws  │
                                │  · _dispatch ─┬─► CHAT_MESSAGE: asyncio.create_task │
                                │               │                    └─► _run_chat_message_task
                                │               │                             └─► _handle_chat_message
                                │               │                                    └─► BrowserStreamer.stream_events
                                │               ├─► NEW_SESSION / RESUME_SESSION / GET_SESSIONS / DELETE_SESSION
                                │               ├─► BROWSER_STOP / BROWSER_HITL_RESPONSE / BROWSER_LIVE_VIEW_REQUEST
                                │               └─► CONNECTION_INIT (no-op; handshake already sent)
                                │  · wait_for_hitl_response (asyncio.Event + timeout)  │
                                │  · _handle_disconnect (grace period + task cancel)   │
                                └────────┬────────────────────────────────────┬───────┘
                                         │                                    │
                                         ▼                                    ▼
                                ┌────────────────────────┐      ┌─────────────────────────┐
                                │ SessionStoreBase        │      │ ScreenshotStorageBase    │
                                │  · InMemorySessionStore │      │  · LocalScreenshotStorage│
                                │  · DynamoDBSessionStore │      │  · S3ScreenshotStorage   │
                                │  · S3SessionStore       │      │                          │
                                └────────────────────────┘      └─────────────────────────┘

                                         │                                    │
                                         └───────────┬────────────────────────┘
                                                     ▼
                                ┌───────────────────────────────────────────────────────┐
                                │ BrowserStreamer (per CHAT_MESSAGE turn)               │
                                │  · stream_events(agent, query)                        │
                                │  · _process_event routes by Strands event key:        │
                                │    · current_tool_use → BROWSER_ACTION_START          │
                                │    · reasoningText    → REASONING (thinking-budget)   │
                                │    · data             → buffer; classified on message │
                                │    · message (assistant, toolUse)  → REASONING (flush)│
                                │    · message (assistant, text-only)→ STREAM (flush)   │
                                │    · message (toolResult)          → SCREENSHOT + COMPLETE
                                │    · result (AgentResult)          → final_assistant_text capture
                                │  · _finalize → METADATA + ORCHESTRATION_END           │
                                └─────────────────────┬─────────────────────────────────┘
                                                      │
                                                      ▼
                                ┌─────────────────────────────────────────────────────────┐
                                │ VisualBrowserTool(AgentCoreBrowser)                     │
                                │  · _execute_async — skips nest_asyncio.apply()          │
                                │  · create_browser_session — stores BrowserClient in dict│
                                │  · _setup_session_from_browser — context.on("page")     │
                                │  · Composes:                                             │
                                │    ┌─ ScreenshotTool     (persists via ScreenshotStorage)│
                                │    ├─ SemanticActionTool (Playwright Locator API)        │
                                │    ├─ AccessibilityTool  (CDP Accessibility.getFullAXTree)│
                                │    └─ HandoffToUserTool  (WebSocket-backed HITL)         │
                                └─────────────────────────────────────────────────────────┘
```

## Request lifecycle (typical chat)

### Connect phase

1. Client opens WebSocket at `wss://gateway/ws?token=JWT&profile=browser`.
2. Gateway (NGINX) extracts the JWT from the query param, injects `Authorization: Bearer <JWT>` and `X-Profile-Id: browser`, proxies to AgentCore Runtime.
3. `agent.py::websocket_handler` accepts the WS, extracts `user_id` via `_extract_user_id_from_jwt` (priority: `oid` → `sub` → `uid`, sanitized for DDB/S3 key safety). Constructs `BrowserHandler` with the shared `SessionStore` + `ScreenshotStorage` + `BrowserAgentFactory` (all created once in `lifespan`).
4. `handler.handle_connection()` enters `async for raw_message in self.ws`.
5. Client sends `CONNECTION_INIT`.
6. Handler sends `CONNECTION_ESTABLISHED { session_id, profile }` (deferred until the first client frame because AgentCore's WS proxy only starts relaying container frames after the client speaks).
7. `CONNECTION_INIT` handler is a no-op.

### Chat phase

1. Client sends `CHAT_MESSAGE { content }`.
2. `_dispatch` synchronously rejects a second concurrent chat (sets `automation_in_progress = True` atomically to prevent races), then spawns `asyncio.create_task(_run_chat_message_task(payload))`.
3. **Main receive loop stays free** — this is the Issue 5 fix that lets `BROWSER_HITL_RESPONSE` arrive mid-stream.
4. Chat task calls `BrowserAgentFactory.create_agent()` — creates a fresh `VisualBrowserTool`, which initializes `ScreenshotTool`, `SemanticActionTool`, `AccessibilityTool`, `HandoffToUserTool`.
5. Wires context: `ScreenshotTool.set_context(user_id, session_id, screenshot_storage)` so screenshots land at `{user_id}/{session_id}/screenshots/…`; `HandoffToUserTool.set_hitl_context(ws, wait_for_response)` captures the current running event loop.
6. Initializes the AgentCore browser microVM (via `VisualBrowserTool.create_browser_session`); generates the live-view URL via `BrowserClient.generate_live_view_url()`.
7. Persists a `SessionRecord { user_id, session_id, browser_session_id, status='active', live_view_url, conversation_history=[] }`.
8. Appends the user turn to `conversation_history`.
9. Emits `BROWSER_SESSION_STARTED { session_id, liveViewUrl }` and `ORCHESTRATION_START`.
10. Instantiates `BrowserStreamer` and calls `stream_events(agent, content)`.

### Streaming phase (inside `BrowserStreamer`)

Per Strands event (see `_process_event` in `src/streaming/browser_streamer.py`):

- `current_tool_use` → increments `step_counter`, records pending tool name/input/use_id, emits `BROWSER_ACTION_START`.
- `reasoningText` → emits `REASONING` directly (extended-thinking-enabled models only).
- `data` → appended to `_data_buffer`. Does NOT emit immediately — classification waits for the enclosing `message` event.
- `message` (role=assistant):
  - `_capture_final_text_from_message` — if no `toolUse` blocks and content is text-only, set `final_assistant_text` (running best-guess).
  - `_classify_buffered_data_for_message` — inspect content blocks:
    - Contains `toolUse` → flush `_data_buffer` as `REASONING`.
    - Text-only → flush `_data_buffer` as `STREAM`, latch `_reached_final_answer = True`.
  - `_handle_tool_result` — if this message carries a `toolResult` block for the pending tool:
    - `screenshot_for_vision` → `BROWSER_SCREENSHOT` (pre-signed S3 URL) + `BROWSER_ACTION_COMPLETE`.
    - Other browser tools → `BROWSER_ACTION_COMPLETE`.
- `result` → terminal `AgentResult`. `_capture_final_text_from_result` overwrites `final_assistant_text` with the authoritative value.

After `agent.stream_async(query)` exits:
- Residual `_data_buffer` is flushed as `STREAM` (safety net).
- `_finalize` emits `METADATA { total_duration_ms, steps_completed }` and `ORCHESTRATION_END`.

### Persist phase

1. `_handle_chat_message` reads `streamer.final_assistant_text`, appends an assistant turn to `conversation_history`, writes back to the store. Empty text still persists (balances user/assistant counts).
2. `finally` block clears `automation_in_progress`.

### Disconnect phase

1. Client closes, `async for raw_message in self.ws` raises → loop exits.
2. `_await_chat_task` waits for any in-flight chat task to finish (swallows `CancelledError` and final exceptions).
3. `_handle_disconnect`:
   - If HITL is pending, sets `hitl_event` to unblock the waiter with `None`.
   - Cancels the in-flight chat task so it stops trying to send frames to a closed socket.
   - Schedules `_grace_period` as a background task: `asyncio.sleep(BA_DISCONNECT_GRACE_SECONDS)` then `_terminate_browser_session("completed")`.

## HITL threading model

HITL (`handoff_to_user`) runs on a tool worker thread but must bridge back to the handler's main event loop to send/receive WebSocket frames. This is the core mechanic:

```
Main event loop                  Tool worker thread (asyncio.to_thread)
─────────────────                ────────────────────────────────────────
Handler._handle_chat_message
 └─ stream_events()
     └─ agent.stream_async()
          ├─ HandoffToUserTool.set_hitl_context(ws, wait_for_response)
          │    └─ captures loop = get_running_loop()
          │
          │◄── Strands dispatches handoff_to_user via asyncio.to_thread
          │
          │                         HandoffToUserTool.invoke(message)
          │                          │
          │◄─ run_coroutine_threadsafe(ws.send_json(HITL_PROMPT))
          │    send_future.result(timeout=10)
          │  [main loop sends frame]
          │                          │
          │                          │ (worker thread blocks on next step)
          │                          │
          │◄─ run_coroutine_threadsafe(wait_for_response(timeout=300))
          │    wait_future.result(timeout=330)
          │  [main loop coroutine awaits hitl_event]
          │                          │
          │                          │ (worker blocked)
BROWSER_HITL_RESPONSE arrives via main receive loop
 └─ _dispatch → _handle_hitl_response
     └─ self.hitl_response = payload
     └─ self.hitl_event.set()
 [hitl_event.wait() unblocks]
  returns payload
                                    │ (worker thread wakes up)
                                    │ wait_future resolves with payload
                                    │
                                    │ return {"status": "success",
                                    │         "content": [{"text": "User response: ..."}]}
                                    │◄─ Strands continues tool loop
          │
          │◄── next event: message/toolResult/etc.
          │
```

Key points:

- **The main loop is free to read `BROWSER_HITL_RESPONSE` while the worker thread is blocked** — this is only true because `CHAT_MESSAGE` runs in `_run_chat_message_task`, not inline in `_dispatch`.
- **`asyncio.run_coroutine_threadsafe` is the bridge** — it submits the coroutine to the main loop and returns a `concurrent.futures.Future` the worker can block on.
- **Timeouts have concentric rings**: handler timeout (`BA_HITL_TIMEOUT_SECONDS`, 300 s default) inside `asyncio.wait_for(hitl_event.wait())`, worker-thread timeout (`timeout_seconds + 30`) on `wait_future.result`. Handler timeout always wins; worker timeout is just a defense against a stuck main loop.
- **On session end**, `BrowserHandler._terminate_browser_session` calls `_handoff_tool.clear_hitl_context()` to drop the captured loop + ws references so a subsequent session reusing the connection doesn't see stale state.

## Buffered-data classifier (Issue 3 fix)

Strands does not distinguish pre-tool narration from final-answer text at the `data` event level for models without extended thinking. The assistant `message` event is the structural boundary that classifies the preceding `data` chunks.

```
    data ──┐
    data ──┼───► _data_buffer = ["chunk1", "chunk2", ...]
    data ──┘
                                                 ▼
    message (role=assistant,                     inspect content blocks
             content=[{text}, {toolUse}]) ─────► has toolUse? ──Yes──► flush buffer as REASONING
                                                                │
                                                                No ──► flush as STREAM
                                                                       + latch _reached_final_answer
                                                                       + subsequent `data` chunks dispatch as STREAM directly
```

Once `_reached_final_answer` latches, the buffer is empty by construction and any trailing `data` chunk dispatches directly as `STREAM`. A safety drain in `stream_events` flushes any residual buffer as `STREAM` before `_finalize` — covers runs that never produced a terminal text-only message.

## Session resume semantics

`RESUME_SESSION` loads `conversation_history` from the store and emits `SESSION_RESUMED`. It does **not** resurrect the ephemeral AgentCore Browser microVM — each automation session runs in a fresh microVM. The UI shows only user/assistant text bubbles for resumed turns; screenshots, action progress, and live-view URLs don't replay. See [`../../../.kiro/research/agentcore-browser-tool-reference.md`](../../../.kiro/research/agentcore-browser-tool-reference.md) §10.2.

## Popup handling

`VisualBrowserTool._setup_session_from_browser` registers a `context.on("page")` listener. When a page calls `window.open()` or a link has `target="_blank"`, Playwright creates a new `Page` in the same `BrowserContext`. The listener auto-registers each new page as a `popup_N` tab in the `BrowserSession`; `add_tab` switches `active_tab_id` to the popup so all tools (semantic_action, accessibility_snapshot, screenshot_for_vision) immediately target it.

`new_page.on("close")` auto-removes the tab when the popup closes itself (`window.close()`). The active tab falls back to the first remaining tab — typically `main`, not the nearest parent popup. Claude handles the mismatch via `browser(switch_tab)` explicitly.
