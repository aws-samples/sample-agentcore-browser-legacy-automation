// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Notification Settings Section
 *
 * Provides granular control over notification preferences
 */

import React from 'react';
import {
  Box,
  Typography,
  FormGroup,
  FormControlLabel,
  Switch,
  Divider,
  Button,
  Alert,
} from '@mui/material';
import { useNotifications } from '../../../contexts/NotificationContext';

export const NotificationSettingsSection: React.FC = () => {
  const {
    preferences,
    updatePreferences,
    getRegisteredComponents,
    showNotification
  } = useNotifications();

  const registeredComponents = getRegisteredComponents();

  const handleToggle = (componentName: string) => {
    const newPreferences = {
      ...preferences,
      [componentName]: !preferences[componentName as keyof typeof preferences],
    };
    updatePreferences(newPreferences);
  };

  const handleEnableAll = () => {
    const allEnabled = registeredComponents.reduce((acc, component) => {
      acc[component.name as keyof typeof preferences] = true;
      return acc;
    }, {} as any);

    updatePreferences(allEnabled);
    showNotification('All notifications enabled', 'success', 'settingsModal');
  };

  const handleDisableAll = () => {
    const allDisabled = registeredComponents.reduce((acc, component) => {
      acc[component.name as keyof typeof preferences] = false;
      return acc;
    }, {} as any);

    updatePreferences(allDisabled);
    showNotification('All notifications disabled', 'warning', 'settingsModal');
  };

  const handleTestNotification = () => {
    showNotification(
      'This is a test notification to verify the system is working correctly',
      'info',
      'settingsModal',
      6000
    );
  };



  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Notification Preferences
      </Typography>

      <Typography variant="body2" color="text.secondary" paragraph>
        Control which components can send notifications. Disabled components will not show
        notifications, helping you focus on what's important.
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Notifications appear in the top-right corner and automatically dismiss after a few seconds.
        You can also click the X to dismiss them manually.
      </Alert>

      <Box sx={{ mb: 3 }}>
        <Button
          variant="outlined"
          onClick={handleEnableAll}
          sx={{ mr: 1, mb: 1 }}
          size="small"
        >
          Enable All
        </Button>
        <Button
          variant="outlined"
          onClick={handleDisableAll}
          sx={{ mr: 1, mb: 1 }}
          size="small"
        >
          Disable All
        </Button>
        <Button
          variant="outlined"
          onClick={handleTestNotification}
          sx={{ mb: 1 }}
          size="small"
        >
          Test Notification
        </Button>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <FormGroup>
        {registeredComponents.map((component) => (
          <Box key={component.name} sx={{ mb: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={preferences[component.name as keyof typeof preferences] ?? true}
                  onChange={() => handleToggle(component.name)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1" component="div">
                    {component.displayName}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" component="div">
                    {component.description}
                  </Typography>
                </Box>
              }
            />
          </Box>
        ))}
      </FormGroup>
    </Box>
  );
};