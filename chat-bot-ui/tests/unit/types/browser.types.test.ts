// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Browser Types Tests
 *
 * Validates the browser-profile TypeScript definitions:
 *   1. Every BrowserMessageType constant value equals its key name (backend parity)
 *   2. Discriminated-union narrowing compiles for representative server + client frames
 *   3. BrowserChatMessage accepts optional screenshots, actions, hitlPrompt
 *   4. The initial BrowserSessionState shape matches the spec design
 */

import {
  BrowserMessageType,
  BrowserChatMessage,
  BrowserSessionState,
  BrowserServerMessage,
  BrowserClientMessage,
  BrowserScreenshotMessage,
  BrowserHitlResponseMessage,
  BrowserScreenshotEntry,
  BrowserActionEntry,
  BrowserHitlPromptEntry,
} from '../../../src/types/browser.types';

describe('Browser Types', () => {
  describe('BrowserMessageType constants', () => {
    test('every constant value equals its key name (backend parity)', () => {
      const entries = Object.entries(BrowserMessageType);

      // Sanity: 9 client + 11 shared-server + 8 browser-specific-server = 28 total
      expect(entries).toHaveLength(28);

      entries.forEach(([key, value]) => {
        expect(value).toBe(key);
      });
    });

    test('contains all 9 client → server frame types', () => {
      expect(BrowserMessageType.CONNECTION_INIT).toBe('CONNECTION_INIT');
      expect(BrowserMessageType.CHAT_MESSAGE).toBe('CHAT_MESSAGE');
      expect(BrowserMessageType.BROWSER_STOP).toBe('BROWSER_STOP');
      expect(BrowserMessageType.BROWSER_HITL_RESPONSE).toBe('BROWSER_HITL_RESPONSE');
      expect(BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST).toBe('BROWSER_LIVE_VIEW_REQUEST');
      expect(BrowserMessageType.NEW_SESSION).toBe('NEW_SESSION');
      expect(BrowserMessageType.RESUME_SESSION).toBe('RESUME_SESSION');
      expect(BrowserMessageType.GET_SESSIONS).toBe('GET_SESSIONS');
      expect(BrowserMessageType.DELETE_SESSION).toBe('DELETE_SESSION');
    });

    test('contains all 8 browser-specific server → client frame types', () => {
      expect(BrowserMessageType.BROWSER_SESSION_STARTED).toBe('BROWSER_SESSION_STARTED');
      expect(BrowserMessageType.BROWSER_ACTION_START).toBe('BROWSER_ACTION_START');
      expect(BrowserMessageType.BROWSER_SCREENSHOT).toBe('BROWSER_SCREENSHOT');
      expect(BrowserMessageType.BROWSER_ACTION_COMPLETE).toBe('BROWSER_ACTION_COMPLETE');
      expect(BrowserMessageType.BROWSER_HITL_PROMPT).toBe('BROWSER_HITL_PROMPT');
      expect(BrowserMessageType.BROWSER_HITL_TIMEOUT).toBe('BROWSER_HITL_TIMEOUT');
      expect(BrowserMessageType.BROWSER_LIVE_VIEW_URL).toBe('BROWSER_LIVE_VIEW_URL');
      expect(BrowserMessageType.BROWSER_SESSION_ENDED).toBe('BROWSER_SESSION_ENDED');
    });
  });

  describe('Discriminated-union narrowing', () => {
    test('narrows BrowserServerMessage via switch on `type` (BROWSER_SCREENSHOT)', () => {
      const msg: BrowserServerMessage = {
        type: BrowserMessageType.BROWSER_SCREENSHOT,
        screenshotPath: 's3://amzn-s3-demo-bucket/key.png',
        screenshotUrl: 'https://signed.example/url.png',
        timestamp: 1_700_000_000_000,
        title: 'After click',
        stepNumber: 3,
      };

      switch (msg.type) {
        case BrowserMessageType.BROWSER_SCREENSHOT: {
          const narrowed: BrowserScreenshotMessage = msg;
          expect(narrowed.stepNumber).toBe(3);
          expect(narrowed.title).toBe('After click');
          expect(narrowed.screenshotUrl).toBe('https://signed.example/url.png');
          expect(narrowed.screenshotPath).toBe('s3://amzn-s3-demo-bucket/key.png');
          expect(narrowed.timestamp).toBe(1_700_000_000_000);
          break;
        }
        default:
          throw new Error('expected BROWSER_SCREENSHOT narrowing to match');
      }
    });

    test('narrows BrowserClientMessage via switch on `type` (BROWSER_HITL_RESPONSE)', () => {
      const msg: BrowserClientMessage = {
        type: BrowserMessageType.BROWSER_HITL_RESPONSE,
        promptId: 'prompt-123',
        action: 'approve',
        value: 'continue',
      };

      switch (msg.type) {
        case BrowserMessageType.BROWSER_HITL_RESPONSE: {
          const narrowed: BrowserHitlResponseMessage = msg;
          expect(narrowed.promptId).toBe('prompt-123');
          expect(narrowed.action).toBe('approve');
          expect(narrowed.value).toBe('continue');
          break;
        }
        default:
          throw new Error('expected BROWSER_HITL_RESPONSE narrowing to match');
      }
    });
  });

  describe('BrowserChatMessage optional fields', () => {
    test('accepts minimal message without any browser-specific fields', () => {
      const minimal: BrowserChatMessage = {
        id: 'msg-1',
        role: 'assistant',
        content: 'Hello',
        timestamp: '2025-01-01T00:00:00Z',
      };

      expect(minimal.screenshots).toBeUndefined();
      expect(minimal.actions).toBeUndefined();
      expect(minimal.hitlPrompt).toBeUndefined();
    });

    test('accepts message with all three optional fields populated', () => {
      const screenshot: BrowserScreenshotEntry = {
        stepNumber: 1,
        screenshotUrl: 'https://signed.example/shot.png',
        screenshotPath: 's3://amzn-s3-demo-bucket/shot.png',
        title: 'Landing page',
        timestamp: 1_700_000_000_000,
      };

      const action: BrowserActionEntry = {
        stepNumber: 1,
        actionType: 'browser',
        details: 'navigate to https://example.com',
        status: 'succeeded',
        result: 'ok',
      };

      const hitlPrompt: BrowserHitlPromptEntry = {
        promptId: 'prompt-1',
        question: 'Proceed?',
        options: ['yes', 'no'],
        context: 'confirming navigation',
        status: 'pending',
      };

      const full: BrowserChatMessage = {
        id: 'msg-2',
        role: 'assistant',
        content: 'Working on it...',
        timestamp: '2025-01-01T00:00:00Z',
        screenshots: [screenshot],
        actions: [action],
        hitlPrompt,
      };

      expect(full.screenshots).toEqual([screenshot]);
      expect(full.actions).toEqual([action]);
      expect(full.hitlPrompt).toEqual(hitlPrompt);
    });

    test('accepts empty arrays for screenshots and actions', () => {
      const msg: BrowserChatMessage = {
        id: 'msg-3',
        role: 'assistant',
        content: '',
        timestamp: '2025-01-01T00:00:00Z',
        screenshots: [],
        actions: [],
      };

      expect(msg.screenshots).toEqual([]);
      expect(msg.actions).toEqual([]);
    });
  });

  describe('BrowserSessionState initial shape', () => {
    test('matches spec design: isActive=false, liveViewUrl=null, stepCounter=0, pendingHitl=null', () => {
      const INITIAL_BROWSER_SESSION: BrowserSessionState = {
        isActive: false,
        liveViewUrl: null,
        stepCounter: 0,
        pendingHitl: null,
      };

      expect(INITIAL_BROWSER_SESSION.isActive).toBe(false);
      expect(INITIAL_BROWSER_SESSION.liveViewUrl).toBeNull();
      expect(INITIAL_BROWSER_SESSION.stepCounter).toBe(0);
      expect(INITIAL_BROWSER_SESSION.pendingHitl).toBeNull();
    });

    test('accepts populated state with live view URL and pending HITL', () => {
      const pending: BrowserHitlPromptEntry = {
        promptId: 'prompt-1',
        question: 'Continue?',
        options: ['yes', 'no'],
        context: '',
        status: 'pending',
      };

      const active: BrowserSessionState = {
        isActive: true,
        liveViewUrl: 'https://dcv.example/live',
        stepCounter: 5,
        pendingHitl: pending,
      };

      expect(active.isActive).toBe(true);
      expect(active.liveViewUrl).toBe('https://dcv.example/live');
      expect(active.stepCounter).toBe(5);
      expect(active.pendingHitl).toEqual(pending);
    });
  });
});
