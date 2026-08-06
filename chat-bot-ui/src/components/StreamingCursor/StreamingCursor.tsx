// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * StreamingCursor — Blinking cursor appended to streaming assistant content.
 *
 * Renders a blinking pipe character (`|`) during active streaming.
 * Removed from the DOM when streaming completes (SYNTHESIS_END).
 *
 * @module components/StreamingCursor
 */

import React from 'react';
import { Box } from '@mui/material';
import { keyframes } from '@mui/system';

const blink = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`;

export const StreamingCursor: React.FC = () => (
  <Box
    component="span"
    data-testid="streaming-cursor"
    aria-hidden="true"
    sx={{
      display: 'inline-block',
      width: 2,
      height: '1em',
      bgcolor: 'primary.main',
      ml: 0.25,
      verticalAlign: 'text-bottom',
      animation: `${blink} 0.8s step-end infinite`,
    }}
  />
);
