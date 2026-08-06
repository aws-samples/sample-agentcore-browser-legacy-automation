// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Screenshot — Renders a single browser-agent screenshot from a pre-signed S3 URL.
 *
 * Pure presentational component. Displays the step number label, the image itself,
 * and a caption. Clicking the thumbnail opens a lightbox overlay that shows the
 * screenshot at its natural size, capped to 90vw × 90vh, with a title line that
 * reads `Step {N} · {title} · {formatted timestamp}`. The lightbox is dismissed
 * by clicking the backdrop, pressing Escape, or clicking the Close button — all
 * handled by MUI's Dialog which already provides focus trapping, aria-modal
 * semantics, and portal rendering.
 *
 * If the pre-signed URL has expired (or the image fails to load for any other
 * reason), the `<img>` is swapped for a graceful fallback placeholder — no
 * re-sign attempt is made because the backend does not expose a refresh
 * endpoint. The fallback placeholder is not clickable.
 *
 * Click propagation is stopped on the thumbnail so that a future parent click
 * handler (e.g. a step card collapse toggle) never fires when the user is
 * trying to zoom the screenshot.
 *
 * @module components/browser/Screenshot
 */

import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import './Screenshot.css';

export interface ScreenshotProps {
  screenshotUrl: string;
  title: string;
  stepNumber: number;
  timestamp?: number;
}

/**
 * Format a Unix timestamp (in seconds) into a human-readable `YYYY-MM-DD HH:mm:ss`
 * string for the lightbox title. Returns an empty string when the timestamp is
 * missing or not a finite number.
 */
function formatTimestamp(timestamp?: number): string {
  if (timestamp === undefined || !Number.isFinite(timestamp)) {
    return '';
  }
  // Pre-signed URLs carry Unix seconds; multiply into millis for Date.
  const date = new Date(timestamp * 1000);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const mi = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}:${ss}`;
}

export const Screenshot: React.FC<ScreenshotProps> = ({
  screenshotUrl,
  title,
  stepNumber,
  timestamp,
}) => {
  const [loadError, setLoadError] = useState<boolean>(false);
  const [lightboxOpen, setLightboxOpen] = useState<boolean>(false);

  // Requirement 18.5: always provide a non-empty alt / aria-label even when
  // `title` is missing or an empty string.
  const accessibleLabel = title && title.trim().length > 0
    ? title
    : `Browser step ${stepNumber}`;

  // Render the caption with the same fallback so screen readers and sighted
  // users see a meaningful label.
  const captionText = title && title.trim().length > 0 ? title : 'Screenshot';

  // Compose the lightbox title line. Mirrors the mock:
  //   "Step 4 · after-click-agree · 2026-04-29 21:37:14"
  const formattedTimestamp = formatTimestamp(timestamp);
  const lightboxTitle = [
    `Step ${stepNumber}`,
    captionText,
    formattedTimestamp,
  ].filter((segment) => segment.length > 0).join(' · ');

  const handleOpenLightbox = (event: React.MouseEvent<HTMLButtonElement>): void => {
    // Prevent the click from bubbling to any parent (e.g. a StepCard header
    // button or a future collapse toggle) — the screenshot zoom is the
    // intended action here.
    event.stopPropagation();
    setLightboxOpen(true);
  };

  const handleCloseLightbox = (): void => {
    setLightboxOpen(false);
  };

  return (
    <>
      <figure className="browser-screenshot">
        <div className="browser-screenshot-step">Step {stepNumber}</div>
        {loadError ? (
          <div
            className="browser-screenshot-fallback"
            role="img"
            aria-label={accessibleLabel}
          >
            <span>Screenshot no longer available</span>
          </div>
        ) : (
          <button
            type="button"
            className="browser-screenshot-trigger"
            onClick={handleOpenLightbox}
            aria-label={`Open ${accessibleLabel} at full size`}
          >
            <img
              src={screenshotUrl}
              alt={accessibleLabel}
              onError={() => setLoadError(true)}
              loading="lazy"
            />
          </button>
        )}
        <figcaption>{captionText}</figcaption>
      </figure>

      <Dialog
        open={lightboxOpen}
        onClose={handleCloseLightbox}
        maxWidth={false}
        aria-label={`${accessibleLabel} — full size`}
        PaperProps={{ className: 'browser-screenshot-lightbox-paper' }}
        data-testid="browser-screenshot-lightbox"
      >
        <div className="browser-screenshot-lightbox-header">
          <span
            className="browser-screenshot-lightbox-title"
            data-testid="browser-screenshot-lightbox-title"
          >
            {lightboxTitle}
          </span>
          <IconButton
            onClick={handleCloseLightbox}
            aria-label="Close screenshot"
            size="small"
            className="browser-screenshot-lightbox-close"
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>
        <div className="browser-screenshot-lightbox-body">
          <img
            src={screenshotUrl}
            alt={accessibleLabel}
            className="browser-screenshot-lightbox-image"
          />
        </div>
      </Dialog>
    </>
  );
};

export default Screenshot;
