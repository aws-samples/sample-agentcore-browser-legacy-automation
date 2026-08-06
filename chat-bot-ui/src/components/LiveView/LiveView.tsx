// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * LiveView — Toggleable right-side panel embedding the Amazon DCV viewer
 * via `<iframe>` for real-time visualization of the browser agent session.
 *
 * Parent (`BrowserProfileContent`) owns the `open` boolean and the current
 * pre-signed `liveViewUrl`. This component:
 *
 *   - Renders `null` when `open === false` (no background work).
 *   - Renders an `<iframe>` when `open` and `liveViewUrl` is non-null.
 *   - Renders a "Waiting for live view URL…" placeholder when `open` but
 *     `liveViewUrl` is null — avoids shipping an `<iframe src="">` to the DOM.
 *   - Fires `onRequestRefresh()` every 270 s while `open` to stay under the
 *     300 s pre-signed URL TTL. The cleanup clears the interval on close,
 *     so no stray `BROWSER_LIVE_VIEW_REQUEST` leaks after the panel closes.
 *
 * @module components/browser/LiveView
 */

import React, { useEffect } from 'react';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloseIcon from '@mui/icons-material/Close';
import './LiveView.css';

/** Pre-signed DCV URLs expire after ~300 s; refresh at 270 s with headroom. */
const REFRESH_INTERVAL_MS = 270_000;

export interface LiveViewProps {
  open: boolean;
  onClose: () => void;
  liveViewUrl: string | null;
  onRequestRefresh: () => void;
}

export const LiveView: React.FC<LiveViewProps> = ({
  open,
  onClose,
  liveViewUrl,
  onRequestRefresh,
}) => {
  // Auto-refresh pre-signed URL every 270 s while open. Declared before any
  // early return so the hook order stays stable across renders.
  useEffect(() => {
    if (!open) return;
    const id = window.setInterval(() => onRequestRefresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [open, onRequestRefresh]);

  if (!open) return null;

  return (
    <aside
      className="browser-live-view"
      role="complementary"
      aria-label="Browser live view"
    >
      <header className="browser-live-view-header">
        <span className="browser-live-view-title">Live view</span>
        <button
          type="button"
          className="browser-live-view-refresh"
          onClick={onRequestRefresh}
          aria-label="Refresh live view URL"
        >
          <RefreshIcon fontSize="small" aria-hidden="true" />
          <span>Refresh</span>
        </button>
        {liveViewUrl && (
          <a
            className="browser-live-view-open"
            href={liveViewUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open live view in new tab"
          >
            Open in new tab
          </a>
        )}
        <button
          type="button"
          className="browser-live-view-close"
          onClick={onClose}
          aria-label="Close live view panel"
        >
          <CloseIcon fontSize="small" aria-hidden="true" />
        </button>
      </header>
      {liveViewUrl ? (
        <iframe
          src={liveViewUrl}
          title="Browser live view"
          className="browser-live-view-iframe"
        />
      ) : (
        <div className="browser-live-view-empty" role="status">
          Waiting for live view URL…
        </div>
      )}
    </aside>
  );
};

export default LiveView;
