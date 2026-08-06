// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Theme Settings Section - UI Theme Configuration
 */

import React from 'react';
import {
  Box,
  TextField,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  Card,
  CardContent
} from '@mui/material';
import { THEME_CONFIGS } from '../../../theme/themeConfig';
import type { ThemeOption } from '../../../types/ui.types';

interface ThemeSettings {
  selectedTheme: ThemeOption;
  fontFamily: string;
  borderRadius: number;
  spacing: number;
  scrollbarWidth: string;
  scrollbarBorderRadius: string;
}

interface ThemeSettingsSectionProps {
  settings: ThemeSettings;
  onChange: (settings: ThemeSettings) => void;
}

export const ThemeSettingsSection: React.FC<ThemeSettingsSectionProps> = ({
  settings,
  onChange
}) => {
  const handleChange = (field: keyof ThemeSettings, value: string | number) => {
    onChange({
      ...settings,
      [field]: value
    });
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure UI theme and visual appearance settings.
      </Typography>

      <Grid container spacing={3}>
        {/* Theme Selection */}
        <Grid item xs={12}>
          <FormControl fullWidth>
            <InputLabel>Theme</InputLabel>
            <Select
              value={settings.selectedTheme}
              onChange={(e) => handleChange('selectedTheme', e.target.value)}
              label="Theme"
            >
              {THEME_CONFIGS.map((theme) => (
                <MenuItem key={theme.name} value={theme.name}>
                  {theme.displayName}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              {THEME_CONFIGS.find(t => t.name === settings.selectedTheme)?.description}
            </FormHelperText>
          </FormControl>
        </Grid>

        {/* Typography Settings */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            Typography
          </Typography>
        </Grid>

        <Grid item xs={12}>
          <TextField
            label="Font Family"
            value={settings.fontFamily}
            onChange={(e) => handleChange('fontFamily', e.target.value)}
            fullWidth
            helperText="CSS font family stack for the application"
          />
        </Grid>

        {/* Layout Settings */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            Layout
          </Typography>
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Border Radius (px)"
            type="number"
            value={settings.borderRadius}
            onChange={(e) => handleChange('borderRadius', parseInt(e.target.value) || 8)}
            inputProps={{ min: 0, max: 20 }}
            fullWidth
            helperText="Default border radius for UI elements"
          />
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Spacing (px)"
            type="number"
            value={settings.spacing}
            onChange={(e) => handleChange('spacing', parseInt(e.target.value) || 8)}
            inputProps={{ min: 4, max: 16 }}
            fullWidth
            helperText="Base spacing unit for layout"
          />
        </Grid>

        {/* Scrollbar Settings */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            Scrollbar Appearance
          </Typography>
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Scrollbar Width"
            value={settings.scrollbarWidth}
            onChange={(e) => handleChange('scrollbarWidth', e.target.value)}
            fullWidth
            helperText="Width of custom scrollbars (e.g., '8px')"
          />
        </Grid>

        <Grid item xs={6}>
          <TextField
            label="Scrollbar Border Radius"
            value={settings.scrollbarBorderRadius}
            onChange={(e) => handleChange('scrollbarBorderRadius', e.target.value)}
            fullWidth
            helperText="Border radius for scrollbar thumb (e.g., '4px')"
          />
        </Grid>

        {/* Theme Preview */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            Theme Preview
          </Typography>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sample Content
              </Typography>
              <Typography variant="body1" paragraph>
                This is how text will appear with the current theme settings.
                The selected theme affects colors, typography, and overall appearance.
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: 'primary.main',
                    borderRadius: `${settings.borderRadius}px`
                  }}
                />
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: 'secondary.main',
                    borderRadius: `${settings.borderRadius}px`
                  }}
                />
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: 'success.main',
                    borderRadius: `${settings.borderRadius}px`
                  }}
                />
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: 'warning.main',
                    borderRadius: `${settings.borderRadius}px`
                  }}
                />
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: 'error.main',
                    borderRadius: `${settings.borderRadius}px`
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};