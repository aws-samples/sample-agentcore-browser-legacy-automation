// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Application Settings Section - Core App Configuration
 */

import React from 'react';
import { Box, TextField, Typography, Grid } from '@mui/material';

interface ApplicationSettings {
  websocketReconnectInterval: number;
  maxReconnectAttempts: number;
}

interface ApplicationSettingsSectionProps {
  settings: ApplicationSettings;
  onChange: (settings: ApplicationSettings) => void;
}

export const ApplicationSettingsSection: React.FC<ApplicationSettingsSectionProps> = ({
  settings,
  onChange,
}) => {
  const handleChange = (field: keyof ApplicationSettings, value: number) => {
    onChange({
      ...settings,
      [field]: value,
    });
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure WebSocket connection behavior.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Typography variant="subtitle2" gutterBottom>
            WebSocket Configuration
          </Typography>
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Reconnect Interval (ms)"
            type="number"
            value={settings.websocketReconnectInterval}
            onChange={(e) =>
              handleChange('websocketReconnectInterval', parseInt(e.target.value, 10) || 3000)
            }
            inputProps={{ min: 1000, max: 30000, step: 1000 }}
            fullWidth
            helperText="Time between reconnection attempts"
          />
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Max Reconnect Attempts"
            type="number"
            value={settings.maxReconnectAttempts}
            onChange={(e) =>
              handleChange('maxReconnectAttempts', parseInt(e.target.value, 10) || 5)
            }
            inputProps={{ min: 1, max: 20 }}
            fullWidth
            helperText="Maximum number of reconnection attempts"
          />
        </Grid>
      </Grid>
    </Box>
  );
};
