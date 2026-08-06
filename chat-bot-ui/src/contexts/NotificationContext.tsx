// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Notification Context
 *
 * React context for accessing the notification service throughout the app.
 *
 * All callbacks and the context value are memoized so consumers that depend
 * on them (e.g. `useEffect([showNotification])`) don't re-fire every render.
 * Without memoization, a consumer that calls `showNotification` inside an
 * effect triggers an infinite render loop because the service subscription
 * updates provider state on every notification.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from 'react';
import {
  NotificationContextValue,
  NotificationMessage,
  NotificationPreferences,
  NotificationSeverity,
  NotificationComponent,
} from '../types/notification.types';
import { notificationService } from '../services/NotificationService';

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationMessage[]>(() =>
    notificationService.getNotifications(),
  );
  const [preferences, setPreferences] = useState<NotificationPreferences>(() =>
    notificationService.getPreferences(),
  );

  // Subscribe to notification service changes
  useEffect(() => {
    const updateState = () => {
      setNotifications(notificationService.getNotifications());
      setPreferences(notificationService.getPreferences());
    };

    // Initial state
    updateState();

    // Subscribe to changes
    const unsubscribe = notificationService.subscribe(updateState);

    return unsubscribe;
  }, []);

  const showNotification = useCallback(
    (
      message: string,
      severity: NotificationSeverity,
      componentSource: string,
      autoHideDuration?: number,
    ): void => {
      notificationService.showNotification(message, severity, componentSource, autoHideDuration);
    },
    [],
  );

  const dismissNotification = useCallback((id: string): void => {
    notificationService.dismissNotification(id);
  }, []);

  const clearAllNotifications = useCallback((): void => {
    notificationService.clearAllNotifications();
  }, []);

  const updatePreferences = useCallback(
    (newPreferences: Partial<NotificationPreferences>): void => {
      notificationService.updatePreferences(newPreferences);
    },
    [],
  );

  const isComponentEnabled = useCallback((componentSource: string): boolean => {
    return notificationService.isComponentEnabled(componentSource);
  }, []);

  const getRegisteredComponents = useCallback((): NotificationComponent[] => {
    return notificationService.getRegisteredComponents();
  }, []);

  const contextValue = useMemo<NotificationContextValue>(
    () => ({
      notifications,
      preferences,
      showNotification,
      dismissNotification,
      clearAllNotifications,
      updatePreferences,
      isComponentEnabled,
      getRegisteredComponents,
    }),
    [
      notifications,
      preferences,
      showNotification,
      dismissNotification,
      clearAllNotifications,
      updatePreferences,
      isComponentEnabled,
      getRegisteredComponents,
    ],
  );

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
    </NotificationContext.Provider>
  );
};

/**
 * Hook to use the notification context
 */
export const useNotifications = (): NotificationContextValue => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
