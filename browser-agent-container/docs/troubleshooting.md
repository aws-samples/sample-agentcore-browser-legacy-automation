# Troubleshooting — Browser Agent Container

Common failure modes, symptoms, and fixes.

## WebSocket connection drops after ~15 s (AgentCore)

**Symptom**: `ConnectionClosedError: no close frame received or sent` in container logs soon after the first tool call.

**Cause**: Some upstream `strands_tools.browser.Browser._execute_async` implementation called `nest_asyncio.apply()`, which patches `asyncio.BaseEventLoop` at the **class level** — corrupting Uvicorn's main event loop.

**Fix**: `VisualBrowserTool._execute_async` in `src/tools/visual_browser_tool.py` overrides the base method to skip the `nest_asyncio.apply()` call. Strands dispatches tool calls via `asyncio.to_thread`, so the browser's private loop can use `run_until_complete` without nesting. If you upgrade `strands-tools` and this symptom returns, verify the override still applies to the new base class.

## Screenshot frame blocked / connection dropping after a screenshot

**Symptom**: `BLOCKED oversized WebSocket frame: type=BROWSER_SCREENSHOT size=... bytes (...), limit=32768 bytes (32 KB). Frame not sent — connection preserved.` in container logs. The UI sees an `ERROR` frame instead of the screenshot.

**Cause**: A screenshot was sent as inline base64 instead of a pre-signed URL, exceeding the 32 KB AgentCore WebSocket frame limit.

**Fix**: The `BrowserStreamer._send_screenshot_frame` path is correct as of issue #86 — it sends `screenshotPath` + `screenshotUrl` (pre-signed S3 GET URL). If this warning fires:

1. Check that `ScreenshotTool.set_context(user_id, session_id, storage)` is called before the first screenshot — the storage backend must be wired for the persistence step to return an `s3://...` path.
2. Check that `create_screenshot_storage(BA_SESSION_STORE_TYPE)` returned `S3ScreenshotStorage` (for `dynamodb` / `s3` store types). `LocalScreenshotStorage` (memory mode) returns a local filesystem path that cannot be pre-signed — memory mode only works with the UI side fetching the image via a different mechanism. Memory mode is dev-only.
3. The guardrail in `StarletteWebSocketAdapter.send_json` is doing its job — the frame was blocked and the connection preserved. Fix the upstream sending path rather than disabling the guardrail.

## `Screenshot no longer available` placeholder in UI

**Symptom**: The UI shows a grey placeholder instead of a screenshot.

**Cause**: Pre-signed URL expired. Default lifetime is 4 h (`BA_SCREENSHOT_URL_EXPIRY_MINUTES=240`). Users revisiting a session after 4 h see the fallback.

**Fix**: Not a bug — intentional graceful degradation. There is no refresh endpoint; the UI's `<img onError>` handler swaps to the placeholder and does not retry. For longer-lived URLs, bump `BA_SCREENSHOT_URL_EXPIRY_MINUTES` (max is capped by S3 at `604800` minutes = 7 days with SigV4).

## HITL prompt times out (no response received)

**Symptom**: `HITL timeout: session=... timeout=300.0s` in container logs. UI sees `BROWSER_HITL_TIMEOUT` frame.

**Possible causes**:

1. **User genuinely didn't respond** within `BA_HITL_TIMEOUT_SECONDS` (default 300 s). Expected behaviour — the agent receives a timeout error string and decides whether to retry or give up.
2. **UI didn't dispatch `BROWSER_HITL_RESPONSE`**. Open browser devtools, send the response, watch for a `BROWSER_HITL_RESPONSE` frame in the WS traffic. If absent, the UI's `pendingHitl` state or `sendMessage` wiring is broken.
3. **Pre-Issue-5 regression**: `CHAT_MESSAGE` running inline instead of as a background task would queue the response until the chat body returned. The current `BrowserHandler._dispatch` spawns `asyncio.create_task(_run_chat_message_task(...))` — verify this hasn't been undone.

## `Failed to create browser session` on first `CHAT_MESSAGE`

**Symptom**: Client receives `ERROR: Failed to create browser session: ...` immediately after sending the first `CHAT_MESSAGE`.

**Possible causes**:

1. **IAM missing** `bedrock-agentcore:*` permissions on `arn:aws:bedrock-agentcore:*:*:browser/*`. Check the execution role.
2. **AgentCore Browser not available** in the deployed region. Verify `AWS_DEFAULT_REGION` is one of the supported regions (see AWS docs).
3. **Quota exceeded** — check the CloudWatch metrics for `BrowserSessionsAvailable`.

## `Chat task crashed` in container logs

**Symptom**: `Chat task crashed: session=... error=...` log line after a `CHAT_MESSAGE`.

**Cause**: An unexpected exception escaped `_handle_chat_message`. The `_run_chat_message_task` wrapper catches it, clears `automation_in_progress`, and sends an `ERROR` frame so the UI can recover.

**Diagnosis**:

1. The full traceback should be in the surrounding logs (`Streaming error: session=... error=...`) or the logged exception detail.
2. Common causes: Bedrock throttling (ThrottlingException), IAM issues, network blip to AgentCore Browser, Claude returning a malformed tool use.
3. Retry the chat — the handler cleared state and is ready for the next `CHAT_MESSAGE`.

## Disconnect grace-period noise in logs

**Symptom**: `WebSocket disconnected, starting grace period: session=... seconds=30` followed by `Grace period expired, terminating: session=...` 30 s later.

**Expected**. `BA_DISCONNECT_GRACE_SECONDS` holds the browser microVM for a brief reconnect window. Tune if too long or short for your use case.

## Event-loop context warnings during shutdown

**Symptom**: `WARNING:asyncio: ... attached to a different loop` during session termination or test teardown.

**Cause**: The browser's private event loop (created by `Browser.__init__`) is shutting down while cleanup coroutines finish on the handler's main loop. The two loops briefly cross-reference each other during `_cleanup`.

**Mitigation**: Already suppressed at WARNING by `logging_config.py::configure_agentcore_logging()`. If you see these in tests, they don't indicate a real problem — the cleanup completes successfully.

## `Invalid JSON message` ERROR frame

**Symptom**: Client receives `ERROR: Invalid JSON message`.

**Cause**: A raw WebSocket frame was not valid JSON. The handler's `handle_connection` catches `json.JSONDecodeError` and sends an `ERROR`. The UI's `useBrowserChatSession` should never produce invalid JSON — check a custom client or inspect the frame with a WebSocket debugger.

## `Unknown message type: ...` ERROR frame

**Symptom**: `ERROR: Unknown message type: SOMETHING`.

**Cause**: The client sent a frame whose `type` is not in `BrowserHandler._dispatch`'s routing table. Likely a frontend-backend version skew.

**Fix**: Verify the backend `BrowserMessageType` constants and frontend `browser.types.ts` are in sync. If you recently added a new frame type, check both files and the `_dispatch` handler map.

## JWT extraction failure — WebSocket closed 4001

**Symptom**: UI sees the WebSocket close with code 4001 immediately. Container logs show `JWT user extraction failed: ...`.

**Cause**: `_extract_user_id_from_jwt` (`src/agent.py`) could not decode the JWT payload or found no `oid` / `sub` / `uid` claim.

**Fix**: Verify the IdP is issuing a real JWT (not an opaque token). Auth0 users: enable the "User Access" toggle so tokens carry `sub`. Check the token payload at [jwt.io](https://jwt.io) — it must have at least one of `oid`, `sub`, `uid`.

## `Automation in progress` ERROR on a second CHAT_MESSAGE

**Symptom**: `ERROR: Automation in progress` when sending a chat while a previous chat is still streaming.

**Expected**. Concurrent chats on the same WebSocket connection are rejected synchronously in `_dispatch`. Wait for `ORCHESTRATION_END` before sending the next message, or open a new WebSocket connection for a parallel chat.

## Session resume shows only user messages, no assistant responses

**Symptom**: After `RESUME_SESSION`, the UI shows only `{role: 'user'}` entries; assistant bubbles missing.

**Cause**: Pre-Issue-4 bug — assistant turns were not persisted to `conversation_history`. Fixed: the handler now reads `streamer.final_assistant_text` after `stream_events` returns and appends an `{role: 'assistant', content, timestamp}` entry.

**Diagnosis**: If you still see this after deploying the fix:

1. Check the session in the store directly — DDB `GetItem` or `aws s3 cp s3://.../session.json -` and inspect the `conversation_history` array. If it only has user entries, the container isn't running the fix.
2. Check container logs for `Chat task crashed` or `Streaming error` — errors during streaming skip the assistant-turn append (intentional — matches concierge-agent-container behavior).

## Where to file issues

- Protocol contract issues (frame types, payloads): open an issue on this repository and reference `docs/protocol.md`.
- Strands / AgentCore SDK bugs: reproduce against the vanilla `strands_tools.browser.Browser` class to isolate from our overrides, then report upstream.
- Playwright-specific weirdness: include a minimal Playwright-only repro (no Strands) before filing.
