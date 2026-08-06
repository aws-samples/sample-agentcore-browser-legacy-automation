# Multi-IdP Smoke Test Procedure

The `chat-bot-ui` is **IdP-agnostic** — authentication is wired through
[`react-oidc-context`](https://github.com/authts/react-oidc-context) and
[`oidc-client-ts`](https://github.com/authts/oidc-client-ts), both of which
operate purely off the OIDC discovery document. No IdP-specific branches
exist in the source tree.

The integration suite in this directory covers the frame protocol
(`frameCoverage.test.ts`) and the end-to-end chat lifecycle
(`browserChatLifecycle.test.ts`) against a `MockWebSocket` harness. What it
cannot cover is the browser-level OAuth redirect dance — that requires a
live IdP. Before shipping the reference architecture we manually verify the
UI against the three IdPs we advertise support for: Amazon Cognito,
Auth0, and Okta. This document is that procedure.

## Prerequisites

- A running `chat-bot-ui` dev server started with `yarn start-dev` (serves
  at `http://localhost:3000`), **or** a deployed CloudFront distribution
  from the Phase 3 single-apply stack.
- A running `browser-agent-container` — either locally via
  `docker run` / `python -m src.server` on port `8081`, or deployed via
  the Phase 3 Terraform stack as an AgentCore runtime.
- **Optional:** a running `gateway-container` if you want to exercise the
  NGINX TLS proxy path. Not required for the dev-server smoke test.

For each IdP, set the following four DefinePlugin variables in your
`.env.dev` (read by `webpack.config.js`) before `yarn start-dev`:

```bash
OIDC_AUTHORITY=<issuer URL from the IdP>
OIDC_CLIENT_ID=<SPA client ID>
OIDC_AUDIENCE=<API audience — leave empty for Cognito/Okta>
OIDC_SCOPE="openid profile email"
WEBSOCKET_URL=ws://localhost:8081
```

The UI round-trip you are verifying is always the same:

1. Navigate to `http://localhost:3000`.
2. `ProtectedRoute` redirects to `/login`.
3. Click **Sign In** — the browser redirects to the IdP's authorize endpoint.
4. Complete the IdP login form.
5. The IdP redirects to `http://localhost:3000/callback` with an
   authorization code; `react-oidc-context` exchanges it for an access token.
6. `AppShell` mounts. The chat surface is usable.
7. Send a simple prompt like `What is the current date on example.com?`.
8. Observe a `BROWSER_SCREENSHOT` thumbnail attach to the assistant
   message and a final answer stream in.
9. Click the user avatar → **Sign Out**. The UI redirects via the IdP's
   `end_session_endpoint` and lands back at `/login`.

## 1. Amazon Cognito

### Obtain the `__OIDC_*__` values

From the Phase 3 Terraform outputs (root `README.md` lists the output
names), copy:

- `cognito_user_pool_issuer` → `OIDC_AUTHORITY`
  (looks like `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`)
- `cognito_spa_client_id` → `OIDC_CLIENT_ID`

Leave `OIDC_AUDIENCE` empty. Cognito embeds the client ID into the JWT's
`client_id` claim and the browser-agent container validates that directly;
no explicit `audience` parameter is needed.

### Register the callback URL

In the Cognito Console → User Pools → your pool → **App integration**
tab → your app client → **Hosted UI** → **Allowed callback URLs**,
append:

- `http://localhost:3000/callback` for local dev.
- `https://<cloudfront-distribution>/callback` for the deployed UI.

Under **Allowed sign-out URLs**, append the corresponding `/login` paths.

Under **OAuth 2.0 grant types**, enable **Authorization code grant**.
Under **OpenID Connect scopes**, enable `openid`, `profile`, `email`.

### Round-trip

Follow the nine-step round-trip above. A successful Cognito sign-in lands
you on the app shell with the username visible in the sidebar footer.

### Troubleshooting

- **"Invalid client_id"** — the SPA client ID in `OIDC_CLIENT_ID` does
  not match the Cognito app client. Double-check the Terraform output.
- **Redirect loop at `/callback`** — the callback URL is not listed in
  Cognito's allowed callback URLs, or the `redirect_uri` in the token
  exchange does not match exactly (trailing slash counts).
- **Final answer never streams in** — WebSocket authentication is
  failing. Check the browser console for a `1008` close code. Confirm
  `cognito_user_pool_issuer` is the **issuer** URL (no trailing path)
  and that the browser-agent container was configured with the same
  issuer on its `BA_OIDC_AUTHORITY` env var.

## 2. Auth0

### Obtain the `__OIDC_*__` values

1. Log in to the [Auth0 Dashboard](https://manage.auth0.com/).
2. Note your tenant domain — e.g. `dev-xyz.us.auth0.com`. This is your
   `OIDC_AUTHORITY` **prefixed with `https://` and with a trailing slash**:
   `https://dev-xyz.us.auth0.com/`.
3. **Applications → Create Application** →
   **Single Page Web Applications** → name it `browser-agent-ui`.
4. Copy the **Client ID** into `OIDC_CLIENT_ID`.
5. **APIs → Create API** → name it `browser-agent` → set **Identifier**
   (e.g. `https://browser-agent/api`) → **RS256** signing. Copy this
   identifier into `OIDC_AUDIENCE`. Auth0 requires an explicit
   `audience` query parameter to return a **JWT access token** instead
   of an opaque token — without it, the browser-agent container cannot
   validate the token.

### Register the callback URL

In the Auth0 SPA application settings:

- **Allowed Callback URLs**: `http://localhost:3000/callback,
  https://<cloudfront-distribution>/callback`
- **Allowed Logout URLs**: `http://localhost:3000/login,
  https://<cloudfront-distribution>/login`
- **Allowed Web Origins**: `http://localhost:3000,
  https://<cloudfront-distribution>`

### Round-trip

Follow the nine-step round-trip above. Auth0 presents its Universal
Login screen; complete sign-in. On success, the `access_token` carried
by the SPA is a JWT whose `aud` matches your `OIDC_AUDIENCE`.

### Troubleshooting

- **Opaque token / "invalid JWT" error from the browser-agent** —
  `OIDC_AUDIENCE` is not set or does not match the API identifier.
  Auth0 returns an opaque access token when no `audience` is requested;
  the browser-agent container expects a signed JWT.
- **"Callback URL mismatch"** — the URL the SPA is redirecting to
  (including port and protocol) is not listed in **Allowed Callback URLs**.
- **Sign-out leaves you authenticated on subsequent refresh** — the
  Logout URL is not in **Allowed Logout URLs**. Auth0 rejects the
  `end_session_endpoint` request and does not clear its SSO cookie.

## 3. Okta

### Obtain the `__OIDC_*__` values

1. Log in to the [Okta Admin Console](https://login.okta.com/).
2. Note your Okta domain — e.g. `dev-12345678.okta.com`. This is your
   `OIDC_AUTHORITY`: `https://dev-12345678.okta.com/oauth2/default`.
   (The `/oauth2/default` path is the default authorization server
   issuer. Custom authorization servers live at `/oauth2/<server-id>`.)
3. **Applications → Create App Integration** →
   **OIDC - OpenID Connect** → **Single-Page Application** → name it
   `browser-agent-ui`.
4. Copy the **Client ID** into `OIDC_CLIENT_ID`.
5. Leave `OIDC_AUDIENCE` empty. Okta's default authorization server
   signs access tokens as JWTs whose `aud` is `api://default` by default;
   the browser-agent container validates this based on the issuer only.
   (If you run a custom authorization server with a non-default
   audience, set `OIDC_AUDIENCE` accordingly.)

### Register the callback URL

In the Okta app **General Settings**:

- **Sign-in redirect URIs**:
  `http://localhost:3000/callback,
  https://<cloudfront-distribution>/callback`
- **Sign-out redirect URIs**:
  `http://localhost:3000/login,
  https://<cloudfront-distribution>/login`

Under **Assignments**, assign the application to the user(s) you plan to
sign in as. Okta denies authorize requests for unassigned users.

### Round-trip

Follow the nine-step round-trip above. Okta presents its sign-in widget;
complete sign-in with an assigned user.

### Troubleshooting

- **"Unauthorized" at the authorize endpoint** — the signed-in user is
  not assigned to the Okta application. Add the user under
  **Assignments** and retry.
- **`aud` mismatch when the browser-agent validates the token** — you
  are using a custom authorization server and `OIDC_AUDIENCE` is not
  set to match. Either set it explicitly or switch to the default
  authorization server at `/oauth2/default`.
- **Browser console shows a `403` fetching the discovery document** —
  some Okta tenants disable the default authorization server. Enable
  it under **Security → API → Authorization Servers → default**, or
  use a custom authorization server and update the `OIDC_AUTHORITY`
  path segment to match.

## Appendix: What a successful round-trip looks like

On successful sign-in, in order:

1. **Login screen** (`/login`): the `<Login />` component renders with
   platform branding and a single **Sign In** button.
2. **IdP redirect**: browser navigates to the IdP's authorize endpoint
   with `client_id`, `redirect_uri`, `code` response type, `scope`, and
   (for Auth0) the `audience` query parameter.
3. **IdP login form**: you complete the IdP's login form. The IdP
   redirects back to `http://localhost:3000/callback?code=...`.
4. **Token exchange**: `react-oidc-context` exchanges the code for an
   access token + id token (PKCE, no client secret).
5. **App shell** (`/`): `<ProtectedRoute />` detects `isAuthenticated`,
   renders `<AppShell />`. The sidebar footer shows the signed-in user's
   email or name.
6. **Chat**: the WebSocket to the browser-agent container opens with the
   access token on the query string. The backend's JWT validator accepts
   the token (issuer + audience match). `CONNECTION_ESTABLISHED` arrives
   within a second.
7. **Prompt**: typing a prompt and hitting Enter dispatches a
   `CHAT_MESSAGE` frame. The backend responds with `ORCHESTRATION_START`,
   `BROWSER_SESSION_STARTED`, and a stream of `BROWSER_ACTION_START` /
   `BROWSER_SCREENSHOT` / `BROWSER_ACTION_COMPLETE` frames. The UI
   renders a `<ReasoningTrace>` with one step card per action.
8. **Final answer**: `STREAM` frames arrive token-by-token; the final
   answer renders into a `<FinalAnswer>` card below the trace.
9. **Sign out**: the sidebar footer **Sign Out** action calls
   `signoutRedirect()`, which sends the browser to the IdP's
   `end_session_endpoint` and back to `/login`.

If any of those nine steps breaks, the troubleshooting section for the
relevant IdP is the first place to check.
