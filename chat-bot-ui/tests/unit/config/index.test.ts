// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * config/index.ts smoke test — verifies the barrel re-exports the OIDC helpers.
 */

import * as configIndex from '../../../src/config';

describe('config/index barrel', () => {
  it('re-exports getOidcConfig, oidcConfig, and websocketConfig', () => {
    expect(typeof configIndex.getOidcConfig).toBe('function');
    expect(configIndex.oidcConfig).toBeDefined();
    expect(configIndex.websocketConfig).toBeDefined();
  });
});
