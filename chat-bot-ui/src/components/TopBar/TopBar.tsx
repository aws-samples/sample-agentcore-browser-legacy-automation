// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * TopBar — Application top bar.
 *
 * Minimal top bar for the single-profile blog reference implementation. The
 * profile selector, agent badge, and theme selector have been removed; the
 * bar is reserved for future affordances.
 *
 * @module components/TopBar
 */

import React from 'react';
import { Box } from '@mui/material';

export const TopBar: React.FC = () => {
  return (
    <Box
      data-testid="top-bar"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 2,
        py: 0.75,
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        minHeight: 48,
      }}
    />
  );
};
