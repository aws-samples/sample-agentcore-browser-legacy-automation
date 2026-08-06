// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ReasoningTrace — Collapsible wrapper that bundles all browser-agent step
 * cards for a single assistant turn into one unit.
 *
 * The trace has two states:
 *   - Collapsed (default) — shows only a one-line summary: "🧠 Reasoning &
 *     actions · N steps · status indicator". Clicking expands the trace.
 *   - Expanded — shows all step cards in order, followed by any trailing
 *     reasoning that did not line up with an action.
 *
 * UX rules (per product decision, 2026-04-29):
 *   - Trace is collapsed by default.
 *   - Trace remains collapsed when an error or HITL is engaged — the user
 *     opts in to auditing the trace, the UI does not force it on them.
 *   - Trace remains collapsed while streaming — users can still open it
 *     mid-stream by clicking the header.
 *
 * The trace header surfaces the running status subtly (a small pulsing
 * dot) so users can see that work is happening without having to expand.
 *
 * @module components/browser/ReasoningTrace
 */

import React, { useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { BrowserStep } from '../../utils/browserSteps';
import { StepCard } from '../StepCard/StepCard';
import { isStepDefaultExpanded } from '../../utils/browserSteps';
import './ReasoningTrace.css';

export interface ReasoningTraceProps {
  /** Ordered steps for this assistant turn. */
  steps: BrowserStep[];
  /** Reasoning text that had no matching action — rendered at the end of the trace. */
  trailingReasoning?: string;
  /** Whether the turn is still streaming — shown as a subtle running dot. */
  isStreaming?: boolean;
  /** Whether the trace should be open initially. Defaults to false. */
  defaultExpanded?: boolean;
}

/** Count each step's status to drive the header status indicator. */
function countByStatus(steps: BrowserStep[]): { running: number; failed: number; waiting: number } {
  let running = 0;
  let failed = 0;
  let waiting = 0;
  for (const s of steps) {
    if (s.status === 'running') running += 1;
    else if (s.status === 'failed') failed += 1;
    else if (s.status === 'waiting-for-user') waiting += 1;
  }
  return { running, failed, waiting };
}

export const ReasoningTrace: React.FC<ReasoningTraceProps> = ({
  steps,
  trailingReasoning = '',
  isStreaming = false,
  defaultExpanded = false,
}) => {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded);

  if (steps.length === 0 && trailingReasoning.length === 0) {
    return null;
  }

  const { running, failed, waiting } = countByStatus(steps);

  const toggle = () => setExpanded((v) => !v);

  // Short status line that summarizes the trace for the collapsed view.
  const statusBits: string[] = [];
  statusBits.push(`${steps.length} step${steps.length === 1 ? '' : 's'}`);
  if (running > 0) statusBits.push(`${running} running`);
  if (failed > 0) statusBits.push(`${failed} failed`);
  if (waiting > 0) statusBits.push('needs your input');
  const metaText = statusBits.join(' · ');

  return (
    <section
      className={`browser-trace${expanded ? ' browser-trace-open' : ''}`}
      data-testid="browser-reasoning-trace"
      data-expanded={expanded}
    >
      <button
        type="button"
        className="browser-trace-header"
        onClick={toggle}
        aria-expanded={expanded}
        aria-controls="browser-trace-body"
        data-testid="browser-trace-header"
      >
        <ExpandMoreIcon
          className={`browser-trace-caret${expanded ? ' browser-trace-caret-open' : ''}`}
          fontSize="small"
          aria-hidden="true"
        />
        <span className="browser-trace-title">🧠 Reasoning &amp; actions</span>
        <span className="browser-trace-meta">{metaText}</span>
        {isStreaming && (
          <span
            className="browser-trace-running-dot"
            aria-label="Agent is working"
            title="Agent is working"
          />
        )}
      </button>

      {expanded && (
        <div
          className="browser-trace-body"
          id="browser-trace-body"
          data-testid="browser-trace-body"
        >
          {steps.map((step) => (
            <StepCard
              key={step.stepNumber}
              step={step}
              defaultExpanded={isStepDefaultExpanded(step)}
            />
          ))}

          {trailingReasoning.length > 0 && (
            <div
              className="browser-trace-trailing-reasoning"
              data-testid="browser-trace-trailing-reasoning"
            >
              {trailingReasoning}
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default ReasoningTrace;
