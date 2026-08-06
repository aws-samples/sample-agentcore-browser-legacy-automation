// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ActionProgress — Renders a single browser-agent action as a one-line status chip.
 *
 * Pure presentational component. Shows the step number, a status icon
 * (spinner / check / error), the action type, and a truncated details string.
 * When `result` is present, an info button expands a scrollable `<pre>` with the
 * full result text; when `result` is empty/undefined, the affordance is hidden.
 *
 * @module components/browser/ActionProgress
 */

import React, { useState } from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import './ActionProgress.css';

export interface ActionProgressProps {
  stepNumber: number;
  actionType: string;
  details: string;
  status: 'running' | 'succeeded' | 'failed';
  result?: string;
}

/** Clip a string to `max` characters, appending an ellipsis when truncated. */
const truncate = (s: string, max: number): string =>
  s.length > max ? `${s.slice(0, max)}…` : s;

export const ActionProgress: React.FC<ActionProgressProps> = ({
  stepNumber,
  actionType,
  details,
  status,
  result,
}) => {
  const [expanded, setExpanded] = useState<boolean>(false);

  // Requirement 7.5: hide the expand affordance when `result` is empty or missing.
  const hasResult = typeof result === 'string' && result.length > 0;

  return (
    <div
      className={`browser-action-progress browser-action-${status}`}
      role="status"
    >
      <span className="browser-action-step">#{stepNumber}</span>
      <span className="browser-action-icon" aria-hidden="true">
        {status === 'running' && <CircularProgress size={16} />}
        {status === 'succeeded' && <CheckCircleOutlineIcon fontSize="small" />}
        {status === 'failed' && <ErrorOutlineIcon fontSize="small" />}
      </span>
      <span className="browser-action-type">{actionType}</span>
      <span className="browser-action-details">{truncate(details, 80)}</span>
      {hasResult && (
        <button
          type="button"
          className="browser-action-expand"
          aria-label={expanded ? 'Hide full result' : 'Show full result'}
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          ⓘ
        </button>
      )}
      {hasResult && expanded && (
        <pre className="browser-action-result">{result}</pre>
      )}
    </div>
  );
};

export default ActionProgress;
