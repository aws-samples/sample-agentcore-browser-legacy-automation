// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Unit tests for browserSteps pure helper.
 *
 * Covers:
 *  - empty message → empty grouping
 *  - action-only messages produce one step per action, sorted by stepNumber
 *  - screenshots attach to matching action stepNumber
 *  - orphan screenshots (no matching action) produce screenshot-only steps
 *  - HITL prompts produce a waiting-for-user step appended after last action
 *  - reasoning blob is split on double-newline and distributed in order
 *  - trailing reasoning (more chunks than actions) is surfaced separately
 *  - final answer (message.content) is returned on `finalAnswer`
 *  - isStepDefaultExpanded returns true only for screenshot steps
 *  - isTraceDefaultExpanded returns false always
 */

import {
  groupMessageIntoSteps,
  isStepDefaultExpanded,
  isTraceDefaultExpanded,
} from '../../../src/utils/browserSteps';
import type {
  BrowserChatMessage,
  BrowserActionEntry,
  BrowserScreenshotEntry,
  BrowserHitlPromptEntry,
} from '../../../src/types/browser.types';

const makeAction = (
  stepNumber: number,
  overrides: Partial<BrowserActionEntry> = {},
): BrowserActionEntry => ({
  stepNumber,
  actionType: 'browser',
  details: `action ${stepNumber}`,
  status: 'succeeded',
  ...overrides,
});

const makeShot = (
  stepNumber: number,
  overrides: Partial<BrowserScreenshotEntry> = {},
): BrowserScreenshotEntry => ({
  stepNumber,
  screenshotUrl: `https://s3.test/${stepNumber}.png`,
  screenshotPath: `sessions/abc/step-${stepNumber}.png`,
  title: `shot-${stepNumber}`,
  timestamp: 1_700_000_000_000 + stepNumber,
  ...overrides,
});

const makeHitl = (
  overrides: Partial<BrowserHitlPromptEntry> = {},
): BrowserHitlPromptEntry => ({
  promptId: 'p1',
  question: 'Proceed?',
  options: ['yes', 'no'],
  context: '',
  status: 'pending',
  ...overrides,
});

const baseMessage = (overrides: Partial<BrowserChatMessage> = {}): BrowserChatMessage => ({
  id: 'm1',
  role: 'assistant',
  content: '',
  timestamp: '2026-04-29T21:00:00Z',
  ...overrides,
});

describe('groupMessageIntoSteps', () => {
  it('returns an empty grouping for a bare assistant message', () => {
    const g = groupMessageIntoSteps(baseMessage());
    expect(g.steps).toEqual([]);
    expect(g.trailingReasoning).toBe('');
    expect(g.finalAnswer).toBe('');
  });

  it('produces one step per action, sorted by stepNumber ascending', () => {
    const msg = baseMessage({
      actions: [makeAction(3), makeAction(1), makeAction(2)],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps.map((s) => s.stepNumber)).toEqual([1, 2, 3]);
    expect(g.steps.every((s) => s.action)).toBe(true);
  });

  it('attaches a screenshot to the matching action stepNumber', () => {
    const msg = baseMessage({
      actions: [makeAction(1)],
      screenshots: [makeShot(1, { title: 'after-click' })],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps).toHaveLength(1);
    expect(g.steps[0].action).toBeDefined();
    expect(g.steps[0].screenshot).toBeDefined();
    expect(g.steps[0].screenshot?.title).toBe('after-click');
  });

  it('produces a screenshot-only step when no matching action exists', () => {
    const msg = baseMessage({
      actions: [makeAction(1)],
      screenshots: [makeShot(5, { title: 'orphan-shot' })],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps).toHaveLength(2);
    const orphan = g.steps.find((s) => s.stepNumber === 5);
    expect(orphan).toBeDefined();
    expect(orphan?.action).toBeUndefined();
    expect(orphan?.screenshot?.title).toBe('orphan-shot');
    expect(orphan?.status).toBe('screenshot');
    expect(orphan?.summary).toBe('orphan-shot');
  });

  it('handles an orphan screenshot with empty title by using a default summary', () => {
    const msg = baseMessage({
      screenshots: [makeShot(1, { title: '' })],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps).toHaveLength(1);
    expect(g.steps[0].summary).toBe('Screenshot');
  });

  it('appends a waiting-for-user step when a HITL prompt is present', () => {
    const msg = baseMessage({
      actions: [makeAction(1), makeAction(2)],
      hitlPrompt: makeHitl({ question: 'Need your input' }),
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps).toHaveLength(3);
    const last = g.steps[2];
    expect(last.stepNumber).toBe(3); // lastAction.stepNumber + 1
    expect(last.status).toBe('waiting-for-user');
    expect(last.hitl).toBeDefined();
    expect(last.summary).toBe('Need your input');
  });

  it('HITL without any prior actions lands at step 1', () => {
    const msg = baseMessage({
      hitlPrompt: makeHitl({ question: 'Q?' }),
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps).toHaveLength(1);
    expect(g.steps[0].stepNumber).toBe(1);
    expect(g.steps[0].status).toBe('waiting-for-user');
  });

  it('distributes reasoning blob across action steps on double-newline boundaries', () => {
    const reasoning = 'First thought.\n\nSecond thought.\n\nThird thought.';
    const msg = baseMessage({
      actions: [makeAction(1), makeAction(2), makeAction(3)],
      agentMetadata: { browser: { reasoning } },
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].reasoning).toBe('First thought.');
    expect(g.steps[1].reasoning).toBe('Second thought.');
    expect(g.steps[2].reasoning).toBe('Third thought.');
    expect(g.trailingReasoning).toBe('');
  });

  it('surfaces trailing reasoning when there are more chunks than actions', () => {
    const reasoning = 'One.\n\nTwo.\n\nThree.\n\nFour.';
    const msg = baseMessage({
      actions: [makeAction(1), makeAction(2)],
      agentMetadata: { browser: { reasoning } },
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].reasoning).toBe('One.');
    expect(g.steps[1].reasoning).toBe('Two.');
    expect(g.trailingReasoning).toBe('Three.\n\nFour.');
  });

  it('handles reasoning with fewer chunks than actions without crashing', () => {
    const msg = baseMessage({
      actions: [makeAction(1), makeAction(2), makeAction(3)],
      agentMetadata: { browser: { reasoning: 'Only one thought.' } },
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].reasoning).toBe('Only one thought.');
    expect(g.steps[1].reasoning).toBe('');
    expect(g.steps[2].reasoning).toBe('');
    expect(g.trailingReasoning).toBe('');
  });

  it('treats empty / whitespace-only reasoning as no reasoning', () => {
    const msg = baseMessage({
      actions: [makeAction(1)],
      agentMetadata: { browser: { reasoning: '   \n\n   ' } },
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].reasoning).toBe('');
    expect(g.trailingReasoning).toBe('');
  });

  it('passes message.content through as finalAnswer', () => {
    const msg = baseMessage({
      content: 'Here is the final answer with details.',
      actions: [makeAction(1)],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.finalAnswer).toBe('Here is the final answer with details.');
  });

  it('maps action status to step status (running/succeeded/failed)', () => {
    const msg = baseMessage({
      actions: [
        makeAction(1, { status: 'succeeded' }),
        makeAction(2, { status: 'failed' }),
        makeAction(3, { status: 'running' }),
      ],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].status).toBe('succeeded');
    expect(g.steps[1].status).toBe('failed');
    expect(g.steps[2].status).toBe('running');
  });

  it('truncates a very long action details into the summary with an ellipsis', () => {
    const long = 'x'.repeat(120);
    const msg = baseMessage({
      actions: [makeAction(1, { details: long })],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].summary.endsWith('…')).toBe(true);
    expect(g.steps[0].summary.length).toBeLessThanOrEqual(81);
  });

  it('falls back to actionType in summary when details is empty', () => {
    const msg = baseMessage({
      actions: [makeAction(1, { details: '', actionType: 'navigate' })],
    });
    const g = groupMessageIntoSteps(msg);
    expect(g.steps[0].summary).toBe('navigate');
  });
});

describe('isStepDefaultExpanded', () => {
  it('returns true for a step with a screenshot', () => {
    const step = groupMessageIntoSteps(
      baseMessage({
        actions: [makeAction(1)],
        screenshots: [makeShot(1)],
      }),
    ).steps[0];
    expect(isStepDefaultExpanded(step)).toBe(true);
  });

  it('returns true for an orphan screenshot step', () => {
    const step = groupMessageIntoSteps(
      baseMessage({
        screenshots: [makeShot(1)],
      }),
    ).steps[0];
    expect(isStepDefaultExpanded(step)).toBe(true);
  });

  it('returns false for an action step without a screenshot', () => {
    const step = groupMessageIntoSteps(
      baseMessage({
        actions: [makeAction(1)],
      }),
    ).steps[0];
    expect(isStepDefaultExpanded(step)).toBe(false);
  });

  it('returns false for a waiting-for-user HITL step', () => {
    const step = groupMessageIntoSteps(
      baseMessage({
        hitlPrompt: makeHitl(),
      }),
    ).steps[0];
    expect(isStepDefaultExpanded(step)).toBe(false);
  });
});

describe('isTraceDefaultExpanded', () => {
  it('always returns false — the trace stays collapsed by default', () => {
    const emptyGrouping = groupMessageIntoSteps(baseMessage());
    expect(isTraceDefaultExpanded(emptyGrouping, false)).toBe(false);
    expect(isTraceDefaultExpanded(emptyGrouping, true)).toBe(false);

    const activeGrouping = groupMessageIntoSteps(
      baseMessage({
        actions: [makeAction(1, { status: 'running' })],
      }),
    );
    expect(isTraceDefaultExpanded(activeGrouping, true)).toBe(false);
  });
});
