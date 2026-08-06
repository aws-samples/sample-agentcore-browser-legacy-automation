# Identity Provider Setup — OIDC M2M Configuration

## Overview

The gateway authenticates WebSocket connections using JWT access tokens
passed as query parameters. It is IdP-agnostic — any OAuth2 / OIDC-compliant
provider works. This guide covers machine-to-machine (M2M) integration-test
configuration for Amazon Cognito, Auth0, Okta, and Microsoft Entra ID.

For the user-facing OIDC flow (authorization code + PKCE in the UI), see
the root [`README.md`](../../README.md) § "Switching identity providers".

## Architecture

```text
┌──────────┐   1. client_credentials   ┌──────────┐
│  Client   │ ────────────────────────▶ │  OIDC    │
│  (Test /  │ ◀──────────────────────── │  Provider│
│  UI)      │   2. JWT access_token     └──────────┘
│           │
│           │   3. wss://<alb-dns>/ws?token=<JWT>
│           │ ────────────────────────▶ ┌──────────────┐
└──────────┘                           │  ALB (443)   │
                                       └──────┬───────┘
                                              │ HTTP :80
                                       ┌──────▼───────┐
                                       │  NGINX       │
                                       │  Gateway     │
                                       └──────┬───────┘
                                              │ HTTPS :443
                                       ┌──────▼───────┐
                                       │  AgentCore   │
                                       │  Runtime     │
                                       │  (JWKS       │
                                       │  validation) │
                                       └──────────────┘
```

## Gateway token flow

1. Client obtains a JWT via the OAuth2 `client_credentials` grant from the
   OIDC provider.
2. Client connects: `wss://<alb-dns>/ws?token=<JWT>`.
3. ALB terminates TLS and forwards to NGINX on port 80.
4. NGINX extracts `$arg_token` → `$jwt_token`.
5. If the token is empty, NGINX returns `401 {"error": "Missing token"}`.
6. NGINX sets `Authorization: Bearer $jwt_token` on the upstream request.
7. NGINX proxies to the AgentCore Runtime over HTTPS (port 443).
8. AgentCore validates the JWT via JWKS from the OIDC discovery endpoint.

## Provider setup — test (M2M) clients

### Amazon Cognito (default for the reference architecture)

If you deployed via `deployment/terraform/stacks/all/`, the Cognito User
Pool, hosted-UI domain, SPA app client, resource server, and M2M app client
are already provisioned. Pull the values from Terraform outputs:

| Env var | Terraform output |
|---------|------------------|
| `TEST_OIDC_TOKEN_ENDPOINT` | `m2m_token_endpoint` |
| `TEST_OIDC_CLIENT_ID` | `m2m_app_client_id` |
| `TEST_OIDC_CLIENT_SECRET` | `m2m_app_client_secret` (sensitive) |

For a manual setup:

1. Create a User Pool with a custom domain prefix (e.g.,
   `<your-domain-prefix>`).
2. Resource server — identifier `browser-agent`, scope `invoke`.
3. App client — client secret enabled, `client_credentials` grant, scope
   `browser-agent/invoke`.

Resulting values:

```bash
TEST_OIDC_TOKEN_ENDPOINT=https://<your-domain-prefix>.auth.<region>.amazoncognito.com/oauth2/token
TEST_OIDC_CLIENT_ID=<m2m-app-client-id>
TEST_OIDC_CLIENT_SECRET=<m2m-app-client-secret>
TEST_OIDC_SCOPE=browser-agent/invoke
TEST_OIDC_AUDIENCE=
TEST_OIDC_AUTH_METHOD=client_secret_basic
```

Cognito access tokens carry the client ID as `client_id`, not `aud`. Leave
`TEST_OIDC_AUDIENCE` empty. AgentCore's `jwt_allowed_clients` is set from
the SPA client ID and the M2M client ID, not from `jwt_allowed_audience`.

### Auth0

1. Dashboard → **Applications → APIs → Create API**. Name:
   `browser-agent`, Identifier: `https://browser-agent/invoke`, Signing: RS256.
2. **Applications → Create Application → Machine to Machine**. Authorize
   it for the API above.
3. Note the Domain, Client ID, Client Secret.

Resulting values:

```bash
TEST_OIDC_TOKEN_ENDPOINT=https://<your-tenant>.auth0.com/oauth/token
TEST_OIDC_CLIENT_ID=<m2m-client-id>
TEST_OIDC_CLIENT_SECRET=<m2m-client-secret>
TEST_OIDC_AUDIENCE=https://browser-agent/invoke
TEST_OIDC_SCOPE=
TEST_OIDC_AUTH_METHOD=client_secret_post
```

Auth0 requires an explicit `audience` query parameter to return a JWT
access token (rather than an opaque token). The AgentCore authorizer on
an Auth0-backed runtime uses `jwt_allowed_audience = ["https://browser-agent/invoke"]`.

Auth0 free tier limits M2M tokens to 1,000 / month — sufficient for
integration tests but not high-volume load testing.

### Okta

1. Admin Console → **Security → API → Add Authorization Server**. Name:
   `browser-agent`, Audience: `https://browser-agent/invoke`.
2. On that auth server → **Scopes → Add Scope**. Name: `invoke`.
3. **Access Policies → Add Policy** (assign to all clients) → Add Rule
   with grant type = Client Credentials only, scopes = `invoke`.
4. **Applications → Create App Integration → API Services**. Note Client
   ID and Client Secret. Disable DPoP under **General Settings**.

Resulting values:

```bash
TEST_OIDC_TOKEN_ENDPOINT=https://<your-org>.okta.com/oauth2/<authServerId>/v1/token
TEST_OIDC_CLIENT_ID=<m2m-client-id>
TEST_OIDC_CLIENT_SECRET=<m2m-client-secret>
TEST_OIDC_SCOPE=browser-agent/invoke
TEST_OIDC_AUDIENCE=
TEST_OIDC_AUTH_METHOD=client_secret_basic
```

### Microsoft Entra ID

1. Azure Portal → **Entra ID → App registrations → New registration**.
   Create a client secret under **Certificates & secrets**.
2. **Expose an API → Set Application ID URI** (e.g.,
   `api://browser-agent`). Add scope `invoke` with admin consent.

Resulting values:

```bash
TEST_OIDC_TOKEN_ENDPOINT=https://login.microsoftonline.com/<tenantId>/oauth2/v2.0/token
TEST_OIDC_CLIENT_ID=<app-client-id>
TEST_OIDC_CLIENT_SECRET=<client-secret>
TEST_OIDC_AUDIENCE=
TEST_OIDC_SCOPE=api://browser-agent/.default
TEST_OIDC_AUTH_METHOD=client_secret_post
```

## Terraform inputs by provider

When the AgentCore Runtime module (`bedrock-agentcore-runtime`) is
configured with a non-Cognito IdP, swap these two inputs accordingly:

| Provider | `jwt_discovery_url` | `jwt_allowed_audience` |
|----------|---------------------|------------------------|
| Cognito | `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/openid-configuration` | `[]` (use `jwt_allowed_clients`) |
| Auth0 | `https://<tenant>.auth0.com/.well-known/openid-configuration` | `["https://browser-agent/invoke"]` |
| Okta | `https://<org>.okta.com/oauth2/<authServerId>/.well-known/openid-configuration` | `["https://browser-agent/invoke"]` |
| Entra ID | `https://login.microsoftonline.com/<tenantId>/v2.0/.well-known/openid-configuration` | `["api://browser-agent"]` |

For Cognito, set `jwt_allowed_clients = [<spa-client-id>, <m2m-client-id>]`
because the access token carries the client ID in the `client_id` claim.

## Using the OIDC client helper

`src/oidc_client.py` obtains M2M tokens programmatically:

```python
from oidc_client import get_m2m_token

token = get_m2m_token(
    token_endpoint="https://<your-domain-prefix>.auth.<region>.amazoncognito.com/oauth2/token",
    client_id="<m2m-client-id>",
    client_secret="<m2m-client-secret>",
    scope="browser-agent/invoke",
    audience="",
    auth_method="client_secret_basic",
)
```

## Security considerations

- Store client secrets in AWS Secrets Manager or SSM Parameter Store for
  production. Never commit secrets to source control.
- The gateway log format excludes tokens from access logs. Verify by
  inspecting the `log_format` directive in `nginx/nginx.conf`.
- Use short-lived tokens (1 hour) in production. Integration tests accept
  the default TTL from the IdP.
- The gateway does not validate JWT signatures. AgentCore Runtime
  validates the token against the configured JWKS endpoint.
- Rate limiting (10 req/s per IP with burst 20 in production) guards
  against token brute-force attempts at the gateway. AgentCore has its
  own upstream rate limits.
