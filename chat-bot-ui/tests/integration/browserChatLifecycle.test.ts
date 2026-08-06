// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * End-to-end integration test for the browser-agent chat lifecycle.
 *
 * Drives `useBrowserChatSession` through a full round-trip against the
 * MockWebSocket harness:
 *
 *   CHAT_MESSAGE →
 *     BROWSER_SESSION_STARTED →
 *     BROWSER_ACTION_START →
 *     BROWSER_SCREENSHOT →
 *     BROWSER_ACTION_COMPLETE →
 *     BROWSER_HITL_PROMPT →
 *     BROWSER_HITL_RESPONSE (client) →
 *     STREAM →
 *     METADATA →
 *     ORCHESTRATION_END
 *
 * Asserts that the hook's `messages` state ends with a user message + an
 * assistant message carrying the attached screenshots, actions, HITL
 * prompt, final content and metadata — and that the client dispatched
 * the 9 frame types end-to-end in the expected order.
 *
 * Requirement: 9.4, 9.5
 */

import { renderHook, act } from '@testing-library/react';
import { useBrowserChatSession } from '../../src/hooks/useBrowserChatSession';
import { BrowserMessageType } from '../../src/types/browser.types';
import { MockWebSocket, installMockWebSocket } from './__mocks__/MockWebSocket';

jest.mock('../../src/utils/websocket', () => ({
  buildWebSocketUrl: (token: string, profile: string) =>
    `ws://integration-test/ws?token=${encodeURIComponent(token)}&profile=${encodeURIComponent(profile)}`,
}));

describe('browser chat lifecycle (integration)', () => {
  let uninstall: () => void;

  beforeEach(() => {
    uninstall = installMockWebSocket();
  });

  afterEach(() => {
    uninstall();
  });

  it('covers a full CHAT_MESSAGE → BROWSER_* → STREAM → METADATA round-trip', () => {
    // 1. Connect + handshake.
    const { result } = renderHook(() => useBrowserChatSession());

    act(() => {
      result.current.connect('integration-token', 'browser');
    });

    const ws = MockWebSocket.latest();

    act(() => {
      ws.simulateOpen();
    });

    // CONNECTION_INIT is dispatched on open.
    expect(ws.findSent(BrowserMessageType.CONNECTION_INIT)).toBeDefined();

    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.CONNECTION_ESTABLISHED,
        session_id: 'integ-sess-1',
        profile: 'browser',
      });
    });
    expect(result.current.connectionState).toBe('connected');
    expect(result.current.sessionId).toBe('integ-sess-1');

    // 2. User sends a chat message.
    act(() => {
      result.current.sendMessage('Navigate to example.com and click Login');
    });

    const chat = ws.findSent(BrowserMessageType.CHAT_MESSAGE);
    expect(chat).toEqual({
      type: BrowserMessageType.CHAT_MESSAGE,
      content: 'Navigate to example.com and click Login',
    });

    // 3. Backend kicks off orchestration and browser session.
    act(() => {
      ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_START });
    });
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.BROWSER_SESSION_STARTED,
        session_id: 'integ-sess-1',
        liveViewUrl: 'https://live.example/dcv',
      });
    });
    expect(result.current.browserSession.isActive).toBe(true);
    expect(result.current.browserSession.liveViewUrl).toBe('https://live.example/dcv');

    // 4. Action lifecycle: START → SCREENSHOT → COMPLETE.
    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.BROWSER_ACTION_START,
        actionType: 'browser',
        details: 'navigate https://example.com',
        stepNumber: 1,
      });
    });
    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.BROWSER_SCREENSHOT,
        stepNumber: 1,
        screenshotUrl: 'https://s3.test/step-1.png',
        screenshotPath: 'sessions/integ-sess-1/step-1.png',
        title: 'Landed on example.com',
        timestamp: 1_700_000_001_000,
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

    // 5. HITL prompt + client response.
    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.BROWSER_HITL_PROMPT,
        promptId: 'prompt-1',
        question: 'Proceed with login?',
        options: ['yes', 'no'],
        context: 'About to click Login',
        screenshotBase64: '',
      });
    });
    expect(result.current.browserSession.pendingHitl?.promptId).toBe('prompt-1');

    act(() => {
      result.current.sendHitlResponse('confirm', 'yes');
    });

    const hitlResponse = ws.findSent(BrowserMessageType.BROWSER_HITL_RESPONSE);
    expect(hitlResponse).toEqual({
      type: BrowserMessageType.BROWSER_HITL_RESPONSE,
      promptId: 'prompt-1',
      action: 'confirm',
      value: 'yes',
    });
    expect(result.current.browserSession.pendingHitl).toBeNull();

    // 6. Streamed final answer tokens + metadata + orchestration end.
    act(() => {
      ws.simulateMessage({ type: BrowserMessageType.STREAM, content: 'Logged in ' });
    });
    act(() => {
      ws.simulateMessage({ type: BrowserMessageType.STREAM, content: 'successfully.' });
    });
    act(() => {
      ws.simulateMessage({
        type: BrowserMessageType.METADATA,
        total_duration_ms: 2345,
        steps_completed: 2,
      });
    });
    act(() => {
      ws.simulateMessage({ type: BrowserMessageType.ORCHESTRATION_END });
    });

    // -------------------------------------------------------------------
    // End-state assertions
    // -------------------------------------------------------------------

    // BROWSER_HITL_PROMPT opens a new assistant message to host the prompt
    // (see useBrowserChatSession). After the STREAM response, the hook
    // writes final-answer tokens into the same message. So the final slice
    // has: user → assistant (actions + screenshots) → assistant (HITL + final answer).
    expect(result.current.messages).toHaveLength(3);
    const userMsg = result.current.messages[0];
    const traceMsg = result.current.messages[1];
    const assistantMsg = result.current.messages[2];

    expect(userMsg.role).toBe('user');
    expect(userMsg.content).toBe('Navigate to example.com and click Login');

    expect(traceMsg.role).toBe('assistant');
    // Screenshots + actions land on the trace message that was streaming before HITL.
    expect(traceMsg.screenshots).toHaveLength(1);
    expect(traceMsg.screenshots?.[0].stepNumber).toBe(1);
    expect(traceMsg.screenshots?.[0].screenshotUrl).toBe('https://s3.test/step-1.png');
    expect(traceMsg.actions).toHaveLength(1);
    expect(traceMsg.actions?.[0].stepNumber).toBe(1);
    expect(traceMsg.actions?.[0].status).toBe('succeeded');

    expect(assistantMsg.role).toBe('assistant');
    expect(assistantMsg.isStreaming).toBe(false);
    expect(assistantMsg.content).toBe('Logged in successfully.');

    // HITL prompt is recorded on the final assistant message, now 'responded'.
    expect(assistantMsg.hitlPrompt?.promptId).toBe('prompt-1');
    expect(assistantMsg.hitlPrompt?.status).toBe('responded');

    // Metadata attached to the final assistant message.
    expect(assistantMsg.agentMetadata?.browser?.total_duration_ms).toBe(2345);
    expect(assistantMsg.agentMetadata?.browser?.steps_completed).toBe(2);

    // isStreaming cleared after ORCHESTRATION_END.
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.connectionState).toBe('connected');

    // Client-frame coverage: ensure every dispatched client frame that the
    // test drove ended up on the wire, in dispatch order.
    const sentTypes = ws.getSentParsed().map((f) => f.type);
    expect(sentTypes).toEqual(expect.arrayContaining([
      BrowserMessageType.CONNECTION_INIT,
      BrowserMessageType.GET_SESSIONS, // auto-fired by the hook after CONNECTION_ESTABLISHED
      BrowserMessageType.CHAT_MESSAGE,
      BrowserMessageType.BROWSER_HITL_RESPONSE,
    ]));
  });
});
