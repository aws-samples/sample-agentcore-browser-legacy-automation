// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * browserSteps — Pure helper that groups browser-agent artifacts into
 * a step-card structure suitable for the Step Card UX.
 *
 * The `useBrowserChatSession` hook stores each assistant turn as a flat
 * `BrowserChatMessage` carrying three parallel arrays — `actions[]`,
 * `screenshots[]`, and (optionally) one `hitlPrompt` — plus a free-form
 * `agentMetadata.browser.reasoning` string and a `content` string that
 * holds the synthesized STREAM answer.
 *
 * For the new Step Card UX the view layer needs to render the artifacts
 * grouped by `stepNumber`, with the reasoning text attached to the
 * step it triggered. This module derives that grouped view from the
 * flat shape — no hook changes required.
 *
 * Key decisions:
 * - Reasoning tokens are unstructured; the backend does not attach them
 *   to a particular step. We split the accumulated reasoning string on
 *   double-newline boundaries ("\n\n") to approximate per-step chunks,
 *   then distribute them in order to the action steps that own them.
 *   Any leftover reasoning text that has no matching action becomes
 *   `trailingReasoning` — rendered as free-form text above the final
 *   answer so nothing is lost.
 * - Steps are keyed by `stepNumber`. Screenshots whose `stepNumber`
 *   matches an action entry are attached to that step; orphan
 *   screenshots (no matching action) become their own "screenshot-only"
 *   step so the UI can still render them.
 * - HITL prompts are attached to a synthetic step that carries
 *   `status: 'waiting-for-user'`. If the message's `stepCounter` is
 *   ahead of the last action's step, the HITL step gets that higher
 *   number; otherwise it's appended after the last action.
 * - The final STREAM answer lives on `message.content` as plain text;
 *   we surface it separately as `finalAnswer` so the view can render
 *   it in its own privileged card.
 *
 * This module is intentionally data-only. It does no rendering, imports
 * no React, and has no side effects — it's trivially unit-testable.
 *
 * @module utils/browserSteps
 */

import type {
  BrowserChatMessage,
  BrowserActionEntry,
  BrowserScreenshotEntry,
  BrowserHitlPromptEntry,
} from '../types/browser.types';

/**
 * One logical step in the browser-agent loop: a piece of reasoning paired
 * with the action it produced (plus the screenshot/result it returned, or
 * a HITL prompt if it paused).
 */
export interface BrowserStep {
  /** Step index as reported by the backend (stable across START/COMPLETE). */
  stepNumber: number;
  /** Reasoning text that led to this step. Empty string when absent. */
  reasoning: string;
  /** The underlying action, if this step was a tool call. */
  action?: BrowserActionEntry;
  /** The screenshot captured for this step, if any. */
  screenshot?: BrowserScreenshotEntry;
  /** The HITL prompt this step paused on, if any. */
  hitl?: BrowserHitlPromptEntry;
  /** Unified status — used for visual accent and auto-expand decisions. */
  status: 'running' | 'succeeded' | 'failed' | 'waiting-for-user' | 'screenshot';
  /** A short one-line summary for the step header. */
  summary: string;
}

/** Grouped view of one assistant message, suitable for Step Card rendering. */
export interface BrowserMessageGrouping {
  steps: BrowserStep[];
  /** Reasoning fragments that did not line up with any action — shown
   *  above the final answer so they are not lost. */
  trailingReasoning: string;
  /** The streamed final answer (message.content). */
  finalAnswer: string;
}

/**
 * Split a reasoning blob into per-action chunks on double-newline boundaries.
 * Collapses whitespace-only chunks. Any remainder (more chunks than actions)
 * is joined back with "\n\n" and returned as `trailing`.
 */
function splitReasoning(
  reasoning: string,
  chunkCount: number,
): { chunks: string[]; trailing: string } {
  if (!reasoning || reasoning.trim().length === 0) {
    return { chunks: [], trailing: '' };
  }
  const rawParts = reasoning.split(/\n\s*\n+/).map((p) => p.trim()).filter(Boolean);

  if (rawParts.length <= chunkCount) {
    return { chunks: rawParts, trailing: '' };
  }

  const chunks = rawParts.slice(0, chunkCount);
  const trailing = rawParts.slice(chunkCount).join('\n\n');
  return { chunks, trailing };
}

/**
 * Derive a short one-line step summary from the action details.
 * The backend sends `details` as a short phrase already; we just clip it.
 */
function summarizeAction(action: BrowserActionEntry): string {
  const details = action.details?.trim() ?? '';
  if (details.length === 0) {
    return action.actionType;
  }
  return details.length > 80 ? `${details.slice(0, 80)}…` : details;
}

/**
 * Map an action entry's `status` field to the unified step status.
 */
function actionStatusToStepStatus(
  action: BrowserActionEntry,
): 'running' | 'succeeded' | 'failed' {
  return action.status;
}

/**
 * Group a single assistant message into Step Cards.
 *
 * The grouping is deterministic:
 *   1. Collect all distinct stepNumbers from actions + screenshots + hitl.
 *   2. For each stepNumber, attach the matching action, screenshot, and hitl
 *      (at most one of each) to a step entry.
 *   3. Sort the steps by stepNumber ascending.
 *   4. Split the reasoning blob so each action step gets its chunk in order.
 *
 * @param message The assistant message to group. User messages have no
 *   browser artifacts so the returned grouping will have `steps: []`.
 */
export function groupMessageIntoSteps(
  message: BrowserChatMessage,
): BrowserMessageGrouping {
  const actions = message.actions ?? [];
  const screenshots = message.screenshots ?? [];
  const hitl = message.hitlPrompt;

  // Build a map keyed by stepNumber so we can attach action + screenshot
  // entries that share the same step.
  const stepMap: Map<number, BrowserStep> = new Map();

  for (const action of actions) {
    const step: BrowserStep = {
      stepNumber: action.stepNumber,
      reasoning: '',
      action,
      status: actionStatusToStepStatus(action),
      summary: summarizeAction(action),
    };
    stepMap.set(action.stepNumber, step);
  }

  for (const shot of screenshots) {
    const existing = stepMap.get(shot.stepNumber);
    if (existing) {
      existing.screenshot = shot;
    } else {
      // Orphan screenshot — create a screenshot-only step so we don't lose it.
      stepMap.set(shot.stepNumber, {
        stepNumber: shot.stepNumber,
        reasoning: '',
        screenshot: shot,
        status: 'screenshot',
        summary: shot.title && shot.title.trim().length > 0 ? shot.title : 'Screenshot',
      });
    }
  }

  // Sort by stepNumber ascending.
  const steps: BrowserStep[] = Array.from(stepMap.values()).sort(
    (a, b) => a.stepNumber - b.stepNumber,
  );

  // Attach HITL prompt — prefer a step whose stepNumber is one past the
  // highest existing step (since HITL interrupts the next action). If that
  // slot isn't taken, synthesize a waiting step; otherwise attach to the
  // existing max step.
  if (hitl) {
    const lastStepNumber = steps.length > 0 ? steps[steps.length - 1].stepNumber : 0;
    const hitlStepNumber = lastStepNumber + 1;
    steps.push({
      stepNumber: hitlStepNumber,
      reasoning: '',
      hitl,
      status: 'waiting-for-user',
      summary: hitl.question
        ? hitl.question.length > 80
          ? `${hitl.question.slice(0, 80)}…`
          : hitl.question
        : 'Waiting for your input',
    });
  }

  // Distribute reasoning across action steps in order.
  const actionSteps = steps.filter((s) => s.action !== undefined);
  const reasoningBlob =
    (message.agentMetadata?.browser?.reasoning as string | undefined) ?? '';
  const { chunks: reasoningChunks, trailing: trailingReasoning } = splitReasoning(
    reasoningBlob,
    actionSteps.length,
  );
  for (let i = 0; i < actionSteps.length && i < reasoningChunks.length; i++) {
    actionSteps[i].reasoning = reasoningChunks[i];
  }

  return {
    steps,
    trailingReasoning,
    finalAnswer: message.content ?? '',
  };
}

/**
 * Decide whether a step card should be expanded by default.
 *
 * UX rules (per product decision, 2026-04-29):
 * - Screenshot steps: expanded by default so the thumbnail is immediately visible.
 * - All other steps: collapsed by default.
 *
 * Note: a step carrying both an action and a screenshot is treated as a
 * screenshot step (screenshot thumbnail is the primary thing to show).
 */
export function isStepDefaultExpanded(step: BrowserStep): boolean {
  return step.screenshot !== undefined;
}

/**
 * Decide whether the overall reasoning trace should be expanded by default.
 *
 * UX rules:
 * - Trace stays collapsed by default.
 * - Trace stays collapsed even while streaming — the user opts in.
 * - Trace remains collapsed when an error or HITL is engaged.
 *
 * This is a pure function of the message grouping — the caller is free to
 * override on explicit user interaction.
 */
export function isTraceDefaultExpanded(
  _grouping: BrowserMessageGrouping,
  _isStreaming: boolean,
): boolean {
  return false;
}
