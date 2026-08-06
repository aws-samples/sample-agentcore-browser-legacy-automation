// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * OIDC Configuration — IdP-agnostic via DefinePlugin variables.
 *
 * Supports Auth0, Okta, Cognito, Entra ID, and any standard OIDC provider
 * through pure OIDC discovery (no IdP-specific switch statements).
 *
 * Environment variables injected at build time via webpack DefinePlugin:
 *   __OIDC_AUTHORITY__  — OIDC issuer URL (e.g. https://dev-xxx.okta.com)
 *   __OIDC_CLIENT_ID__  — SPA client ID
 *   __OIDC_AUDIENCE__   — API audience (Auth0 JWT requirement; empty for other IdPs)
 *   __OIDC_SCOPE__      — OAuth scopes (default: "openid profile email")
 *   __WEBSOCKET_URL__   — AgentCore WebSocket base URL
 *
 * @module config/oidc
 */

import { UserManagerSettings, WebStorageStateStore } from 'oidc-client-ts';

/**
 * Check if OIDC authentication is configured.
 */
export const isOAuthConfigured = (): boolean => {
  return Boolean(__OIDC_AUTHORITY__ && __OIDC_CLIENT_ID__);
};

/**
 * Get OIDC UserManager settings for AuthProvider.
 */
export const getOidcConfig = (): UserManagerSettings => {
  const extraQueryParams: Record<string, string> = {};

  // Auth0 requires explicit audience to return JWT access tokens (vs opaque)
  if (__OIDC_AUDIENCE__) {
    extraQueryParams.audience = __OIDC_AUDIENCE__;
  }

  return {
    authority: __OIDC_AUTHORITY__,
    client_id: __OIDC_CLIENT_ID__,
    redirect_uri: `${window.location.origin}${__PUBLIC_PATH__}callback`,
    post_logout_redirect_uri: `${window.location.origin}${__PUBLIC_PATH__}login`,
    scope: __OIDC_SCOPE__ || 'openid profile email',
    response_type: 'code',
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: true,
    loadUserInfo: true,
    extraQueryParams: Object.keys(extraQueryParams).length > 0 ? extraQueryParams : undefined,
  };
};

/**
 * Minimal structural interface describing the subset of `UserManager` (or the
 * `react-oidc-context` auth context) needed to perform a logout redirect.
 * Using this structural type rather than the full `UserManager` class makes
 * `performLogout` equally callable with:
 *   - `useAuth()` from `react-oidc-context` — the context object exposes
 *     `signoutRedirect` directly.
 *   - A raw `UserManager` instance from `oidc-client-ts`.
 */
export interface SignoutCapable {
  signoutRedirect(args?: { post_logout_redirect_uri?: string }): Promise<void>;
}

/**
 * Perform OIDC-compliant logout via the discovered `end_session_endpoint`.
 *
 * Uses `signoutRedirect()` which transparently resolves the IdP's end-session
 * endpoint via the OIDC discovery document. This works uniformly for Amazon
 * Cognito, Auth0, Okta, and Microsoft Entra ID without any IdP-specific
 * branching.
 *
 * The caller (typically the sign-out button handler) is responsible for:
 *   - Setting any UI "logging-out" guard flags
 *   - Stopping silent renew / clearing local storage
 *   - Calling `removeUser()` if needed
 * before invoking this helper.
 *
 * @param signoutCapable — Either the `react-oidc-context` auth object returned
 *                         by `useAuth()`, or a raw `UserManager` instance from
 *                         `oidc-client-ts`. Both expose `signoutRedirect`.
 */
export const performLogout = async (
  signoutCapable: SignoutCapable,
): Promise<void> => {
  await signoutCapable.signoutRedirect({
    post_logout_redirect_uri: `${window.location.origin}${__PUBLIC_PATH__}login`,
  });
};

/** Legacy static export for backward compatibility. */
export const oidcConfig = getOidcConfig();

/** WebSocket configuration for AgentCore connection. */
export const websocketConfig = {
  url: __WEBSOCKET_URL__,
};
