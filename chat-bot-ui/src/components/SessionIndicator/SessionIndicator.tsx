// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SessionIndicator — Top-of-chat status bar shown while a browser agent
 * session is active.
 *
 * Pure presentational component: parent (`ChatView`) controls visibility by
 * rendering this only when `browserSession.isActive === true`. On mount the
 * component announces "Browser session active" to screen readers via the
 * shared `AccessibilityContext` live region; on unmount it announces
 * "Browser session ended", covering the session start/stop transitions.
 *
 * The "Stop" button intentionally has no confirmation dialog — a deliberate
 * low-friction choice for the power-user audience (Req 10.4).
 *
 * @module components/browser/SessionIndicator
 */

import React, { useEffect } from 'react';
import StopIcon from '@mui/icons-material/Stop';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import './SessionIndicator.css';

export interface SessionIndicatorProps {
  stepCounter: number;
  onStop: () => void;
  onToggleLiveView: () => void;
}

export const SessionIndicator: React.FC<SessionIndicatorProps> = ({
  stepCounter,
  onStop,
  onToggleLiveView,
}) => {
  const { announceToScreenReader } = useAccessibility();

  // Announce session start on mount / session end on unmount. Parent controls
  // visibility so mount/unmount map directly onto session lifecycle events.
  useEffect(() => {
    announceToScreenReader('Browser session active', 'polite');
    return () => {
      announceToScreenReader('Browser session ended', 'polite');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="browser-session-indicator"
      role="region"
      aria-label="Browser session status"
    >
      <span className="browser-session-label">Browser session active</span>
      <span className="browser-session-step">Step {stepCounter}</span>
      <button
        type="button"
        className="browser-session-stop"
        onClick={onStop}
        aria-label="Stop browser session"
      >
        <StopIcon fontSize="small" aria-hidden="true" />
        <span>Stop</span>
      </button>
      <button
        type="button"
        className="browser-session-live-view"
        onClick={onToggleLiveView}
        aria-label="Toggle live view"
      >
        <VisibilityIcon fontSize="small" aria-hidden="true" />
        <span>Live view</span>
      </button>
    </div>
  );
};

export default SessionIndicator;
