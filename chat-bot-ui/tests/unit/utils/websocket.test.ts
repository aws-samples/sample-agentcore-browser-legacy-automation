// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * websocket.ts Tests
 *
 * Tests for buildWebSocketUrl: query parameters, URL encoding,
 * base URL matching, and empty token/profile handling.
 */

import { buildWebSocketUrl } from '../../../src/utils/websocket';

describe('buildWebSocketUrl', () => {
  it('contains token and profile query parameters', () => {
    const url = buildWebSocketUrl('my-token', 'concierge');

    expect(url).toContain('token=my-token');
    expect(url).toContain('profile=concierge');
  });

  it('URL-encodes special characters in token and profile', () => {
    const url = buildWebSocketUrl('tok en&val=ue', 'pro file/id');

    expect(url).toContain('token=tok%20en%26val%3Due');
    expect(url).toContain('profile=pro%20file%2Fid');
  });

  it('uses __WEBSOCKET_URL__ as the base URL', () => {
    const url = buildWebSocketUrl('t', 'p');

    // setupTests.ts sets __WEBSOCKET_URL__ to 'ws://localhost:8081'
    expect(url).toMatch(/^ws:\/\/localhost:8081\/ws\?/);
  });

  it('produces a valid URL structure with empty token and profile', () => {
    const url = buildWebSocketUrl('', '');

    expect(url).toBe('ws://localhost:8081/ws?token=&profile=');
  });
});
