// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * config/oidc.ts smoke test — verifies the OIDC helpers produce
 * well-formed UserManager settings from the DefinePlugin globals.
 */

import {
  getOidcConfig,
  isOAuthConfigured,
  oidcConfig,
  performLogout,
  websocketConfig,
} from '../../../src/config/oidc';

describe('config/oidc', () => {
  it('isOAuthConfigured returns true when both authority and client id are set', () => {
    // setupTests.ts sets test values for both — see `__OIDC_AUTHORITY__` / `__OIDC_CLIENT_ID__`.
    expect(isOAuthConfigured()).toBe(true);
  });

  it('getOidcConfig produces a UserManagerSettings object wired to window.location.origin', () => {
    const cfg = getOidcConfig();
    expect(cfg.authority).toBe('https://test-auth.example.com');
    expect(cfg.client_id).toBe('test-client-id');
    expect(cfg.redirect_uri).toMatch(/\/callback$/);
    expect(cfg.post_logout_redirect_uri).toMatch(/\/login$/);
    expect(cfg.response_type).toBe('code');
    expect(cfg.scope).toBe('openid profile email');
  });

  it('getOidcConfig threads __OIDC_AUDIENCE__ through extraQueryParams.audience', () => {
    const cfg = getOidcConfig();
    expect(cfg.extraQueryParams).toEqual({ audience: 'https://test-api.example.com' });
  });

  it('oidcConfig legacy static export matches getOidcConfig at module load time', () => {
    expect(oidcConfig.client_id).toBe('test-client-id');
  });

  it('websocketConfig.url is set from __WEBSOCKET_URL__', () => {
    expect(websocketConfig.url).toBe('ws://localhost:8081');
  });

  it('performLogout delegates to signoutRedirect and passes post_logout_redirect_uri', async () => {
    const signoutRedirect = jest.fn().mockResolvedValue(undefined);
    await performLogout({ signoutRedirect });
    expect(signoutRedirect).toHaveBeenCalledTimes(1);
    const args = signoutRedirect.mock.calls[0][0];
    expect(args.post_logout_redirect_uri).toMatch(/\/login$/);
  });
});
