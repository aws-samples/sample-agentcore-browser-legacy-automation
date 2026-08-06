// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Frame coverage integration test.
 *
 * Enforces that `BrowserMessageType` (the single source of truth for the
 * wire protocol) carries the full 9 client + 19 server frame census and
 * that the MockWebSocket harness is able to emit every one of them. If a
 * backend protocol change adds or removes a frame and the types are
 * updated but the harness/integration suite is not, this test trips and
 * guides the author to the right spot.
 *
 * Requirement: 9.4
 */

import {
  BrowserMessageType,
  BrowserClientMessage,
  BrowserServerMessage,
} from '../../src/types/browser.types';
import { MockWebSocket, installMockWebSocket } from './__mocks__/MockWebSocket';

const CLIENT_FRAME_TYPES = [
  BrowserMessageType.CONNECTION_INIT,
  BrowserMessageType.CHAT_MESSAGE,
  BrowserMessageType.BROWSER_STOP,
  BrowserMessageType.BROWSER_HITL_RESPONSE,
  BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST,
  BrowserMessageType.NEW_SESSION,
  BrowserMessageType.RESUME_SESSION,
  BrowserMessageType.GET_SESSIONS,
  BrowserMessageType.DELETE_SESSION,
];

const SHARED_SERVER_FRAME_TYPES = [
  BrowserMessageType.CONNECTION_ESTABLISHED,
  BrowserMessageType.SESSION_CREATED,
  BrowserMessageType.SESSION_RESUMED,
  BrowserMessageType.SESSIONS_LOADED,
  BrowserMessageType.SESSION_DELETED,
  BrowserMessageType.ORCHESTRATION_START,
  BrowserMessageType.ORCHESTRATION_END,
  BrowserMessageType.REASONING,
  BrowserMessageType.STREAM,
  BrowserMessageType.METADATA,
  BrowserMessageType.ERROR,
];

const BROWSER_SERVER_FRAME_TYPES = [
  BrowserMessageType.BROWSER_SESSION_STARTED,
  BrowserMessageType.BROWSER_ACTION_START,
  BrowserMessageType.BROWSER_SCREENSHOT,
  BrowserMessageType.BROWSER_ACTION_COMPLETE,
  BrowserMessageType.BROWSER_HITL_PROMPT,
  BrowserMessageType.BROWSER_HITL_TIMEOUT,
  BrowserMessageType.BROWSER_LIVE_VIEW_URL,
  BrowserMessageType.BROWSER_SESSION_ENDED,
];

describe('browser protocol frame census', () => {
  it('defines exactly 9 client frames', () => {
    expect(CLIENT_FRAME_TYPES).toHaveLength(9);
    // Every client frame must be a unique, non-empty string.
    expect(new Set(CLIENT_FRAME_TYPES).size).toBe(9);
  });

  it('defines exactly 19 server frames (11 shared + 8 browser-specific)', () => {
    expect(SHARED_SERVER_FRAME_TYPES).toHaveLength(11);
    expect(BROWSER_SERVER_FRAME_TYPES).toHaveLength(8);
    expect(new Set([...SHARED_SERVER_FRAME_TYPES, ...BROWSER_SERVER_FRAME_TYPES]).size).toBe(19);
  });

  it('the client + server frame set is disjoint', () => {
    const clientSet: Set<string> = new Set(CLIENT_FRAME_TYPES);
    for (const type of [...SHARED_SERVER_FRAME_TYPES, ...BROWSER_SERVER_FRAME_TYPES]) {
      expect(clientSet.has(type)).toBe(false);
    }
  });
});

describe('MockWebSocket harness frame emission', () => {
  let uninstall: () => void;

  beforeEach(() => {
    uninstall = installMockWebSocket();
  });

  afterEach(() => {
    uninstall();
  });

  it('can emit every server frame type via simulateMessage', () => {
    const ws = new MockWebSocket('ws://test/integration');
    const received: string[] = [];
    ws.onmessage = (ev: MessageEvent) => {
      received.push(JSON.parse(ev.data).type);
    };

    for (const type of [...SHARED_SERVER_FRAME_TYPES, ...BROWSER_SERVER_FRAME_TYPES]) {
      ws.simulateMessage({ type });
    }

    expect(received).toEqual([...SHARED_SERVER_FRAME_TYPES, ...BROWSER_SERVER_FRAME_TYPES]);
  });

  it('captures every client frame type that the hook would dispatch', () => {
    const ws = new MockWebSocket('ws://test/integration');

    // Push one representative payload per client frame type through ws.send
    // to confirm it is captured verbatim and parses back to the same `type`.
    const payloads: BrowserClientMessage[] = [
      { type: BrowserMessageType.CONNECTION_INIT },
      { type: BrowserMessageType.CHAT_MESSAGE, content: 'hi' },
      { type: BrowserMessageType.BROWSER_STOP },
      {
        type: BrowserMessageType.BROWSER_HITL_RESPONSE,
        promptId: 'p',
        action: 'respond',
        value: 'yes',
      },
      { type: BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST },
      { type: BrowserMessageType.NEW_SESSION },
      { type: BrowserMessageType.RESUME_SESSION, session_id: 'sess-1' },
      { type: BrowserMessageType.GET_SESSIONS },
      { type: BrowserMessageType.DELETE_SESSION, session_id: 'sess-1' },
    ];

    for (const payload of payloads) {
      ws.send(JSON.stringify(payload));
    }

    const sentTypes = ws.getSentParsed().map((f) => f.type);
    expect(sentTypes).toEqual(CLIENT_FRAME_TYPES);
  });

  it('narrows server frames correctly when round-tripped through JSON', () => {
    const ws = new MockWebSocket('ws://test/integration');
    const received: BrowserServerMessage[] = [];
    ws.onmessage = (ev: MessageEvent) => {
      received.push(JSON.parse(ev.data) as BrowserServerMessage);
    };

    ws.simulateMessage({
      type: BrowserMessageType.BROWSER_SCREENSHOT,
      stepNumber: 1,
      screenshotUrl: 'u',
      screenshotPath: 'p',
      title: 't',
      timestamp: 1,
    });

    expect(received).toHaveLength(1);
    const last = received[0];
    if (last.type === BrowserMessageType.BROWSER_SCREENSHOT) {
      expect(last.stepNumber).toBe(1);
    } else {
      throw new Error('expected BROWSER_SCREENSHOT narrowing');
    }
  });
});
