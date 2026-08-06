// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Notification Display Component
 *
 * Displays notifications using MUI Snackbar positioned at top-right
 */

import React, { useEffect, useState } from 'react';
import { Snackbar, Alert, Stack } from '@mui/material';
import { useNotifications } from '../../contexts/NotificationContext';
import { NotificationMessage } from '../../types/notification.types';

export const NotificationDisplay: React.FC = () => {
  const { notifications, dismissNotification } = useNotifications();
  const [currentNotification, setCurrentNotification] = useState<NotificationMessage | null>(null);

  // Show the most recent notification
  useEffect(() => {
    if (notifications.length > 0 && !currentNotification) {
      setCurrentNotification(notifications[0]);
    }
  }, [notifications, currentNotification]);

  // Auto-dismiss notification after timeout
  useEffect(() => {
    if (currentNotification && currentNotification.autoHideDuration) {
      const timer = setTimeout(() => {
        handleClose();
      }, currentNotification.autoHideDuration);

      return () => clearTimeout(timer);
    }
  }, [currentNotification]);

  const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }

    if (currentNotification) {
      dismissNotification(currentNotification.id);
      setCurrentNotification(null);
    }
  };

  // Show next notification when current one is dismissed
  useEffect(() => {
    if (!currentNotification && notifications.length > 0) {
      const timer = setTimeout(() => {
        setCurrentNotification(notifications[0]);
      }, 100); // Small delay for smooth transition

      return () => clearTimeout(timer);
    }
  }, [currentNotification, notifications]);

  return (
    <>
      <Snackbar
        open={!!currentNotification}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        sx={{
          mt: 1,
          mr: 1,
          zIndex: 9999, // Ensure it's above all other components
          position: 'fixed', // Ensure it's positioned correctly
        }}
      >
        {currentNotification ? (
          <Alert
            onClose={handleClose}
            severity={currentNotification.severity}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {currentNotification.message}
          </Alert>
        ) : (
          <div style={{ display: 'none' }} />
        )}
      </Snackbar>
    </>
  );
};