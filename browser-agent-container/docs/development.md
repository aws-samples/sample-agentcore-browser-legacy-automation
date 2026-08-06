# Development — Browser Agent Container

Dev environment, running modes, adding a new tool, debugging tips, pytest + PBT patterns.

## Dev environment

### VS Code / devcontainer

`.vscode/settings.json` is already configured with:
- Python interpreter `.venv/bin/python`
- `python.analysis.extraPaths` = `["${workspaceFolder}/src"]` so imports like `from handlers.browser_handler import ...` resolve without setting `PYTHONPATH`.
- Pylint rcfile: `.pylintrc`.
- Pytest enabled pointing at `tests`.

`.vscode/launch.json` provides:
- **Python: Current File** — run the open file with `PYTHONPATH=src`.
- **Python: AgentCore Server** — run `src/agent.py` with `BA_` env vars loaded.
- **Python: Starlette Server** — run `src/server.py` on port 8081.
- **Python: Unit Tests** — pytest on `tests/unit/`.
- **Python: Integration Tests** — pytest on `tests/integration/` with AWS env loaded.

### Virtualenv setup

```bash
cd browser-agent-container
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
playwright install chromium
```

`requirements-test.txt` pulls in `requirements.txt` plus test extras (pytest, pytest-asyncio, hypothesis, pylint).

### Private package registry

If you use a private pip index (for example a corporate internal PyPI), the Dockerfile accepts build args:

```bash
docker build \
  --build-arg SCM_TOKEN_NAME=my-token \
  --build-arg SCM_TOKEN_SECRET=<secret> \
  --build-arg EXTRA_INDEX_URLS=https://my.registry/simple/ \
  --build-arg TRUSTED_HOSTS=my.registry \
  -t browser-agent-container .
```

For local iteration, `scripts/setup_pip.sh` writes a `pip.conf` with the same values.

## Running modes

| Mode | Command | Use case |
|------|---------|----------|
| Standalone Starlette | `PYTHONPATH=src python src/server.py` | Fast iteration on handler / streamer logic |
| AgentCore local | `PYTHONPATH=src python src/agent.py` | Run the BedrockAgentCoreApp locally; verify ping / entrypoint behaviour |
| Against local gateway | `server.py` + `docker run ... nginx.local.conf` (see `docs/operations.md`) | Full NGINX routing / JWT / WebSocket upgrade flow |
| Against real AgentCore Browser | `server.py` with `BA_SESSION_STORE_TYPE=memory` | Real browser microVM, in-memory session state — no DDB / S3 round-trips |

## Memory mode vs real AWS

- **Memory mode** (`BA_SESSION_STORE_TYPE=memory`): session state lives in a dict; screenshots written to `{BA_SESSIONS_DIR}/…`. No AWS session-store dependencies — only Bedrock + AgentCore Browser.
- **Real AWS mode** (`BA_SESSION_STORE_TYPE=dynamodb|s3`): add `BA_SESSION_STORE_TABLE` and/or `BA_SESSION_STORE_BUCKET` to `.env`. DynamoDB mode is closer to production but adds DDB IAM + table setup overhead. S3 mode is often sufficient for dev.

Minimum IAM for dev:
- `bedrock-agentcore:*` on the browser resource (for Browser Tool).
- `bedrock:InvokeModel*` on `arn:aws:bedrock:*:*:inference-profile/*` and `arn:aws:bedrock:*::foundation-model/*` (required for `us.` cross-region profile).
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the session store bucket.
- `dynamodb:*Item`, `dynamodb:Query` on the session store table (DDB mode).

## Adding a new browser tool

1. Create the tool class under `src/tools/your_tool.py`. Keep it thin — delegate to `VisualBrowserTool` for Playwright session access via `validate_session`, `get_session_page`, `_execute_async`.
2. If the tool accepts structured input, add a Pydantic model under `src/tools/models.py`. Prefer flat schemas — Claude struggles with deeply nested Pydantic wrappers (see `SemanticActionInput` + `_SEMANTIC_ACTION_SCHEMA` override in `visual_browser_tool.py` for the pattern).
3. Register as a `@tool`-decorated method on `VisualBrowserTool`. Delegate to the tool instance:
   ```python
   @tool
   def your_tool(self, session_name: str, ...) -> Dict[str, Any]:
       return self._your_tool.execute(...)
   ```
4. Add the tool to the agent factory (`src/agents/browser_agent.py::create_agent`) — pass it to `Agent(tools=[...])`.
5. Update the system prompt (`src/prompts/browser_system_prompt.py`) to tell Claude when to use your tool.
6. If the tool result should map to a dedicated WebSocket frame (like `screenshot_for_vision` → `BROWSER_SCREENSHOT`), extend the routing in `BrowserStreamer._handle_tool_result`. Otherwise it flows through the default `BROWSER_ACTION_COMPLETE` path.
7. Unit tests: mock `browser_tool.validate_session`, `get_session_page`, `_execute_async`. Place under `tests/unit/tools/test_your_tool.py`.
8. Property tests: `tests/unit/tools/test_your_tool_pbt.py` — check input-space invariants with Hypothesis at `@settings(max_examples=100)`.
9. Integration test: add a scenario to `tests/integration/test_browser_agent.py` that exercises the tool end-to-end against real AgentCore Browser.

## Debugging tips

### WebSocket frame traffic

The UI's hook logs frames under `__DEV_MODE__` (set by webpack in dev builds). On the backend, set `LOG_LEVEL=DEBUG` and watch for `Dispatching message:` and `send_json` log lines.

### Screenshot not rendering

Trace through:

1. `BrowserStreamer._handle_tool_use` — did `current_tool_use` fire for `screenshot_for_vision`? Check `step_counter` in the emitted `BROWSER_ACTION_START`.
2. `BrowserStreamer._handle_tool_result` — did the `message` event carry a `toolResult` for the matching `toolUseId`? The `Screenshot saved: s3://...` marker must appear in the result text.
3. `BrowserStreamer._send_screenshot_frame` — was `_generate_presigned_url` called with a valid `s3://` path? Check CloudWatch for `Failed to generate pre-signed URL` warnings.
4. UI side: `useBrowserChatSession` `BROWSER_SCREENSHOT` handler appends to `msg.screenshots`. `browserSteps.ts::groupMessageIntoSteps` then pairs by `stepNumber`. Check the browser devtools for the frame arrival and the grouping state.

### HITL response not arriving

The most common cause before the Issue 5 fix was that `CHAT_MESSAGE` ran inline, blocking the main loop. That fix is in place — the current dispatch spawns `_run_chat_message_task`. If HITL still appears stuck:

1. Confirm `_dispatch` is spawning a task: `Dispatching message: type=BROWSER_HITL_RESPONSE` should land while `automation_in_progress` is `True`.
2. Confirm `_handle_hitl_response` fires: look for `HITL response received: session=... prompt_id=...`.
3. Confirm `hitl_event.set()` unblocks `wait_for_hitl_response`: look for a matching log line after the handler returns.
4. Confirm `HandoffToUserTool.invoke` resumes: look for `HITL response received: prompt_id=... action=... len=...` from the tool's log.

### AgentCore WebSocket dropping after ~15 s

The likely cause is `nest_asyncio.apply()` being called against the main Uvicorn loop. This is why `VisualBrowserTool._execute_async` overrides the base `Browser._execute_async` to skip `nest_asyncio.apply()`. If you ever see this symptom after upgrading `strands-tools`, verify the override still applies.

### Event-loop context warnings during shutdown

`WARNING:asyncio:...attached to a different loop` during session termination is harmless — the browser's private event loop is shutting down while cleanup tasks finish. The messages are suppressed at WARNING by `logging_config.py::configure_agentcore_logging()`.

## Pytest / PBT patterns

### Test structure

Unit tests mirror `src/` subdirectories:

```
tests/
├── __init__.py, __setup__.py
├── unit/
│   ├── __init__.py, __setup__.py
│   ├── test_agent.py                 # src/agent.py (top-level)
│   ├── test_agent_pbt.py             # property tests for agent.py
│   ├── test_server.py                # src/server.py
│   ├── test_imageblock_pbt.py
│   ├── test_setup_path_pbt.py
│   ├── agents/       # mirrors src/agents/
│   ├── handlers/     # mirrors src/handlers/
│   ├── models/       # mirrors src/models/
│   ├── prompts/
│   ├── streaming/
│   ├── tools/
│   └── utils/
└── integration/
    ├── __init__.py, __setup__.py
    ├── test_browser_agent.py         # direct-agent scenarios (real AgentCore)
    ├── test_agent_local.py           # protocol-level via StubWebSocket
    └── test_agent_deployed.py        # real WebSocket against deployed AgentCore
```

Each `__setup__.py` adds `src/` to `sys.path` with the correct relative depth (1 up for `tests/`, 2 up for `tests/unit/`, 3 up for `tests/unit/<subdir>/`).

### Property-based tests

Colocated `_pbt.py` files alongside their unit test counterparts. Convention:

```python
# Feature: 86-browser-agent-container-deployment, Property 1: Session ID format
from hypothesis import given, settings, strategies as st

@given(...)
@settings(max_examples=100)
def test_generated_session_ids_match_regex(...):
    ...
```

Tag every property with its feature + number so `pytest -k "_pbt"` surfaces the lot.

### Mocking AWS

Use `unittest.mock.patch` on the store's boto3 client:

```python
with patch.object(store, '_client') as mock_s3:
    mock_s3.put_object.return_value = {}
    await store.create(user_id, record)
    mock_s3.put_object.assert_called_once()
```

For `DynamoDBSessionStore`, the table is a `boto3.resource('dynamodb').Table(...)` — mock `self._table` directly.

### StubWebSocket for protocol tests

`tests/integration/test_agent_local.py` uses a `StubWebSocket` that captures all outgoing frames into a `messages: List[dict]` list. Drive the handler directly:

```python
ws = StubWebSocket()
handler = BrowserHandler(ws, factory, store, screenshot_storage, profile='browser', user_id='test')
await handler._handle_chat_message({'content': 'Go to wikipedia.org'})
frames = frames_of_type(ws.messages, BrowserMessageType.BROWSER_SCREENSHOT)
assert frames, "Expected at least one screenshot frame"
```

This is faster than spinning up a real WebSocket and keeps the test assertions focused on the protocol contract.
