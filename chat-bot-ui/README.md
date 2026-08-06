# Chat Bot UI

Single-profile React SPA for the blog reference architecture. Surfaces the
browser-agent conversation flow — reasoning trace, inline screenshots,
human-in-the-loop prompts, and an optional DCV live-view panel — on top of
the 28-frame WebSocket protocol shipped by `browser-agent-container`.

This is one of three components in the reference architecture that accompanies
the AWS blog post ([published post](TODO: add published blog URL)). Start from the
root [`README.md`](../README.md) for the end-to-end deploy.

## For blog readers

If you deployed through the root Terraform stack, the UI is already built
and hosted on CloudFront. The steps below are only needed if you want to
iterate on the UI in isolation.

1. `cd chat-bot-ui && yarn install`
2. `cp .env.example .env.dev` and fill in `WEBSOCKET_URL`, `OIDC_AUTHORITY`,
   `OIDC_CLIENT_ID`, `OIDC_SCOPE` (leave `OIDC_AUDIENCE` empty for Cognito).
   For local iteration, point `WEBSOCKET_URL=ws://localhost:8081`.
3. `yarn start-dev` — starts Webpack DevServer on `http://localhost:3000/`.
4. Start a local `browser-agent-container` (see
   [`../browser-agent-container/README.md`](../browser-agent-container/README.md)
   § For blog readers).
5. Sign in through the configured IdP, send a `CHAT_MESSAGE`. The reasoning
   trace and screenshots stream in; a final answer card renders at the end.

## What it is

- **React 18 + TypeScript 5 + MUI 6** — functional components, hooks, React
  Context. No Redux. No class components.
- **Webpack 5** build with `DefinePlugin` for compile-time configuration
  (`__WEBSOCKET_URL__`, `__OIDC_AUTHORITY__`, `__OIDC_CLIENT_ID__`,
  `__OIDC_AUDIENCE__`, `__OIDC_SCOPE__`, `__PUBLIC_PATH__`, `__DEV_MODE__`).
- **Jest + React Testing Library** for unit tests; `fast-check` available
  for property-based tests where structural invariants warrant it.
- **IdP-agnostic OIDC** via `react-oidc-context` + `oidc-client-ts`. Works
  with Amazon Cognito (reference default), Auth0, Okta, and Microsoft
  Entra ID. Logout is routed through `signoutRedirect()` so each IdP's
  `end_session_endpoint` from the OIDC discovery document is used.
- **Single profile** — browser automation. The multi-profile concierge /
  interview routing that lived in the parent project has been removed; the
  app shell renders `<AgentContent />` directly.

## Quick reference

### Frame summary (from `browser-agent-container`)

- **Client → Server (9)**: `CONNECTION_INIT`, `CHAT_MESSAGE`, `BROWSER_STOP`,
  `BROWSER_HITL_RESPONSE`, `BROWSER_LIVE_VIEW_REQUEST`, `NEW_SESSION`,
  `RESUME_SESSION`, `GET_SESSIONS`, `DELETE_SESSION`.
- **Server → Client (19)**: 11 shared (`CONNECTION_ESTABLISHED`,
  `SESSION_CREATED`, `SESSION_RESUMED`, `SESSIONS_LOADED`, `SESSION_DELETED`,
  `ORCHESTRATION_START`, `ORCHESTRATION_END`, `REASONING`, `STREAM`,
  `METADATA`, `ERROR`) + 8 browser-specific (`BROWSER_SESSION_STARTED`,
  `BROWSER_ACTION_START`, `BROWSER_SCREENSHOT`, `BROWSER_ACTION_COMPLETE`,
  `BROWSER_HITL_PROMPT`, `BROWSER_HITL_TIMEOUT`, `BROWSER_LIVE_VIEW_URL`,
  `BROWSER_SESSION_ENDED`).

See [`../browser-agent-container/docs/protocol.md`](../browser-agent-container/docs/protocol.md)
for wire-level detail.

### Rendering model

Each assistant turn renders as:

1. A collapsible **`<ReasoningTrace>`** that bundles step cards (reasoning
   text + `<ActionProgress>` + `<Screenshot>` + inline HITL) for the turn.
2. A privileged **`<FinalAnswer>`** card carrying the streaming output —
   separated so reasoning prose never leaks into the final answer.

Step cards group actions and screenshots by `stepNumber` — not by arrival
order — so the visual order on screen always matches the agent's own
numbering even if frames arrive out-of-order. Screenshots open in a
click-to-zoom MUI `<Dialog>` lightbox. Expired pre-signed URLs render a
graceful fallback because the backend does not expose a re-sign endpoint.

HITL prompts render as ordinary assistant chat messages. When
`pendingHitl` is non-null, the chat input placeholder swaps to "Respond to
the browser agent…" and the hook auto-dispatches `BROWSER_HITL_RESPONSE`
instead of `CHAT_MESSAGE`. No modal dialog, no context switch.

The opt-in **`<LiveView>`** panel embeds the Amazon DCV viewer via an
`<iframe>` and auto-refreshes the pre-signed URL every 270 seconds to stay
under the 300-second DCV TTL.

### `browserSteps.ts` — step grouping helper

`src/utils/browserSteps.ts` converts a flat `BrowserChatMessage` into a
grouped `BrowserMessageGrouping` (per-step cards + trailing reasoning +
final answer). It splits `agentMetadata.browser.reasoning` on `\n\n`
boundaries and distributes chunks to action steps in order; leftover
chunks become `trailingReasoning`. Orphan screenshots (no matching action
on the same `stepNumber`) become their own `screenshot`-typed step so
nothing is lost. Pure data, no React imports, trivially unit-testable.

## Build-time environment variables

Injected via Webpack `DefinePlugin` (see `webpack.config.js`). Read from
`.env.dev` during `yarn start-dev`, from `.env` during `yarn build`.

| Variable | Purpose |
|----------|---------|
| `WEBSOCKET_URL` | Full `wss://` URL of the gateway, or `ws://localhost:8081` for local. |
| `OIDC_AUTHORITY` | OIDC issuer URL (e.g. `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`). |
| `OIDC_CLIENT_ID` | SPA app client ID from your IdP. |
| `OIDC_AUDIENCE` | JWT audience. Empty for Cognito and Okta (default authorization server); required for Auth0. |
| `OIDC_SCOPE` | OAuth scopes, default `openid profile email`. |

See the root [`README.md`](../README.md) § "Switching identity providers"
for the full Cognito / Auth0 / Okta / Entra ID matrix.

## Authentication flow

- **Framework**: `react-oidc-context` + `oidc-client-ts`.
- **Flow**: Authorization Code + PKCE (SPA). No client secret.
- **Token storage**: sessionStorage, cleared on tab close. Silent renew
  handled automatically by `oidc-client-ts`.
- **WebSocket auth**: access token passed as `?token=<JWT>` query param.
  The gateway extracts it and injects `Authorization: Bearer <JWT>` on the
  upstream request to AgentCore Runtime. This pattern exists because
  browsers cannot set custom headers on the WebSocket upgrade — see
  [`../gateway-container/README.md`](../gateway-container/README.md)
  § "Why does this exist?" for the full story.
- **Logout**: `performLogout(auth)` in `src/config/oidc.ts` calls
  `signoutRedirect()`, which resolves each IdP's `end_session_endpoint`
  from the OIDC discovery document. Same code path works for Cognito,
  Auth0, Okta, and Entra ID.

## Extending

- **Adding a new WebSocket frame** — add the constant to
  `src/types/browser.types.ts`, extend the `BrowserServerMessage` or
  `BrowserClientMessage` discriminated union with the new payload shape,
  and wire it in `useBrowserChatSession` (server → UI) or the relevant
  component (UI → server). Add a unit test that round-trips the frame
  through `MockWebSocket`. Mirror the backend change in
  `../browser-agent-container/src/models/websocket_message_types.py`.
- **Adding a new component** — flat structure under `src/components/`.
  Each component owns a folder with `index.ts`, `<Name>.tsx`, optional
  CSS, and an entry in the corresponding test folder that mirrors the
  structure 1:1 (`tests/unit/components/<Name>/<Name>.test.tsx`).
- **Swapping the IdP** — change the four `OIDC_*` env values at build
  time. No code change. The repo is IdP-agnostic by construction.
- **Adding a new theme** — append a palette to
  `src/theme/themeConfig.ts` and a matching entry to `THEME_MAP` +
  `THEME_CONFIGS`. The `ThemeManager` component picks it up automatically.

## Testing

```bash
# Unit + integration (214 tests / 45 suites as of 2026-05-03)
yarn test --watchAll=false

# Unit tests only
yarn test:unit

# Integration tests only (MockWebSocket-backed)
yarn test:integration

# Type check
yarn tsc --noEmit

# Production build
yarn build

# Coverage report
yarn test:coverage
```

Test layout mirrors `src/` 1:1:

```text
tests/
├── unit/
│   ├── components/     # one folder per src/components/<Name>/
│   ├── config/
│   ├── contexts/
│   ├── hooks/          # including useBrowserChatSession.test.ts
│   ├── services/
│   ├── theme/
│   ├── types/
│   ├── utils/
│   └── App.test.tsx
└── integration/        # MockWebSocket-driven end-to-end frame coverage
    ├── __mocks__/
    ├── browserChatLifecycle.test.ts
    ├── frameCoverage.test.ts
    └── README.md        # manual multi-IdP smoke test procedure
```

Integration tests exercise the full 9-client / 19-server frame matrix
against a `MockWebSocket` harness, not a real backend. The multi-IdP
smoke test (Cognito / Auth0 / Okta) is documented as a manual procedure
in `tests/integration/README.md`.

## Project structure

```text
chat-bot-ui/
├── src/
│   ├── App.tsx, index.tsx, config.ts, setupTests.ts
│   ├── components/            # 24 flat component folders
│   │   ├── AgentContent/      # renamed from ProfileContent
│   │   ├── AppShell/, TopBar/, ChatInput/, ChatMessage/, Login/
│   │   ├── NotificationDisplay/, ProtectedRoute/, HelpModal/
│   │   ├── SettingsModal/, SidebarFooter/, SidebarHeader/
│   │   ├── SessionList/, StreamingCursor/, ThemeManager/
│   │   ├── KeyboardShortcuts/
│   │   └── ActionProgress/, ChatView/, FinalAnswer/, LiveView/
│   │       ReasoningTrace/, Screenshot/, SessionIndicator/, StepCard/
│   ├── config/                # oidc.ts (IdP-agnostic)
│   ├── contexts/              # NotificationContext, AccessibilityContext
│   ├── hooks/                 # useBrowserChatSession, useKeyboardNavigation
│   ├── services/              # ConfigurationService, NotificationService
│   ├── theme/                 # themeConfig.ts (9 themes)
│   ├── styles/                # main.css, accessibility.css, responsive.css
│   ├── types/                 # browser.types.ts (28 frame discriminated union)
│   └── utils/                 # browserSteps.ts, websocket.ts
├── tests/                     # mirrors src/
├── public/                    # index.html, manifest.json
├── scripts/                   # test-websocket-connection.js
├── webpack.config.js          # DefinePlugin + dev server config
├── package.json, tsconfig.json, jest.config.js
├── .env, .env.dev, .env.example
└── README.md                  # ← you are here
```

## Related

- **Root onboarding**: [`../README.md`](../README.md)
- **Browser agent backend**: [`../browser-agent-container/README.md`](../browser-agent-container/README.md)
- **Gateway**: [`../gateway-container/README.md`](../gateway-container/README.md)
- **Protocol reference**: [`../browser-agent-container/docs/protocol.md`](../browser-agent-container/docs/protocol.md)

License: see the repository-root `LICENSE` (MIT-0).
