# Browser Agent Container

Browser automation backend built on Strands Agents + Playwright + Amazon Bedrock AgentCore Browser Tool. Takes natural-language instructions, drives a managed Chrome microVM, streams typed WebSocket frames (reasoning, action progress, screenshots, HITL prompts) to the chat UI, and persists sessions + screenshots to S3 or DynamoDB.

This is one of three components in the reference architecture that accompanies the AWS blog post ([published post](TODO: add published blog URL)). Start from the root [`README.md`](../README.md) for the end-to-end deploy. The WebSocket protocol wire reference is at [`docs/protocol.md`](./docs/protocol.md).

## For blog readers

This container is one of three components in the reference architecture that accompanies the AWS blog post. It runs on Amazon Bedrock AgentCore Runtime and handles the reasoning + browser-automation loop. The consolidated deploy lives at [`../deployment/terraform/stacks/all/`](../deployment/terraform/stacks/all/) — start there if you want the full solution end-to-end. The root [README](../README.md) has the 5-step quickstart.

If you already ran `terraform apply` from the root stack, the container image was pushed to ECR and the AgentCore Runtime was created for you. The steps below are only needed if you want to iterate on this container in isolation.

1. `cd browser-agent-container && python3.12 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements-test.txt && playwright install chromium`
3. `cp .env.example .env` — fill in `BA_SESSION_STORE_BUCKET` (from the Terraform outputs) if you want the `s3` session backend, or flip `BA_SESSION_STORE_TYPE=memory` for no-AWS local dev.
4. `set -a && source .env && set +a && PYTHONPATH=src python src/server.py` — exposes `ws://localhost:8081/ws`.
5. Point `chat-bot-ui` at that URL (`WEBSOCKET_URL=ws://localhost:8081` in `chat-bot-ui/.env.dev`), `yarn start-dev`, sign in, send a `CHAT_MESSAGE`.

### Customizing the system prompt

The agent's system prompt lives in [`src/prompts/browser_system_prompt.py`](./src/prompts/browser_system_prompt.py). Edit the module-level `SYSTEM_PROMPT` constant, re-run the unit tests (`PYTHONPATH=src python -m pytest tests/unit/`), rebuild the container, redeploy. No schema changes downstream — the prompt is a plain string consumed by the `StrandsAgent` constructor. Keep it focused on browser-automation guidance; the tool selection, HITL semantics, and WebSocket frame mapping are all in code, not prompt.

## What it is

- **Language / runtime**: Python 3.12, class-based, complete type hints.
- **Framework**: [Strands Agents](https://strandsagents.com) with a custom `VisualBrowserTool` composing four tools (`browser`, `screenshot_for_vision`, `semantic_action`, `accessibility_snapshot`) plus a WebSocket-backed `handoff_to_user` for human-in-the-loop.
- **Model**: Claude Sonnet 4.5 via Bedrock cross-region inference profile (`us.` prefix — `BA_BROWSER_MODEL_ID` default `us.anthropic.claude-sonnet-4-5-20250929-v1:0`).
- **Env prefix**: `BA_` (**B**rowser **A**gent). Distinct from the concierge container's `SA_` prefix.
- **Two deployment modes**: AgentCore Runtime (production, `src/agent.py`) and plain Starlette + uvicorn (ECS / local dev, `src/server.py`). Both share the same container image — the target decides which entry point runs.
- **Version**: see `pyproject.toml`.

## Top-level architecture

```
UI ─┐
    │ wss://gateway/ws?token=JWT
    ▼
TLS-terminating WebSocket proxy (gateway-container)
    │ Authorization: Bearer <JWT>
    ▼
BrowserHandler (src/handlers/browser_handler.py)
    │ dispatches CHAT_MESSAGE as a background asyncio.Task
    │ so HITL responses arrive mid-stream
    ▼
BrowserStreamer (src/streaming/browser_streamer.py)
    │ maps Strands events → typed WebSocket frames
    │ buffers "data" chunks → classifies as REASONING vs STREAM
    ▼
VisualBrowserTool (src/tools/visual_browser_tool.py)
    │ navigate · semantic_action · accessibility_snapshot · screenshot_for_vision · handoff_to_user
    ▼
AgentCore Browser Tool (separate managed microVM)
    │ Chrome via Playwright CDP
    ▼
Target web application
```

See [`docs/architecture.md`](./docs/architecture.md) for the full class diagram, request lifecycle, and HITL threading model.

## Quick start

Three ways to run it.

### 1. Local (ECS-mode entry point)

```bash
cd browser-agent-container
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
playwright install chromium

# Validate env + AWS credentials
set -a && source .env && set +a

# Run the Starlette dev server
PYTHONPATH=src python src/server.py
# Listens on ws://localhost:8081/ws
```

### 2. Local Docker

```bash
./scripts/docker_build_ecr.sh
docker run --rm \
  -p 8081:8081 \
  --env-file .env \
  browser-agent-container
```

### 3. AgentCore Runtime deploy

```bash
# Build + push to ECR
./scripts/docker_build_ecr.sh
./scripts/docker_push_ecr.sh

# Deploy via Terraform
./scripts/deploy_agentcore.sh
# Expands deploy/agentcore/main.tf; JWT authorizer settings come from deploy/agentcore/terraform.tfvars
```

See [`docs/operations.md`](./docs/operations.md) for the full deployment walkthrough.

## Environment variables (cheat sheet)

Required: `AWS_DEFAULT_REGION`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `BA_BROWSER_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock model. **Must** use `us.` cross-region inference prefix for AgentCore |
| `BA_SESSION_TIMEOUT` | `3600` | AgentCore browser microVM TTL (seconds) |
| `BA_SESSIONS_DIR` | `sessions` | Local FS root for memory-mode screenshots |
| `BA_MAX_STEPS_PER_SESSION` | `100` | Step budget per session (hard circuit breaker) |
| `BA_DISCONNECT_GRACE_SECONDS` | `30` | Grace period before browser session teardown on disconnect |
| `BA_HITL_TIMEOUT_SECONDS` | `300` | `handoff_to_user` response timeout |
| `BA_SCREENSHOT_URL_EXPIRY_MINUTES` | `240` | Pre-signed S3 URL lifetime (4 h) |
| `BA_SESSION_STORE_TYPE` | `memory` | One of `memory`, `dynamodb`, `s3` |
| `BA_SESSION_STORE_PREFIX` | `browser-sessions` | S3 prefix |
| `BA_SESSION_STORE_TABLE` | — | **Required** when `BA_SESSION_STORE_TYPE=dynamodb` |
| `BA_SESSION_STORE_BUCKET` | — | **Required** when `BA_SESSION_STORE_TYPE=dynamodb` or `s3` |
| `LOG_LEVEL` | `INFO` | Python logging level |

`ConfigValidator.validate_and_log` (`src/utils/config_validator.py`) runs at startup — missing required values or invalid numeric/store-type values abort before the WebSocket accepts connections.

## Testing

```bash
# Unit tests (492 passing as of 2026-05-03)
cd browser-agent-container && \
  set -a && source .env && set +a && \
  source .venv/bin/activate && \
  PYTHONPATH=src python -m pytest tests/unit/ -v \
    > /tmp/test_output.log 2> /tmp/test_errors.log

# Specific suite
PYTHONPATH=src python -m pytest tests/unit/streaming/test_browser_streamer.py -v

# Property-based tests (colocated _pbt.py files)
PYTHONPATH=src python -m pytest tests/unit -k "_pbt" -v

# Integration — direct agent (5 scenarios): Wikipedia, form fill, Amazon, Gap, nested popups
PYTHONPATH=src python -m pytest tests/integration/test_browser_agent.py -v

# Integration — local protocol (StubWebSocket) + deployed (real WebSocket)
PYTHONPATH=src python -m pytest tests/integration/test_agent_local.py -v
PYTHONPATH=src python -m pytest tests/integration/test_agent_deployed.py -v
```

Integration tests require AWS credentials + Bedrock model access + AgentCore Browser permissions. Deployed tests additionally require `TEST_AGENTCORE_WS_URL` and OIDC M2M credentials in `tests/integration/.env.dev`.

See [`docs/development.md`](./docs/development.md) for the dev-container setup, devtools, and pytest/PBT patterns.

## Project structure

```
browser-agent-container/
├── src/
│   ├── agent.py                      # AgentCore Runtime entry point (@app.websocket, @app.ping, @app.entrypoint)
│   ├── server.py                     # Starlette + uvicorn entry point (ECS / local dev)
│   ├── agents/browser_agent.py       # BrowserAgentFactory
│   ├── handlers/
│   │   ├── browser_handler.py        # WebSocket dispatcher, session lifecycle, HITL bridge
│   │   ├── browser_streamer.py       # (actually under streaming/) — see below
│   │   ├── session_store.py          # Pluggable: memory / dynamodb / s3
│   │   ├── screenshot_storage.py     # Pluggable: local / s3
│   │   └── starlette_websocket_adapter.py  # 32 KB frame guardrail
│   ├── streaming/browser_streamer.py # Strands event → WebSocket frame mapping
│   ├── models/websocket_message_types.py   # 28-frame protocol constants
│   ├── prompts/browser_system_prompt.py    # Claude system prompt (with Response Style section)
│   ├── tools/
│   │   ├── visual_browser_tool.py    # Composes all four tools + popup auto-registration
│   │   ├── screenshot_tool.py        # Persists bytes via ScreenshotStorageBase
│   │   ├── semantic_action_tool.py   # Playwright Locator API
│   │   ├── accessibility_tool.py     # AXTree snapshot via CDP
│   │   ├── handoff_to_user_tool.py   # WebSocket-backed HITL (NOT the Strands built-in)
│   │   └── models.py                 # SemanticActionInput Pydantic model
│   └── utils/
│       ├── config_validator.py       # BA_ env-var validation
│       └── logging_config.py         # AgentCore stderr→stdout fix
├── tests/
│   ├── unit/                         # Mirrors src/ subdirs; 492 tests (@ 2026-05-01)
│   └── integration/                  # Direct-agent + local protocol + deployed (real WebSocket)
├── deploy/agentcore/                 # Terraform module + IAM policies
├── scripts/                          # docker_build_ecr.sh, deploy_agentcore.sh, smoke tests
├── docs/                             # Detailed documentation (see below)
├── Dockerfile
├── pyproject.toml, requirements*.txt, pytest.ini, conftest.py, .pylintrc
└── README.md                         # ← you are here
```

## Documentation index

- [`docs/architecture.md`](./docs/architecture.md) — class diagrams, request lifecycle, HITL threading model, buffered-data classifier.
- [`docs/protocol.md`](./docs/protocol.md) — WebSocket protocol wire reference (pointer into the consolidated cross-project reference).
- [`docs/operations.md`](./docs/operations.md) — deployment modes, session storage backends, logging, OpenTelemetry observability.
- [`docs/development.md`](./docs/development.md) — devcontainer setup, running against real AWS vs memory mode, adding a new tool, debugging tips, pytest/PBT patterns.
- [`docs/troubleshooting.md`](./docs/troubleshooting.md) — HITL timeout, screenshot 403, disconnect grace period, event-loop warnings, common errors.

## Extending

- **Customizing the agent system prompt** — edit [`src/prompts/browser_system_prompt.py`](./src/prompts/browser_system_prompt.py). It's a plain Python string consumed by the Strands `Agent` constructor; no downstream schema or parser depends on its shape. Rerun `pytest tests/unit/` after any edit, rebuild the container, redeploy.
- **Swapping the session store** — set `BA_SESSION_STORE_TYPE` to `memory`, `dynamodb`, or `s3`. For `dynamodb` set `BA_SESSION_STORE_TABLE`; for `s3` set `BA_SESSION_STORE_BUCKET`. `ConfigValidator` fails startup if required values are missing. Source of truth is [`src/handlers/session_store.py`](./src/handlers/session_store.py) — the `SessionStoreBase` ABC has three implementations and a single factory (`get_session_store`).
- **Adding a new WebSocket frame type** — add the constant to [`src/models/websocket_message_types.py`](./src/models/websocket_message_types.py), wire dispatch in `BrowserHandler._dispatch` (client-bound) or `BrowserStreamer` / `HandoffToUserTool` (server-bound), and mirror the type in [`../chat-bot-ui/src/types/browser.types.ts`](../chat-bot-ui/src/types/browser.types.ts). Add tests on both sides.
- **Adding a new tool to the agent** — implement the tool as a class under [`src/tools/`](./src/tools/), compose it onto `VisualBrowserTool.__init__`, and register it in `BrowserAgentFactory.create_agent()`'s `tools=[...]` list. Follow the pattern of `screenshot_tool.py` for storage-backed tools or `handoff_to_user_tool.py` for WebSocket-backed tools.
- **Plugging in AgentCore Memory** — the current `SessionStore` handles single-session durability. To add cross-session recall, wire an `AgentCoreMemoryClient` into the `Agent` constructor (Strands supports a `memory` kwarg) and replace the per-turn transcript append in `BrowserStreamer` with a memory write. See the "Extending the solution" section of the [published blog post](TODO: add published blog URL) for context.

## Related

- **Root onboarding**: [`../README.md`](../README.md)
- **Blog post**: [published post](TODO: add published blog URL)
- **WebSocket protocol reference**: [`./docs/protocol.md`](./docs/protocol.md)
- **UI consumer**: [`../chat-bot-ui/README.md`](../chat-bot-ui/README.md)
- **Gateway**: [`../gateway-container/README.md`](../gateway-container/README.md)

License: see the repository-root `LICENSE` (MIT-0).
