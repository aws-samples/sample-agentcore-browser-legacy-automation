// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * MockWebSocket — a controllable WebSocket implementation for integration
 * tests of `useBrowserChatSession`.
 *
 * The real hook speaks the 9 client frames + 19 server frames of the
 * browser-agent protocol (see `src/types/browser.types.ts`). This mock
 * captures every outgoing frame into `sentMessages`, and exposes
 * helpers to inject server frames synchronously so tests can drive a
 * full CHAT_MESSAGE → BROWSER_SESSION_STARTED → … → ORCHESTRATION_END
 * sequence deterministically.
 *
 * Every instance is tracked on the static `instances` registry so tests
 * can `MockWebSocket.latest()` to get the most recently constructed
 * socket (the one the hook's current `connect()` attached to).
 */

export class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  /** Registry of every MockWebSocket ever constructed during a test. */
  static instances: MockWebSocket[] = [];

  /** Reset the registry between test cases. */
  static reset(): void {
    MockWebSocket.instances = [];
  }

  /** Returns the most recently constructed socket. */
  static latest(): MockWebSocket {
    if (MockWebSocket.instances.length === 0) {
      throw new Error('No MockWebSocket has been constructed yet');
    }
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }

  readonly url: string;
  readyState: number = MockWebSocket.CONNECTING;

  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  /** Raw outgoing frames — JSON strings the hook passed to `send()`. */
  readonly sentMessages: string[] = [];
  /** Every `close()` invocation with the given code/reason. */
  readonly closeCalls: Array<{ code?: number; reason?: string }> = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  // --- Web API surface --------------------------------------------------

  send(data: string): void {
    this.sentMessages.push(data);
  }

  close(code?: number, reason?: string): void {
    this.closeCalls.push({ code, reason });
    this.readyState = MockWebSocket.CLOSED;
  }

  addEventListener(): void {
    // The hook uses direct on* assignments; addEventListener is intentionally a no-op.
  }

  removeEventListener(): void {
    // no-op
  }

  // --- Test-controlled events -------------------------------------------

  /** Transition the socket to OPEN and fire the onopen handler. */
  simulateOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  /** Push a structured JSON frame to the hook's message listener. */
  simulateMessage(data: Record<string, unknown>): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  /** Push a raw (possibly malformed) payload to the hook's message listener. */
  simulateRawMessage(raw: string): void {
    this.onmessage?.(new MessageEvent('message', { data: raw }));
  }

  /** Close the socket with a given code (1006 by default = abnormal). */
  simulateClose(code = 1006, reason = ''): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }

  simulateError(): void {
    this.onerror?.(new Event('error'));
  }

  // --- Assertion helpers ------------------------------------------------

  /** Parse every outgoing frame. */
  getSentParsed(): Record<string, unknown>[] {
    return this.sentMessages.map((m) => JSON.parse(m));
  }

  /** Find the most recent outgoing frame of a given type (if any). */
  findSent(type: string): Record<string, unknown> | undefined {
    const parsed = this.getSentParsed();
    for (let i = parsed.length - 1; i >= 0; i -= 1) {
      if (parsed[i].type === type) return parsed[i];
    }
    return undefined;
  }
}

/**
 * Install MockWebSocket as the global WebSocket. Returns a teardown
 * function that restores the previous global.
 */
export function installMockWebSocket(): () => void {
  const previous = (global as unknown as { WebSocket?: unknown }).WebSocket;
  MockWebSocket.reset();

  const mockCtor = jest.fn((url: string) => new MockWebSocket(url)) as unknown as typeof WebSocket;
  (mockCtor as unknown as { OPEN: number }).OPEN = MockWebSocket.OPEN;
  (mockCtor as unknown as { CONNECTING: number }).CONNECTING = MockWebSocket.CONNECTING;
  (mockCtor as unknown as { CLOSING: number }).CLOSING = MockWebSocket.CLOSING;
  (mockCtor as unknown as { CLOSED: number }).CLOSED = MockWebSocket.CLOSED;

  (global as unknown as { WebSocket: unknown }).WebSocket = mockCtor;

  return () => {
    (global as unknown as { WebSocket: unknown }).WebSocket = previous;
    MockWebSocket.reset();
  };
}
