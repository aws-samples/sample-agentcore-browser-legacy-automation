// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Jest setup — sets up the jsdom environment for the browser-agent chat UI.
 *
 * Scope: DefinePlugin globals, browser API polyfills, and a default WebSocket
 * mock. Tests that need fine-grained WebSocket control override the global
 * `WebSocket` in their own setup (see tests/unit/hooks/useBrowserChatSession.test.ts).
 */

import '@testing-library/jest-dom';

// Polyfill TextEncoder/TextDecoder (required by react-router-dom under jsdom)
import { TextEncoder, TextDecoder } from 'util';
(global as any).TextEncoder = TextEncoder;
(global as any).TextDecoder = TextDecoder;

// -----------------------------------------------------------------------------
// Webpack DefinePlugin runtime values for tests
// (declarations live in src/types/global.d.ts)
// -----------------------------------------------------------------------------
(global as any).__WEBSOCKET_URL__ = 'ws://localhost:8081';
(global as any).__DEV_MODE__ = true;
(global as any).__OIDC_AUTHORITY__ = 'https://test-auth.example.com';
(global as any).__OIDC_CLIENT_ID__ = 'test-client-id';
(global as any).__OIDC_AUDIENCE__ = 'https://test-api.example.com';
(global as any).__OIDC_SCOPE__ = 'openid profile email';
(global as any).__PUBLIC_PATH__ = '/';

// Base64 polyfills for Node.js environment
if (typeof global.btoa === 'undefined') {
  global.btoa = (str: string) => Buffer.from(str, 'binary').toString('base64');
}
if (typeof global.atob === 'undefined') {
  global.atob = (str: string) => Buffer.from(str, 'base64').toString('binary');
}

// -----------------------------------------------------------------------------
// matchMedia / ResizeObserver / IntersectionObserver — MUI + responsive shims
// -----------------------------------------------------------------------------
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// -----------------------------------------------------------------------------
// Default WebSocket mock — permissive; tests that assert on frame traffic
// override (global as any).WebSocket in their own beforeEach.
// -----------------------------------------------------------------------------
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send(_data: string | ArrayBuffer | Blob) {
    // Default mock: drop the frame.
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }

  addEventListener(_type: string, _listener: EventListener) {
    // no-op
  }

  removeEventListener(_type: string, _listener: EventListener) {
    // no-op
  }
}

(global as any).WebSocket = MockWebSocket;

// -----------------------------------------------------------------------------
// Console noise suppression — hides React-specific warnings only.
// -----------------------------------------------------------------------------
const originalError = console.error;
const originalWarn = console.warn;

beforeEach(() => {
  console.error = jest.fn((message, ...args) => {
    if (typeof message === 'string' && message.includes('Warning:')) {
      return;
    }
    originalError.call(console, message, ...args);
  });

  console.warn = jest.fn((message, ...args) => {
    if (typeof message === 'string' && message.includes('Warning:')) {
      return;
    }
    originalWarn.call(console, message, ...args);
  });
});

afterEach(() => {
  console.error = originalError;
  console.warn = originalWarn;
  jest.clearAllMocks();
});
