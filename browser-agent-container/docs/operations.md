# Operations — Browser Agent Container

Deployment modes, session storage backends, logging, observability.

## Deployment modes

### AgentCore Runtime (production)

Entry point: `src/agent.py` via `CMD ["opentelemetry-instrument", "python", "agent.py"]` in the Dockerfile.

- Framework: `BedrockAgentCoreApp` with CORS middleware.
- Health: `@app.ping` returns `PingStatus.HEALTHY_BUSY` when `_active_sessions` is non-empty; otherwise `HEALTHY`. This prevents AgentCore from recycling the instance mid-automation.
- Entry: `@app.entrypoint` returns `{"service": "Browser Agent", "version": "1.0.0", "websocket_url": "/ws", "status": "ready"}`.
- WebSocket: `@app.websocket` accepts the connection, extracts JWT user identity, hands off to `BrowserHandler.handle_connection()`.
- Auth: JWT in `Authorization: Bearer <JWT>`. The handler does NOT re-validate signature — AgentCore Runtime does that. The handler only base64-decodes the payload to extract the user identity (`oid` → `sub` → `uid`, sanitized).
- Missing / malformed JWT → WebSocket closed with code 4001.

Deploy:

```bash
# Build and push to ECR
./scripts/docker_build_ecr.sh
./scripts/docker_push_ecr.sh

# Configure Terraform (copy the example if starting fresh)
cp deploy/agentcore/terraform.tfvars.example deploy/agentcore/terraform.tfvars
# Edit image_tag, execution_role_arn, JWT authorizer config, environment_variables map

# Deploy
./scripts/deploy_agentcore.sh
```

Terraform module: `deploy/agentcore/main.tf`.

- Uses the **passthrough map pattern** for env vars: single `map(string)` variable (`environment_variables`) passed directly to the AgentCore Runtime module. Do NOT assemble the map from individual variables in `main.tf`.
- IAM policies under `deploy/agentcore/policies/` (agentcore, bedrock, browser, s3-session, dynamodb-session, cloudwatch, ecr, trust).
- Bedrock policy must include `arn:aws:bedrock:*:*:inference-profile/*` — required because `BA_BROWSER_MODEL_ID` uses the `us.` cross-region inference prefix.
- CloudWatch policy must include `xray:PutTraceSegments` and `xray:PutTelemetryRecords` for OpenTelemetry trace export.

### ECS / container (alternative production)

Entry point: `src/server.py`. Same container image as AgentCore deploy; override the CMD in the ECS task definition:

```json
{
  "containerDefinitions": [
    {
      "name": "browser-agent",
      "image": "${ECR_URL}:${IMAGE_TAG}",
      "command": ["python", "server.py"],
      "portMappings": [{ "containerPort": 8081 }],
      "environment": [
        { "name": "AWS_DEFAULT_REGION", "value": "us-west-2" },
        { "name": "BA_SESSION_STORE_TYPE", "value": "dynamodb" },
        { "name": "BA_SESSION_STORE_TABLE", "value": "browser-sessions" },
        { "name": "BA_SESSION_STORE_BUCKET", "value": "amzn-s3-demo-browser-sessions" }
      ]
    }
  ]
}
```

`server.py` runs plain Starlette on `PORT` (default 8081). `user_id` is hardcoded to `"local"` — ECS deployments typically sit behind another auth layer (the NGINX gateway in this project, which already extracts identity and forwards via Bearer token to AgentCore).

### Local dev

Two sub-modes.

**A. Standalone Starlette**:

```bash
set -a && source .env && set +a
source .venv/bin/activate
PYTHONPATH=src python src/server.py
```

Connect the UI to `ws://localhost:8081/ws?profile=browser`. Direct, no gateway, no TLS.

**B. Against the local gateway**:

```bash
# Terminal 1 — start the container Starlette server
cd browser-agent-container
PYTHONPATH=src python src/server.py

# Terminal 2 — start the gateway with local config
cd ../gateway-container
docker run --rm --name gateway-local \
  -p 8080:80 \
  -v "$(pwd)/nginx/nginx.local.conf:/etc/nginx/nginx.conf:ro" \
  --add-host=host.docker.internal:host-gateway \
  nginx:stable-alpine
```

The gateway's `nginx.local.conf` routes `?profile=browser` to `http://host.docker.internal:8081`. Connect the UI to `ws://localhost:8080/ws?token=<JWT>&profile=browser` to exercise the full NGINX routing / JWT injection / WebSocket upgrade path.

## Session storage backends

Selected by `BA_SESSION_STORE_TYPE`:

| Value | Session metadata | Screenshots | Use case |
|-------|------------------|-------------|----------|
| `memory` (default) | Dict keyed by `(user_id, session_id)` | Local FS at `{BA_SESSIONS_DIR}/{user_id}/{session_id}/screenshots/` | Local dev + integration tests |
| `dynamodb` | DDB table `BA_SESSION_STORE_TABLE` with `pk=user_id`, `sk=session_id`, `item_ttl` for auto-cleanup | S3 at `s3://{BA_SESSION_STORE_BUCKET}/{BA_SESSION_STORE_PREFIX}/{user_id}/{session_id}/screenshots/` | Production — scale + TTL |
| `s3` | `session.json` at `s3://{bucket}/{prefix}/{user_id}/{session_id}/session.json` | Same S3 layout as dynamodb mode | Production (simpler, no DDB) |

Coupling is enforced by `create_session_store` (`src/handlers/session_store.py`) and `create_screenshot_storage` (`src/handlers/screenshot_storage.py`).

Pre-signed screenshot URLs: `BA_SCREENSHOT_URL_EXPIRY_MINUTES` (default 240 = 4 h). Controlled by `BrowserStreamer._generate_presigned_url`. Expired URLs render a graceful "Screenshot no longer available" fallback in the UI.

DynamoDB schema:

- `pk` (S): `user_id` (sanitized)
- `sk` (S): `session_id` (`brws_YYYYMMDD_HHMMSS_hex8`)
- `item_ttl` (N): epoch for auto-cleanup
- `status` (S): `active` | `paused_hitl` | `completed` | `stopped` | `error`
- `conversation_history` (L): list of `{role, content, timestamp}` dicts
- `screenshots`, `steps_completed`, `live_view_url`, `created_at`, `last_activity`

## Logging

- Framework: an internal logging helper with `%s` formatting (never f-strings with logging).
- AgentCore stderr-capture fix: `utils/logging_config.py::configure_agentcore_logging()` redirects the root logger's `StreamHandler` from stderr to stdout and sets noisy loggers (including `playwright`) to WARNING. Called from `agent.py` after all imports.
- Level control: `LOG_LEVEL` env var (default `INFO`).
- Config summary at startup: `ConfigValidator.validate_and_log` prints resolved values for every `BA_` variable (sensitive values containing `SECRET` or `TOKEN` are masked with `***`).

Example startup log:

```
=== Browser Agent Configuration ===
  AWS_DEFAULT_REGION = us-west-2
  BA_BROWSER_MODEL_ID = us.anthropic.claude-sonnet-4-5-20250929-v1:0 (default: us.anthropic.claude-sonnet-4-5-20250929-v1:0)
  BA_SESSION_TIMEOUT = 3600 (default: 3600)
  ...
  BA_SESSION_STORE_TABLE = browser-sessions
  BA_SESSION_STORE_BUCKET = amzn-s3-demo-browser-sessions
===================================
```

## Observability (OpenTelemetry)

The Dockerfile's CMD is `opentelemetry-instrument python agent.py`. `aws-opentelemetry-distro>=0.10.1` exports traces to CloudWatch / X-Ray automatically when the IAM role includes `xray:PutTraceSegments` and `xray:PutTelemetryRecords`.

To disable OTEL logging auto-instrumentation (recommended — it duplicates the application logger):

```hcl
environment_variables = {
  OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = "false"
  # ... other BA_ vars
}
```

## Container build

```bash
./scripts/docker_build_ecr.sh
# Uses BuildKit + build args for private pip registry (SCM_TOKEN_NAME, SCM_TOKEN_SECRET, EXTRA_INDEX_URLS, TRUSTED_HOSTS)
# Tags as browser-agent-container:latest

./scripts/docker_push_ecr.sh
# Authenticates to ECR and pushes
```

Dockerfile highlights:

- Base: `public.ecr.aws/docker/library/python:3.12-slim`.
- Installs Playwright Chromium via `playwright install --with-deps chromium` (takes ~2 min).
- Flattens `src/` into `/app/` so `agent.py` lives at `/app/agent.py` (AgentCore entrypoint discovery).
- Runs as non-root `bedrock_agentcore` user.
- Removes `pip.conf` after dependency installation to avoid leaking private registry credentials.

## Scaling notes

- **One browser microVM per WebSocket connection.** To serve N concurrent users, you need N AgentCore Runtime instances (or ECS tasks). AgentCore auto-scales based on ping results.
- **`HEALTHY_BUSY` keeps an instance alive during long-running automations.** Without this, AgentCore might replace the instance mid-stream.
- **Session-end grace period** (`BA_DISCONNECT_GRACE_SECONDS`, default 30 s) holds the browser microVM for a brief reconnect window. Longer values increase per-session cost; shorter values risk losing in-flight work on flaky networks.
