// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Unit tests for useBrowserChatSession hook.
 *
 * Covers:
 *  - Connection lifecycle + handshake (CONNECTION_INIT → CONNECTION_ESTABLISHED → GET_SESSIONS)
 *  - All 19 server frames (11 shared + 8 browser-specific)
 *  - All 9 client dispatchers
 *  - HITL auto-swap behaviour (sendMessage flips to BROWSER_HITL_RESPONSE when pendingHitl is set)
 *  - Exponential-backoff reconnection (1s → 2s → 4s → 8s → 16s, halt at MAX_RETRIES = 5)
 *  - User-initiated disconnect (close 1000; no reconnection)
 *  - Out-of-order BROWSER_ACTION_START / BROWSER_ACTION_COMPLETE keyed by stepNumber
 *  - Malformed-JSON frames are swallowed without state change
 *
 */

import { renderHook, act } from '@testing-library/react';
import { useBrowserChatSession } from '../../../src/hooks/useBrowserChatSession';
import { BrowserMessageType } from '../../../src/types/browser.types';

// ---------------------------------------------------------------------------
// Mock buildWebSocketUrl
// ---------------------------------------------------------------------------
jest.mock('../../../src/utils/websocket', () => ({
  buildWebSocketUrl: (token: string, profile: string) =>
    `ws://test-host/ws?token=${encodeURIComponent(token)}&profile=${encodeURIComponent(profile)}`,
}));

// ---------------------------------------------------------------------------
// Mock crypto.randomUUID for deterministic IDs
// ---------------------------------------------------------------------------
let uuidCounter = 0;
const mockRandomUUID = jest.fn(() => {
  uuidCounter += 1;
  return `test-uuid-${uuidCounter}`;
});
Object.defineProperty(global, 'crypto', {
  value: { randomUUID: mockRandomUUID },
  writable: true,
});

// ---------------------------------------------------------------------------
// MockWebSocket — manual control over open/message/close/error events
// ---------------------------------------------------------------------------
class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  sentMessages: string[] = [];
  closeCalls: Array<{ code?: number; reason?: string }> = [];

  constructor(url: string) {
    this.url = url;
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close(code?: number, reason?: string) {
    this.closeCalls.push({ code, reason });
    this.readyState = MockWebSocket.CLOSED;
  }

  // ---- Test helpers ----

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateRawMessage(raw: string) {
    this.onmessage?.(new MessageEvent('message', { data: raw }));
  }

  simulateClose(code = 1006, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }

  getSentParsed(): Record<string, unknown>[] {
    return this.sentMessages.map((m) => JSON.parse(m));
  }
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

let mockWsInstances: MockWebSocket[] = [];

beforeEach(() => {
  jest.useFakeTimers();
  uuidCounter = 0;
  mockWsInstances = [];

  // Override the global WebSocket from setupTests.ts with our controllable mock.
  (global as any).WebSocket = jest.fn((url: string) => {
    const ws = new MockWebSocket(url);
    mockWsInstances.push(ws);
    return ws;
  });
  // Attach static constants so readyState comparisons inside the hook still work.
  (global as any).WebSocket.OPEN = MockWebSocket.OPEN;
  (global as any).WebSocket.CONNECTING = MockWebSocket.CONNECTING;
  (global as any).WebSocket.CLOSING = MockWebSocket.CLOSING;
  (global as any).WebSocket.CLOSED = MockWebSocket.CLOSED;
});

afterEach(() => {
  jest.useRealTimers();
});

/** Shorthand: most-recently-constructed MockWebSocket instance. */
const latestWs = (): MockWebSocket => mockWsInstances[mockWsInstances.length - 1];

/**
 * Connect the hook and complete the CONNECTION_ESTABLISHED handshake.
 * Returns the renderHook result for further test actions.
 */
function connectAndHandshake() {
  const hookReturn = renderHook(() => useBrowserChatSession());

  act(() => {
    hookReturn.result.current.connect('test-token', 'browser');
  });

  const ws = latestWs();

  act(() => {
    ws.simulateOpen();
  });

  act(() => {
    ws.simulateMessage({
      type: BrowserMessageType.CONNECTION_ESTABLISHED,
      session_id: 'sess-001',
      profile: 'browser',
    });
  });

  return hookReturn;
}

// ===========================================================================
// Tests
// ===========================================================================

describe('useBrowserChatSession', () => {
  // -----------------------------------------------------------------------
  // Connection & handshake
  // -----------------------------------------------------------------------
  describe('connection & handshake', () => {
    it('starts in disconnected state with empty collections', () => {
      const { result } = renderHook(() => useBrowserChatSession());
      expect(result.current.connectionState).toBe('disconnected');
      expect(result.current.sessionId).toBeNull();
      expect(result.current.messages).toEqual([]);
      expect(result.current.sessions).toEqual([]);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.browserSession).toEqual({
        isActive: false,
        liveViewUrl: null,
        stepCounter: 0,
        pendingHitl: null,
      });
    });

    it('transitions to connecting on connect() and builds the correct URL', () => {
      const { result } = renderHook(() => useBrowserChatSession());

      act(() => {
        result.current.connect('tok', 'browser');
      });

      expect(result.current.connectionState).toBe('connecting');
      expect(mockWsInstances).toHaveLength(1);
      expect(latestWs().url).toBe('ws://test-host/ws?token=tok&profile=browser');
    });

    it('completes the handshake: CONNECTION_INIT on open → CONNECTION_ESTABLISHED → auto GET_SESSIONS', () => {
      const { result } = renderHook(() => useBrowserChatSession());

      act(() => {
        result.current.connect('tok', 'browser');
      });

      const ws = latestWs();

      act(() => {
        ws.simulateOpen();
      });

      // CONNECTION_INIT fires first.
      let sent = ws.getSentParsed();
      expect(sent).toHaveLength(1);
      expect(sent[0]).toEqual({ type: BrowserMessageType.CONNECTION_INIT });

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.CONNECTION_ESTABLISHED,
          session_id: 'sess-abc',
          profile: 'browser',
        });
      });

      expect(result.current.connectionState).toBe('connected');
      expect(result.current.sessionId).toBe('sess-abc');

      // GET_SESSIONS is auto-fired after CONNECTION_ESTABLISHED.
      sent = ws.getSentParsed();
      expect(sent).toHaveLength(2);
      expect(sent[1]).toEqual({ type: BrowserMessageType.GET_SESSIONS });
    });
  });

  // -----------------------------------------------------------------------
  // Shared concierge-style server frames
  // -----------------------------------------------------------------------
  describe('shared server frames', () => {
    it('CONNECTION_ESTABLISHED sets sessionId and transitions to connected', () => {
      const hookReturn = connectAndHandshake();
      expect(hookReturn.result.current.sessionId).toBe('sess-001');
      expect(hookReturn.result.current.connectionState).toBe('connected');
    });

    it('SESSION_CREATED updates sessionId and clears messages', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      // Seed a message so we can observe the clear.
      act(() => {
        hookReturn.result.current.sendMessage('hello');
      });
      expect(hookReturn.result.current.messages.length).toBeGreaterThan(0);

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSION_CREATED,
          session_id: 'new-sess-123',
        });
      });

      expect(hookReturn.result.current.sessionId).toBe('new-sess-123');
      expect(hookReturn.result.current.messages).toEqual([]);
    });

    it('SESSION_RESUMED restores conversation_history and resets browser session state', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      // Pre-populate browser session state to confirm it resets.
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_SESSION_STARTED,
          session_id: 'sess-001',
          liveViewUrl: 'https://live.example/old',
        });
      });
      expect(hookReturn.result.current.browserSession.isActive).toBe(true);

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSION_RESUMED,
          session_id: 'resumed-sess',
          conversation_history: [
            { role: 'user', content: 'What is RPA?' },
            { role: 'assistant', content: 'Robotic Process Automation.' },
          ],
        });
      });

      expect(hookReturn.result.current.sessionId).toBe('resumed-sess');
      expect(hookReturn.result.current.messages).toHaveLength(2);
      expect(hookReturn.result.current.messages[0].role).toBe('user');
      expect(hookReturn.result.current.messages[0].content).toBe('What is RPA?');
      expect(hookReturn.result.current.messages[1].role).toBe('assistant');
      expect(hookReturn.result.current.messages[1].content).toBe('Robotic Process Automation.');
      expect(hookReturn.result.current.browserSession).toEqual({
        isActive: false,
        liveViewUrl: null,
        stepCounter: 0,
        pendingHitl: null,
      });
    });

    it('SESSIONS_LOADED populates the sessions list', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSIONS_LOADED,
          sessions: [
            {
              session_id: 'prev-1',
              profile: 'browser',
              mode: 'text',
              title: 'Prev 1',
              created_at: '2025-01-01T00:00:00Z',
              messages: [],
            },
            {
              session_id: 'prev-2',
              profile: 'browser',
              mode: 'text',
              title: 'Prev 2',
              created_at: '2025-01-02T00:00:00Z',
              messages: [],
            },
          ],
        });
      });

      expect(hookReturn.result.current.sessions).toHaveLength(2);
      expect(hookReturn.result.current.sessions[0].session_id).toBe('prev-1');
      expect(hookReturn.result.current.sessions[1].session_id).toBe('prev-2');
    });

    // Issue 1 (.kiro/research/temp-browser-ui-issues-analysis.md) — the hook
    // must map the wire-format summary dicts into SessionInfo entries with
    // profile/mode populated so the shared SessionList component routes
    // icons and resume clicks correctly for the browser profile.
    it('SESSIONS_LOADED maps summary entries to SessionInfo with profile + mode', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSIONS_LOADED,
          sessions: [
            {
              session_id: 'summary-1',
              profile: 'browser',
              mode: 'text',
              created_at: '2025-02-01T00:00:00Z',
              message_count: 4,
              first_message_preview: 'Navigate to wikipedia',
              status: 'completed',
            },
            {
              session_id: 'summary-2',
              profile: 'browser',
              mode: 'text',
              created_at: '2025-02-02T00:00:00Z',
              message_count: 2,
              first_message_preview: 'Go to httpbin form',
              status: 'active',
            },
          ],
        });
      });

      const sessions = hookReturn.result.current.sessions;
      expect(sessions).toHaveLength(2);
      expect(sessions[0]).toMatchObject({
        session_id: 'summary-1',
        profile: 'browser',
        mode: 'text',
        title: 'Navigate to wikipedia',
        created_at: '2025-02-01T00:00:00Z',
        messages: [],
      });
      expect(sessions[1]).toMatchObject({
        session_id: 'summary-2',
        profile: 'browser',
        mode: 'text',
        title: 'Go to httpbin form',
      });
    });

    it('SESSIONS_LOADED defaults profile=browser and mode=text when missing', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      // Simulate an older container that does not yet include profile/mode
      // in its wire payload — the hook's defensive defaults must cover this.
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSIONS_LOADED,
          sessions: [
            {
              session_id: 'legacy-1',
              created_at: '2024-12-01T00:00:00Z',
              message_count: 1,
              first_message_preview: 'legacy prompt',
            },
          ],
        });
      });

      const sessions = hookReturn.result.current.sessions;
      expect(sessions).toHaveLength(1);
      expect(sessions[0].profile).toBe('browser');
      expect(sessions[0].mode).toBe('text');
      expect(sessions[0].title).toBe('legacy prompt');
    });

    it('SESSIONS_LOADED uses "Untitled session" when first_message_preview is empty', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSIONS_LOADED,
          sessions: [
            {
              session_id: 'empty-preview',
              profile: 'browser',
              mode: 'text',
              created_at: '2025-03-01T00:00:00Z',
              message_count: 0,
              first_message_preview: '',
            },
          ],
        });
      });

      expect(hookReturn.result.current.sessions[0].title).toBe('Untitled session');
    });

    it('SESSION_DELETED removes the matching session from the list', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSIONS_LOADED,
          sessions: [
            { session_id: 'a', profile: 'browser', mode: 'text', title: 'A', created_at: '', messages: [] },
            { session_id: 'b', profile: 'browser', mode: 'text', title: 'B', created_at: '', messages: [] },
          ],
        });
      });
      expect(hookReturn.result.current.sessions).toHaveLength(2);

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.SESSION_DELETED,
          session_id: 'a',
        });
      });

      expect(hookReturn.result.current.sessions).toHaveLength(1);
      expect(hookReturn.result.current.sessions[0].session_id).toBe('b');
    });

    it('ORCHESTRATION_START flips isStreaming true and state to streaming', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
      });

      expect(hookReturn.result.current.isStreaming).toBe(true);
      expect(hookReturn.result.current.connectionState).toBe('streaming');
      // A placeholder assistant message should have been seeded.
      expect(hookReturn.result.current.messages.some((m) => m.role === 'assistant')).toBe(true);
    });

    it('ORCHESTRATION_END flips isStreaming false and state to connected', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
      });

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_END });
      });

      expect(hookReturn.result.current.isStreaming).toBe(false);
      expect(hookReturn.result.current.connectionState).toBe('connected');
      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.isStreaming).toBe(false);
    });

    it('REASONING frames append to agentMetadata.browser.reasoning on the current assistant message', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
      });

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.REASONING, content: 'thinking… ' });
      });
      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.REASONING, content: 'next step.' });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.agentMetadata?.browser?.reasoning).toBe('thinking… next step.');
    });

    it('STREAM frames append to the current assistant message content', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
      });
      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.STREAM, content: 'Hello ' });
      });
      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.STREAM, content: 'world' });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.content).toBe('Hello world');
    });

    it('METADATA attaches total_duration_ms + steps_completed under agentMetadata.browser', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
      });

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.METADATA,
          total_duration_ms: 1234,
          steps_completed: 7,
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.agentMetadata?.browser?.total_duration_ms).toBe(1234);
      expect(assistant?.agentMetadata?.browser?.steps_completed).toBe(7);
    });

    it('ERROR frames mark the current assistant message as error and halt streaming', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.ERROR,
          content: 'Something went wrong',
          recoverable: true,
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.isError).toBe(true);
      expect(assistant?.recoverable).toBe(true);
      expect(assistant?.content).toContain('Something went wrong');
      expect(assistant?.isStreaming).toBe(false);
    });
  });

  // -----------------------------------------------------------------------
  // Browser-specific server frames
  // -----------------------------------------------------------------------
  describe('browser-specific server frames', () => {
    it('BROWSER_SESSION_STARTED sets isActive true and stores liveViewUrl', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_SESSION_STARTED,
          session_id: 'sess-001',
          liveViewUrl: 'https://live.example.com/dcv',
        });
      });

      expect(hookReturn.result.current.browserSession.isActive).toBe(true);
      expect(hookReturn.result.current.browserSession.liveViewUrl).toBe('https://live.example.com/dcv');
    });

    it('BROWSER_ACTION_START appends a running action entry and advances stepCounter', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_START,
          actionType: 'browser',
          details: 'click #login',
          stepNumber: 3,
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.actions).toHaveLength(1);
      expect(assistant?.actions?.[0]).toEqual({
        stepNumber: 3,
        actionType: 'browser',
        details: 'click #login',
        status: 'running',
      });
      expect(hookReturn.result.current.browserSession.stepCounter).toBe(3);
    });

    it('BROWSER_SCREENSHOT appends a screenshot entry to the current assistant message', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_SCREENSHOT,
          stepNumber: 2,
          screenshotUrl: 'https://s3.example/pre-signed/step-2.png',
          screenshotPath: 's3/key/step-2.png',
          title: 'Login page',
          timestamp: 1_700_000_000_000,
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      expect(assistant?.screenshots).toHaveLength(1);
      expect(assistant?.screenshots?.[0]).toEqual({
        stepNumber: 2,
        screenshotUrl: 'https://s3.example/pre-signed/step-2.png',
        screenshotPath: 's3/key/step-2.png',
        title: 'Login page',
        timestamp: 1_700_000_000_000,
      });
      expect(hookReturn.result.current.browserSession.stepCounter).toBe(2);
    });

    it('BROWSER_ACTION_COMPLETE transitions a matching action to succeeded', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_START,
          actionType: 'browser',
          details: 'navigate example.com',
          stepNumber: 1,
        });
      });
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_COMPLETE,
          actionType: 'browser',
          result: 'ok',
          success: true,
          stepNumber: 1,
          currentUrl: 'https://example.com/',
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      const action = assistant?.actions?.find((a) => a.stepNumber === 1);
      expect(action?.status).toBe('succeeded');
      expect(action?.result).toBe('ok');
    });

    it('BROWSER_ACTION_COMPLETE with success=false marks the action as failed', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_START,
          actionType: 'browser',
          details: 'click missing',
          stepNumber: 4,
        });
      });
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_COMPLETE,
          actionType: 'browser',
          result: 'element not found',
          success: false,
          stepNumber: 4,
          currentUrl: 'https://example.com/',
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      const action = assistant?.actions?.find((a) => a.stepNumber === 4);
      expect(action?.status).toBe('failed');
      expect(action?.result).toBe('element not found');
    });

    it('BROWSER_HITL_PROMPT appends a new assistant message and sets pendingHitl', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_PROMPT,
          promptId: 'hitl-1',
          question: 'Proceed with payment?',
          options: ['yes', 'no'],
          context: 'Checkout',
          screenshotBase64: 'iVBORw0KGgo=',
        });
      });

      const withPrompt = hookReturn.result.current.messages.find((m) => !!m.hitlPrompt);
      expect(withPrompt).toBeDefined();
      expect(withPrompt?.hitlPrompt?.promptId).toBe('hitl-1');
      expect(withPrompt?.hitlPrompt?.question).toBe('Proceed with payment?');
      expect(withPrompt?.hitlPrompt?.options).toEqual(['yes', 'no']);
      expect(withPrompt?.hitlPrompt?.status).toBe('pending');
      expect(hookReturn.result.current.browserSession.pendingHitl?.promptId).toBe('hitl-1');
    });

    it('BROWSER_HITL_TIMEOUT marks the pending prompt as timeout and clears pendingHitl', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_PROMPT,
          promptId: 'hitl-2',
          question: 'Confirm?',
          options: [],
          context: '',
          screenshotBase64: '',
        });
      });
      expect(hookReturn.result.current.browserSession.pendingHitl).not.toBeNull();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_TIMEOUT,
          session_id: 'sess-001',
        });
      });

      expect(hookReturn.result.current.browserSession.pendingHitl).toBeNull();
      const msg = hookReturn.result.current.messages.find((m) => m.hitlPrompt?.promptId === 'hitl-2');
      expect(msg?.hitlPrompt?.status).toBe('timeout');
    });

    it('BROWSER_LIVE_VIEW_URL refreshes the live-view URL', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_LIVE_VIEW_URL,
          session_id: 'sess-001',
          liveViewUrl: 'https://live.example.com/refreshed',
        });
      });

      expect(hookReturn.result.current.browserSession.liveViewUrl).toBe('https://live.example.com/refreshed');
    });

    it('BROWSER_SESSION_ENDED resets browserSession to the initial state', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_SESSION_STARTED,
          session_id: 'sess-001',
          liveViewUrl: 'https://live.example.com/dcv',
        });
      });
      expect(hookReturn.result.current.browserSession.isActive).toBe(true);

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_SESSION_ENDED,
          session_id: 'sess-001',
          reason: 'completed',
        });
      });

      expect(hookReturn.result.current.browserSession).toEqual({
        isActive: false,
        liveViewUrl: null,
        stepCounter: 0,
        pendingHitl: null,
      });
    });
  });

  // -----------------------------------------------------------------------
  // Client dispatchers (one test per client frame type)
  // -----------------------------------------------------------------------
  describe('client dispatchers', () => {
    it('sends CONNECTION_INIT on WebSocket open', () => {
      const { result } = renderHook(() => useBrowserChatSession());

      act(() => {
        result.current.connect('tok', 'browser');
      });

      const ws = latestWs();

      act(() => {
        ws.simulateOpen();
      });

      const sent = ws.getSentParsed();
      expect(sent[0]).toEqual({ type: BrowserMessageType.CONNECTION_INIT });
    });

    it('sendMessage dispatches CHAT_MESSAGE when no pendingHitl is set', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.sendMessage('What day is it?');
      });

      const sent = ws.getSentParsed();
      const chat = sent.find((m) => m.type === BrowserMessageType.CHAT_MESSAGE);
      expect(chat).toEqual({
        type: BrowserMessageType.CHAT_MESSAGE,
        content: 'What day is it?',
      });

      // User message + streaming assistant placeholder appended.
      const msgs = hookReturn.result.current.messages;
      expect(msgs.some((m) => m.role === 'user' && m.content === 'What day is it?')).toBe(true);
      expect(msgs.some((m) => m.role === 'assistant' && m.isStreaming)).toBe(true);
    });

    it('stopBrowser dispatches BROWSER_STOP', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.stopBrowser();
      });

      const sent = ws.getSentParsed();
      expect(sent.some((m) => m.type === BrowserMessageType.BROWSER_STOP)).toBe(true);
    });

    it('sendHitlResponse dispatches BROWSER_HITL_RESPONSE and clears pendingHitl', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_PROMPT,
          promptId: 'hitl-42',
          question: 'Pick one',
          options: ['a', 'b'],
          context: '',
          screenshotBase64: '',
        });
      });

      act(() => {
        hookReturn.result.current.sendHitlResponse('pick', 'a');
      });

      const sent = ws.getSentParsed();
      const hitl = sent.find((m) => m.type === BrowserMessageType.BROWSER_HITL_RESPONSE);
      expect(hitl).toEqual({
        type: BrowserMessageType.BROWSER_HITL_RESPONSE,
        promptId: 'hitl-42',
        action: 'pick',
        value: 'a',
      });
      expect(hookReturn.result.current.browserSession.pendingHitl).toBeNull();
    });

    it('requestLiveViewUrl dispatches BROWSER_LIVE_VIEW_REQUEST', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.requestLiveViewUrl();
      });

      const sent = ws.getSentParsed();
      expect(sent.some((m) => m.type === BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST)).toBe(true);
    });

    it('newSession dispatches NEW_SESSION', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.newSession();
      });

      const sent = ws.getSentParsed();
      expect(sent.some((m) => m.type === BrowserMessageType.NEW_SESSION)).toBe(true);
    });

    it('resumeSession dispatches RESUME_SESSION with the given session_id', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.resumeSession('old-sess');
      });

      const sent = ws.getSentParsed();
      const resume = sent.find((m) => m.type === BrowserMessageType.RESUME_SESSION);
      expect(resume).toEqual({
        type: BrowserMessageType.RESUME_SESSION,
        session_id: 'old-sess',
      });
    });

    it('getSessions dispatches GET_SESSIONS (beyond the auto-fire)', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.getSessions();
      });

      const sent = ws.getSentParsed();
      const getSessionsCount = sent.filter((m) => m.type === BrowserMessageType.GET_SESSIONS).length;
      // At least two: one from the handshake auto-fire + one from the manual call.
      expect(getSessionsCount).toBeGreaterThanOrEqual(2);
    });

    it('deleteSession dispatches DELETE_SESSION with the given session_id', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.deleteSession('gone-sess');
      });

      const sent = ws.getSentParsed();
      const del = sent.find((m) => m.type === BrowserMessageType.DELETE_SESSION);
      expect(del).toEqual({
        type: BrowserMessageType.DELETE_SESSION,
        session_id: 'gone-sess',
      });
    });
  });

  // -----------------------------------------------------------------------
  // HITL auto-swap behaviour
  // -----------------------------------------------------------------------
  describe('HITL auto-swap behavior', () => {
    it('sendMessage dispatches BROWSER_HITL_RESPONSE when pendingHitl is set', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_PROMPT,
          promptId: 'hitl-auto',
          question: 'Continue?',
          options: [],
          context: '',
          screenshotBase64: '',
        });
      });

      act(() => {
        hookReturn.result.current.sendMessage('yes please');
      });

      const sent = ws.getSentParsed();
      const hitl = sent.find((m) => m.type === BrowserMessageType.BROWSER_HITL_RESPONSE);
      expect(hitl).toEqual({
        type: BrowserMessageType.BROWSER_HITL_RESPONSE,
        promptId: 'hitl-auto',
        action: 'respond',
        value: 'yes please',
      });
      // Should NOT have dispatched a CHAT_MESSAGE.
      expect(sent.some((m) => m.type === BrowserMessageType.CHAT_MESSAGE)).toBe(false);
      // pendingHitl should be cleared.
      expect(hookReturn.result.current.browserSession.pendingHitl).toBeNull();
      // The prompt should be marked 'responded'.
      const prompt = hookReturn.result.current.messages.find((m) => m.hitlPrompt?.promptId === 'hitl-auto');
      expect(prompt?.hitlPrompt?.status).toBe('responded');
    });

    it('sendMessage falls back to CHAT_MESSAGE once HITL has been responded', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_HITL_PROMPT,
          promptId: 'hitl-x',
          question: 'ok?',
          options: [],
          context: '',
          screenshotBase64: '',
        });
      });
      act(() => {
        hookReturn.result.current.sendMessage('yes');
      });

      // Now send a normal follow-up message; pendingHitl is cleared.
      act(() => {
        hookReturn.result.current.sendMessage('next question');
      });

      const sent = ws.getSentParsed();
      const chat = sent.find(
        (m) => m.type === BrowserMessageType.CHAT_MESSAGE && (m as Record<string, unknown>).content === 'next question',
      );
      expect(chat).toBeDefined();
    });
  });

  // -----------------------------------------------------------------------
  // Reconnection with exponential backoff
  // -----------------------------------------------------------------------
  describe('reconnection with exponential backoff', () => {
    it('triggers reconnection with the delay sequence 1000 → 2000 → 4000 → 8000 → 16000 and halts at MAX_RETRIES = 5', () => {
      const hookReturn = connectAndHandshake();
      const ws1 = latestWs();

      // First abnormal close.
      act(() => {
        ws1.simulateClose(1006, 'abnormal');
      });
      expect(hookReturn.result.current.connectionState).toBe('connecting');

      // Retry 1: 1000ms
      expect(mockWsInstances).toHaveLength(1);
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(mockWsInstances).toHaveLength(2);

      act(() => {
        latestWs().simulateClose(1006);
      });

      // Retry 2: 2000ms
      act(() => {
        jest.advanceTimersByTime(1999);
      });
      expect(mockWsInstances).toHaveLength(2);
      act(() => {
        jest.advanceTimersByTime(1);
      });
      expect(mockWsInstances).toHaveLength(3);

      act(() => {
        latestWs().simulateClose(1006);
      });

      // Retry 3: 4000ms
      act(() => {
        jest.advanceTimersByTime(4000);
      });
      expect(mockWsInstances).toHaveLength(4);

      act(() => {
        latestWs().simulateClose(1006);
      });

      // Retry 4: 8000ms
      act(() => {
        jest.advanceTimersByTime(8000);
      });
      expect(mockWsInstances).toHaveLength(5);

      act(() => {
        latestWs().simulateClose(1006);
      });

      // Retry 5: 16000ms
      act(() => {
        jest.advanceTimersByTime(16000);
      });
      expect(mockWsInstances).toHaveLength(6);

      // The fifth retry also fails — should transition to 'error' with no further retries.
      act(() => {
        latestWs().simulateClose(1006);
      });

      expect(hookReturn.result.current.connectionState).toBe('error');

      // Advance far past any plausible delay — no more WS instances should be created.
      act(() => {
        jest.advanceTimersByTime(60_000);
      });
      expect(mockWsInstances).toHaveLength(6);
    });

    it('resets the retry counter on successful reconnection', () => {
      const hookReturn = connectAndHandshake();
      const ws1 = latestWs();

      act(() => {
        ws1.simulateClose(1006);
      });

      // First retry fires after 1s.
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      const ws2 = latestWs();

      // Successful reconnection.
      act(() => {
        ws2.simulateOpen();
      });
      act(() => {
        ws2.simulateMessage({
          type: BrowserMessageType.CONNECTION_ESTABLISHED,
          session_id: 'sess-001-again',
          profile: 'browser',
        });
      });
      expect(hookReturn.result.current.connectionState).toBe('connected');

      // Another abnormal close — retry counter should have been reset.
      act(() => {
        ws2.simulateClose(1006);
      });

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      // A fresh ws should have been created (delay = 1s again, confirming reset).
      expect(mockWsInstances.length).toBeGreaterThanOrEqual(3);
    });
  });

  // -----------------------------------------------------------------------
  // User-initiated disconnect
  // -----------------------------------------------------------------------
  describe('user-initiated disconnect', () => {
    it('closes with code 1000 and does not attempt reconnection', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      act(() => {
        hookReturn.result.current.disconnect();
      });

      expect(ws.closeCalls).toHaveLength(1);
      expect(ws.closeCalls[0].code).toBe(1000);

      act(() => {
        ws.simulateClose(1000, 'User disconnect');
      });

      expect(hookReturn.result.current.connectionState).toBe('disconnected');

      act(() => {
        jest.advanceTimersByTime(60_000);
      });
      expect(mockWsInstances).toHaveLength(1);
      expect(hookReturn.result.current.connectionState).toBe('disconnected');
    });

    it('clears any pending reconnect timer', () => {
      const hookReturn = connectAndHandshake();
      const ws1 = latestWs();

      // Abnormal close schedules a reconnect.
      act(() => {
        ws1.simulateClose(1006);
      });

      // User disconnects before the timer fires.
      act(() => {
        hookReturn.result.current.disconnect();
      });

      act(() => {
        jest.advanceTimersByTime(60_000);
      });
      expect(mockWsInstances).toHaveLength(1);
    });
  });

  // -----------------------------------------------------------------------
  // Out-of-order BROWSER_ACTION_* matched by stepNumber
  // -----------------------------------------------------------------------
  describe('out-of-order BROWSER_ACTION_*', () => {
    it('matches interleaved START/COMPLETE pairs purely by stepNumber', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      // Two START frames in order.
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_START,
          actionType: 'browser',
          details: 'step-1',
          stepNumber: 1,
        });
      });
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_START,
          actionType: 'browser',
          details: 'step-2',
          stepNumber: 2,
        });
      });

      // COMPLETE for step 2 arrives BEFORE step 1's complete.
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_COMPLETE,
          actionType: 'browser',
          result: 'step-2 result',
          success: true,
          stepNumber: 2,
          currentUrl: 'https://example.com/2',
        });
      });
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_COMPLETE,
          actionType: 'browser',
          result: 'step-1 result',
          success: true,
          stepNumber: 1,
          currentUrl: 'https://example.com/1',
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      const step1 = assistant?.actions?.find((a) => a.stepNumber === 1);
      const step2 = assistant?.actions?.find((a) => a.stepNumber === 2);

      expect(step1?.status).toBe('succeeded');
      expect(step1?.result).toBe('step-1 result');
      expect(step2?.status).toBe('succeeded');
      expect(step2?.result).toBe('step-2 result');
    });

    it('synthesizes a terminal entry when COMPLETE arrives before its START', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      // COMPLETE with no prior START.
      act(() => {
        ws.simulateMessage({
          type: BrowserMessageType.BROWSER_ACTION_COMPLETE,
          actionType: 'browser',
          result: 'orphan result',
          success: true,
          stepNumber: 99,
          currentUrl: 'https://example.com/orphan',
        });
      });

      const assistant = hookReturn.result.current.messages.find((m) => m.role === 'assistant');
      const orphan = assistant?.actions?.find((a) => a.stepNumber === 99);
      expect(orphan).toBeDefined();
      expect(orphan?.status).toBe('succeeded');
      expect(orphan?.result).toBe('orphan result');
    });
  });

  // -----------------------------------------------------------------------
  // Malformed-JSON handling
  // -----------------------------------------------------------------------
  describe('malformed JSON handling', () => {
    it('swallows malformed frames without mutating state', () => {
      const hookReturn = connectAndHandshake();
      const ws = latestWs();

      const beforeMessages = hookReturn.result.current.messages;
      const beforeSessions = hookReturn.result.current.sessions;
      const beforeState = hookReturn.result.current.connectionState;

      act(() => {
        ws.simulateRawMessage('{"type": "STREAM", "content": '); // truncated JSON
      });
      act(() => {
        ws.simulateRawMessage('not json at all');
      });

      // No state change.
      expect(hookReturn.result.current.messages).toBe(beforeMessages);
      expect(hookReturn.result.current.sessions).toBe(beforeSessions);
      expect(hookReturn.result.current.connectionState).toBe(beforeState);
    });
  });
});
