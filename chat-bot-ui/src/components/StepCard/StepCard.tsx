// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * StepCard — One step of the browser agent loop rendered as a collapsible card.
 *
 * A step bundles the three things the agent actually did at a point in time
 * into a single visual unit: the reasoning it produced, the tool action it
 * took (if any), and the artifact it got back — either a screenshot or a
 * HITL prompt, or both.
 *
 * The card has a compact header (always visible) that shows step number,
 * action kind, one-line summary, duration or waiting indicator, and status
 * icon. Clicking the header toggles an expanded body that shows the
 * reasoning text, a screenshot thumbnail (if any), the HITL prompt (if
 * any), and the full tool result (for action steps with non-empty result).
 *
 * UX rules (per product decision, 2026-04-29):
 *   - Cards are collapsed by default.
 *   - Cards whose step holds a screenshot are expanded by default so the
 *     thumbnail is immediately visible without a click.
 *
 * The component is pure — it renders from its props and reports click
 * toggles to local state only. Parent decides step ordering and whether
 * the card lives inside a ReasoningTrace.
 *
 * @module components/browser/StepCard
 */

import React, { useState, useEffect } from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutline';
import ImageOutlinedIcon from '@mui/icons-material/ImageOutlined';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { BrowserStep } from '../../utils/browserSteps';
import { Screenshot } from '../Screenshot/Screenshot';
import './StepCard.css';

export interface StepCardProps {
  /** The step to render. */
  step: BrowserStep;
  /** Initial expanded state — controlled by the parent via `isStepDefaultExpanded`. */
  defaultExpanded?: boolean;
}

/** Render the icon that corresponds to the step's status. */
const StatusIcon: React.FC<{ status: BrowserStep['status'] }> = ({ status }) => {
  switch (status) {
    case 'running':
      return <CircularProgress size={14} aria-label="Running" />;
    case 'succeeded':
      return <CheckCircleOutlineIcon fontSize="small" aria-label="Succeeded" />;
    case 'failed':
      return <ErrorOutlineIcon fontSize="small" aria-label="Failed" />;
    case 'waiting-for-user':
      return <PauseCircleOutlineIcon fontSize="small" aria-label="Waiting for user" />;
    case 'screenshot':
      return <ImageOutlinedIcon fontSize="small" aria-label="Screenshot" />;
    default:
      return null;
  }
};

/** HITL prompt block rendered inside a waiting-for-user step. */
const HitlBlock: React.FC<{ hitl: NonNullable<BrowserStep['hitl']> }> = ({ hitl }) => (
  <div
    className="browser-step-hitl"
    role="region"
    aria-label="Human-in-the-loop prompt"
  >
    <div className="browser-step-hitl-question">{hitl.question}</div>
    {hitl.screenshotBase64 && (
      <img
        src={`data:image/png;base64,${hitl.screenshotBase64}`}
        alt="HITL screenshot context"
        className="browser-step-hitl-screenshot"
      />
    )}
    {hitl.context && <div className="browser-step-hitl-context">{hitl.context}</div>}
    <div className="browser-step-hitl-status" data-status={hitl.status}>
      {hitl.status}
    </div>
  </div>
);

export const StepCard: React.FC<StepCardProps> = ({ step, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded);

  // If the caller's computed default expanded state changes across renders
  // (e.g. a screenshot arrives late for an already-rendered action step),
  // honour the new default — but only for transitions false → true. We
  // never auto-collapse a card the user has opened.
  useEffect(() => {
    if (defaultExpanded) {
      setExpanded(true);
    }
  }, [defaultExpanded]);

  const kindLabel = step.action?.actionType ?? (step.hitl ? 'handoff_to_user' : 'screenshot');
  const hasExpandableBody =
    step.reasoning.length > 0 ||
    step.screenshot !== undefined ||
    step.hitl !== undefined ||
    (step.action?.result !== undefined && step.action.result.length > 0);

  const toggle = () => {
    if (hasExpandableBody) setExpanded((v) => !v);
  };

  return (
    <div
      className={`browser-step browser-step-${step.status}${expanded ? ' browser-step-open' : ''}`}
      data-testid="browser-step-card"
      data-step-number={step.stepNumber}
      data-status={step.status}
    >
      <button
        type="button"
        className="browser-step-head"
        onClick={toggle}
        aria-expanded={expanded}
        aria-controls={`step-body-${step.stepNumber}`}
        data-testid="browser-step-head"
        disabled={!hasExpandableBody}
      >
        <span className="browser-step-num">Step {step.stepNumber}</span>
        <span className="browser-step-title">
          <span className="browser-step-kind">{kindLabel}</span>
          <span className="browser-step-summary">{step.summary}</span>
        </span>
        <span className="browser-step-status" aria-hidden={step.status === 'screenshot'}>
          <StatusIcon status={step.status} />
        </span>
        {hasExpandableBody && (
          <ExpandMoreIcon
            className={`browser-step-caret${expanded ? ' browser-step-caret-open' : ''}`}
            fontSize="small"
            aria-hidden="true"
          />
        )}
      </button>

      {expanded && hasExpandableBody && (
        <div
          className="browser-step-body"
          id={`step-body-${step.stepNumber}`}
          data-testid="browser-step-body"
        >
          {step.reasoning && (
            <div className="browser-step-reasoning" data-testid="browser-step-reasoning">
              {step.reasoning}
            </div>
          )}

          {step.screenshot && (
            <div className="browser-step-screenshot-wrap">
              <Screenshot
                screenshotUrl={step.screenshot.screenshotUrl}
                title={step.screenshot.title}
                stepNumber={step.screenshot.stepNumber}
                timestamp={step.screenshot.timestamp}
              />
            </div>
          )}

          {step.hitl && <HitlBlock hitl={step.hitl} />}

          {step.action?.result && step.action.result.length > 0 && (
            <pre className="browser-step-result" data-testid="browser-step-result">
              {step.action.result}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export default StepCard;
