# Gateway Container

NGINX reverse proxy that terminates the browser's WebSocket upgrade, pulls a
JWT out of the `?token=` query string, and injects it as
`Authorization: Bearer <JWT>` on the upstream request to an Amazon Bedrock
AgentCore Runtime. It is one piece of the blog reference architecture —
start from the root [`README.md`](../README.md) for the end-to-end story.

## Why does this exist?

The [WebSocket API in browsers does not support custom headers][ws-headers]
on the initial HTTP Upgrade request. `new WebSocket(url)` opens the
connection, and the only ways to carry application state at that point are
the URL itself, the `Sec-WebSocket-Protocol` subprotocol, or cookies. This
is a property of the browser platform, not of any particular backend.

The simplest choice — a query parameter like `?token=<JWT>` — works, but it
has two problems for an enterprise deployment: the token shows up in
server access logs and, depending on referer policy, in browser history.
The standard pattern is to accept the token at a TLS-terminating reverse
proxy, strip it off the request, and translate it into an
`Authorization: Bearer <JWT>` header that the backend sees instead. The
token never reaches the application, and access logs can be scrubbed.

That translation is all this container does. NGINX extracts `$arg_token`,
rejects empty tokens with `401`, and sets the `Authorization` header on the
upstream `proxy_pass` to the AgentCore Runtime. The rest of the config —
SNI, Host header, WebSocket upgrade plumbing, rate limiting, security
headers — is standard reverse-proxy hygiene.

[ws-headers]: https://stackoverflow.com/questions/4361173/http-headers-in-websockets-client-api

## What it is

- NGINX config-driven reverse proxy with an `envsubst` template.
- JWT extraction from `?token=<JWT>` query parameter.
- `Authorization: Bearer <JWT>` injection on the upstream request.
- Single profile (`browser`). The `?profile=` map is retained as a default
  pass-through so a future profile can be wired in by adding map entries
  without touching the `location` blocks.
- Rate limiting — 10 req/s per IP with burst 20 (prod); 100 r/s in the
  local config for quick iteration.
- Security headers — `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`.
- Health check — `/health` returns `{"status": "ok"}`.
- IdP-agnostic M2M helper — `src/oidc_client.py` fetches `client_credentials`
  grant tokens from any OAuth2-compliant provider (Cognito, Auth0, Okta,
  Entra ID) for integration tests.

## Architecture

```text
Client (Browser / UI)
    │  wss://<alb-dns>/ws?token=<JWT>&profile=browser
    ▼
┌──────────┐     ┌────────────────────────┐     ┌──────────────────────────┐
│   ALB    │────▶│ NGINX Gateway (port 80)│────▶│ AgentCore Runtime (HTTPS)│
│  (TLS    │     │  · JWT extract          │     │  BROWSER_AGENT_ARN       │
│  term)   │     │  · Auth header inject   │     │  (managed microVM)       │
└──────────┘     │  · SNI + Host header    │     └──────────────────────────┘
                 │  · Rate limit           │
                 │  · Security headers     │
                 └─────────────────────────┘
```

The ALB terminates TLS and forwards plain HTTP to the container on port 80.
The container then re-establishes TLS to the AgentCore edge with
`proxy_ssl_server_name on` and `proxy_ssl_name $backend_host`, which is
required because AgentCore uses SNI-based routing and certificate selection
on its multi-tenant edge.

## WebSocket proxy flow

```text
Client                         NGINX /ws                         AgentCore Runtime
  │                               │                                     │
  │ wss://.../ws?token=<JWT>      │                                     │
  │──────────────────────────────▶│                                     │
  │                               │ set $jwt_token $arg_token           │
  │                               │ if empty → 401 {"error":"Missing"}  │
  │                               │ proxy_pass                          │
  │                               │   https://browser_worker/runtimes/  │
  │                               │     $BROWSER_AGENT_ARN/ws           │
  │                               │ proxy_set_header Upgrade …          │
  │                               │ proxy_set_header Connection upgrade │
  │                               │ proxy_set_header Authorization      │
  │                               │   "Bearer $jwt_token"               │
  │                               │ proxy_ssl_server_name on            │
  │                               │ proxy_ssl_name $backend_host        │
  │                               │ Host: $backend_host                 │
  │                               │────────────────────────────────────▶│
  │                               │                                     │
  │◀──────────── bidirectional WebSocket frames ─────────────────────── │
```

Key NGINX settings:

- `proxy_read_timeout 3600s; proxy_send_timeout 3600s` — long-lived WebSocket
  sessions survive through a one-hour browser task.
- `proxy_connect_timeout 60s` — initial upstream connect.
- `proxy_buffering off` — required for streaming WebSocket frames.

The `$backend_upstream`, `$backend_arn`, and `$backend_host` maps currently
have a single entry (`browser`). They are kept as one-branch maps instead
of inlined literals because the template reads more naturally to someone
who has seen multi-profile NGINX configs — and adding a second backend
later is a matter of one map entry + one `upstream` block.

## Environment variables

Validated at startup by `nginx/entrypoint.sh`:

| Variable | Purpose |
|----------|---------|
| `BROWSER_AGENTCORE_ENDPOINT` | AgentCore hostname, e.g. `bedrock-agentcore.<region>.amazonaws.com` |
| `BROWSER_AGENT_ARN` | URL-encoded AgentCore Runtime ARN |

The entrypoint runs `envsubst` against `nginx.conf`, then `nginx -t` to
validate, then `exec "$@"` to hand control to NGINX.

## For blog readers

If you deployed through the root Terraform stack, you have nothing
container-specific to do. The five steps are:

1. `cd deployment/terraform/stacks/all && terraform apply` — provisions
   Cognito, ECR repos, ECS, the ALB, and the AgentCore Runtime.
2. The Terraform stack builds and pushes this container's image to ECR as
   part of the apply.
3. The ECS Fargate service launches the container with
   `BROWSER_AGENTCORE_ENDPOINT` and `BROWSER_AGENT_ARN` wired from the
   Terraform outputs.
4. Point `chat-bot-ui` at `wss://<alb-dns>/ws?token=<JWT>` — the UI's
   `__WEBSOCKET_URL__` build-time value.
5. No manual gateway configuration is needed. Sign in to the UI and send a
   `CHAT_MESSAGE`.

See the root [`README.md`](../README.md) for the full quickstart.

## Quick start (iterating on this container)

Two modes are supported.

### Standalone Docker against a deployed AgentCore Runtime

```bash
cd gateway-container
./scripts/docker_build_ecr.sh

docker run --rm -p 8080:80 \
  -e BROWSER_AGENTCORE_ENDPOINT=<agentcore-host> \
  -e BROWSER_AGENT_ARN=<url-encoded-arn> \
  gateway-container
```

Connect the UI to `ws://localhost:8080/ws?token=<JWT>`.

### Local dev against a local browser-agent-container

Use `nginx/nginx.local.conf`, a non-`envsubst` config that routes
`/ws` to `host.docker.internal:8081` over plain HTTP. No ARN, no TLS.

```bash
# Terminal 1 — start the browser-agent Starlette server
cd browser-agent-container
PYTHONPATH=src python src/server.py

# Terminal 2 — start NGINX with the local config
cd gateway-container
docker run --rm --name gateway-local \
  -p 8080:80 \
  -v "$(pwd)/nginx/nginx.local.conf:/etc/nginx/nginx.conf:ro" \
  --add-host=host.docker.internal:host-gateway \
  nginx:stable-alpine
```

`--add-host=host.docker.internal:host-gateway` resolves to the Docker host
from inside the container on macOS, Windows, and Docker Desktop on Linux.
The browser-agent Starlette server listens on port `8081`.

A VS Code task `gateway:docker:run-local` encapsulates this invocation.

### Production build

```bash
cd gateway-container
./scripts/docker_build_ecr.sh
./scripts/docker_push_ecr.sh
```

The root Terraform stack handles the production build + push during
`terraform apply` — these scripts are here for when you want to iterate on
the image outside the stack.

## Extending

- **Multi-tenant routing** — restore the multi-branch `map $arg_profile
  $backend_*` pattern in `nginx/nginx.conf`, one branch per tenant, and add
  a corresponding `upstream` block.
- **Per-tenant auth headers** — modify the
  `proxy_set_header Authorization "Bearer $jwt_token"` directive to select
  a header / prefix based on `$arg_profile` (or any other request variable)
  via an additional `map`.
- **Second backend** — add a new `upstream` block, extend the three
  `map $arg_profile $backend_*` tables with a new branch, and point a new
  `location` block (or reuse `/ws`) at it.

The `location` blocks are intentionally small so these extensions are
additive rather than rewrites.

## How it fits into the single-apply Terraform stack

The root stack at
[`deployment/terraform/stacks/all/`](../deployment/terraform/stacks/all/)
deploys this container as an ECS Fargate service behind an ALB with an
ACM-terminated TLS certificate. Readers deploying the full stack do not
need to touch anything in this directory — the image is built and pushed
from the stack and the task definition is generated there.

Readers who want to deploy this container in isolation use
[`deploy/main.tf`](./deploy/main.tf), which sources the `ecs-fargate`
module from `../../deployment/terraform/modules/ecs-fargate` (retargeted in
Phase 3 of the reference-architecture spec). The two paths share the same
module, so the deployed resource shape is identical.

## Testing

```bash
# Unit tests — NGINX config validation
PYTHONPATH=src python -m pytest tests/unit/ -v

# Integration tests — requires a deployed gateway + Cognito M2M credentials
PYTHONPATH=src python -m pytest tests/integration/ -v
```

The integration tests are skipped automatically when
`TEST_GATEWAY_WS_URL` is unset. The environment matrix for Cognito:

| Variable | Value |
|----------|-------|
| `TEST_GATEWAY_WS_URL` | `wss://<alb-dns>/ws` |
| `TEST_GATEWAY_HEALTH_URL` | `https://<alb-dns>/health` |
| `TEST_OIDC_TOKEN_ENDPOINT` | `<cognito-domain>/oauth2/token` |
| `TEST_OIDC_CLIENT_ID` | M2M app client ID (Terraform output) |
| `TEST_OIDC_CLIENT_SECRET` | M2M app client secret (Terraform output, sensitive) |
| `TEST_OIDC_SCOPE` | `browser-agent/invoke` |
| `TEST_OIDC_AUDIENCE` | empty (Cognito access tokens carry `client_id`, not `aud`) |
| `TEST_OIDC_AUTH_METHOD` | `client_secret_basic` |

The same file drives Auth0, Okta, and Entra ID by flipping those values —
see [`tests/integration/README.md`](./tests/integration/README.md) and
[`tests/integration/.env.sample`](./tests/integration/.env.sample).

## Project structure

```text
gateway-container/
├── nginx/
│   ├── nginx.conf            # Production envsubst template (single profile)
│   ├── nginx.local.conf      # Local dev — routes to host.docker.internal:8081
│   ├── entrypoint.sh         # Validates 2 env vars, expands template, nginx -t, exec
│   └── ssl/                  # Local-dev SSL certs (git-ignored)
├── deploy/
│   ├── main.tf, variables.tf, outputs.tf
│   ├── terraform.tfvars.sample
│   ├── create-ecr-repository.sh
│   └── create-security-groups.sh
├── src/
│   └── oidc_client.py        # Generic OIDC M2M token helper (integration tests)
├── tests/
│   ├── unit/                 # test_nginx_config.py — validates envsubst expansion
│   └── integration/          # test_nginx_proxy.py — end-to-end proxy test
│       └── .env.sample       # Cognito-flavored placeholders (copy to .env.dev)
├── scripts/
│   ├── docker_build_ecr.sh, docker_push_ecr.sh
│   ├── docker_run.sh, deploy_ecs.sh
│   └── generate_ssl.sh       # Self-signed SSL for local HTTPS (optional)
├── docs/
│   └── identity-provider-setup.md
├── Dockerfile
├── pyproject.toml, requirements*.txt
└── README.md                 # ← you are here
```

## Troubleshooting

### `401 {"error": "Missing token"}`

The `?token=` query parameter is empty. The UI must include the OIDC access
token — verify `auth.user?.access_token` is populated at the point where
the WebSocket opens.

### Upstream unreachable (HTTP 502 / 504)

Check that `BROWSER_AGENTCORE_ENDPOINT` and `BROWSER_AGENT_ARN` are set
correctly and that the AgentCore Runtime is reachable. The ARN must be
URL-encoded (e.g., `arn%3Aaws%3Abedrock-agentcore%3A...`).

### 503 Service Unavailable on WebSocket upgrade

Symptom: `/health` returns 200 but `GET /ws?token=…` returns
`503 Service Temporarily Unavailable`. The access log shows
`upstream=<ip>:443`, so NGINX resolved DNS and opened a TCP connection, but
the TLS handshake never completed. The default `error_log warn` level does
not surface TLS peer-reset events.

Root cause: `proxy_ssl_server_name` is **off by default** in NGINX. When
proxying to the AgentCore multi-tenant HTTPS edge
(`bedrock-agentcore.<region>.amazonaws.com`), the upstream uses
SNI-based routing and certificate selection. Without SNI, the edge either
returns a 503 or serves a certificate that does not match the intended
tenant, and the handshake is torn down. The same mistake can be made at
the application layer by forwarding the ALB hostname in the `Host` header
(via `$host`) instead of the real AgentCore hostname — AgentCore's
virtual-host routing will then return 503.

Fix (already applied in `nginx.conf`):

```nginx
map $arg_profile $backend_host {
    default    ${BROWSER_AGENTCORE_ENDPOINT};
    "browser"  ${BROWSER_AGENTCORE_ENDPOINT};
}

location /ws {
    # ...
    proxy_pass https://$backend_upstream/runtimes/$backend_arn/ws;
    proxy_ssl_server_name on;
    proxy_ssl_name $backend_host;
    proxy_set_header Host $backend_host;
    # ...
}
```

Regression guard: `tests/unit/test_nginx_config.py::TestTlsSni` covers the
`$backend_host` map, both SNI directives on `/ws` and `/api/`, and a
negative check that forbids `proxy_set_header Host $host`.

### WebSocket drops after ~15 s

This is a symptom of the upstream agent, not the gateway. Check the
container logs for the browser-agent backend — see
[`../browser-agent-container/docs/troubleshooting.md`](../browser-agent-container/docs/troubleshooting.md).

### 32 KB frame-limit interactions

The AgentCore Runtime enforces a **32 KB WebSocket frame size** limit that
is not adjustable. Exceeding it causes the relay to terminate the
connection without a close frame. The gateway does **not** enforce this
limit — it forwards frames as-is. Enforcement happens inside the backend
container (`StarletteWebSocketAdapter.send_json`). If you see AgentCore-side
connection drops with no close frame, inspect the backend container logs
for oversized-frame warnings.

### Rate limit 429

The production rate limit is 10 req/s per IP with burst 20. For heavy
testing, use `nginx.local.conf` (100 r/s) or adjust the
`limit_req_zone … rate=Nr/s` value in `nginx.conf`.

### OIDC integration test 401 / invalid token

`src/oidc_client.py` supports two auth methods — `client_secret_post`
(credentials in body) and `client_secret_basic` (HTTP Basic header).
Different IdPs default to different methods:

- Amazon Cognito, Okta → `client_secret_basic`
- Auth0, Microsoft Entra ID → `client_secret_post`

Set `TEST_OIDC_AUTH_METHOD` accordingly.

## Related

- Root onboarding: [`../README.md`](../README.md)
- Browser agent backend: [`../browser-agent-container/README.md`](../browser-agent-container/README.md)
- IdP setup guide: [`docs/identity-provider-setup.md`](./docs/identity-provider-setup.md)
- Cross-project reference: [`../.kiro/research/agentcore-browser-tool-reference.md`](../.kiro/research/agentcore-browser-tool-reference.md)

License: see the repository-root `LICENSE` (MIT-0).
