// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Centralized Notification Service
 *
 * Provides centralized notification management with granular control settings
 */

import {
  NotificationMessage,
  NotificationPreferences,
  NotificationSeverity,
  NotificationComponent,
  NotificationServiceConfig,
  DEFAULT_NOTIFICATION_PREFERENCES,
  NOTIFICATION_COMPONENTS,
  DEFAULT_NOTIFICATION_CONFIG
} from '../types/notification.types';

class NotificationService {
  private notifications: NotificationMessage[] = [];
  private preferences: NotificationPreferences = { ...DEFAULT_NOTIFICATION_PREFERENCES };
  private config: NotificationServiceConfig = { ...DEFAULT_NOTIFICATION_CONFIG };
  private listeners: Set<() => void> = new Set();
  private nextId = 1;

  constructor() {
    this.loadPreferences();
  }

  /**
   * Load notification preferences from localStorage
   */
  private loadPreferences(): void {
    try {
      const stored = localStorage.getItem('notification-preferences');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.preferences = { ...DEFAULT_NOTIFICATION_PREFERENCES, ...parsed };
      }
    } catch (error) {
      console.warn('Failed to load notification preferences:', error);
      this.preferences = { ...DEFAULT_NOTIFICATION_PREFERENCES };
    }
  }

  /**
   * Save notification preferences to localStorage
   */
  private savePreferences(): void {
    try {
      localStorage.setItem('notification-preferences', JSON.stringify(this.preferences));
    } catch (error) {
      console.warn('Failed to save notification preferences:', error);
    }
  }

  /**
   * Subscribe to notification changes
   */
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify all listeners of changes
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener());
  }

  /**
   * Check if a component is enabled for notifications
   */
  isComponentEnabled(componentSource: string): boolean {
    const key = componentSource as keyof NotificationPreferences;
    return this.preferences[key] ?? true;
  }

  /**
   * Show a notification if the component is enabled
   */
  showNotification(
    message: string,
    severity: NotificationSeverity = 'success',
    componentSource: string,
    autoHideDuration?: number
  ): string | null {
    // Check if notifications are enabled for this component
    if (!this.isComponentEnabled(componentSource)) {
      return null;
    }

    const notification: NotificationMessage = {
      id: `notification-${this.nextId++}`,
      message,
      severity,
      componentSource,
      timestamp: Date.now(),
      autoHideDuration: autoHideDuration ?? this.config.defaultAutoHideDuration,
    };

    // Add to notifications array (newest first)
    this.notifications.unshift(notification);

    // Limit the number of notifications
    if (this.notifications.length > this.config.maxNotifications) {
      this.notifications = this.notifications.slice(0, this.config.maxNotifications);
    }

    this.notifyListeners();
    return notification.id;
  }

  /**
   * Dismiss a specific notification
   */
  dismissNotification(id: string): void {
    const index = this.notifications.findIndex(n => n.id === id);
    if (index >= 0) {
      this.notifications.splice(index, 1);
      this.notifyListeners();
    }
  }

  /**
   * Clear all notifications
   */
  clearAllNotifications(): void {
    this.notifications = [];
    this.notifyListeners();
  }

  /**
   * Update notification preferences
   */
  updatePreferences(newPreferences: Partial<NotificationPreferences>): void {
    this.preferences = { ...this.preferences, ...newPreferences };
    this.savePreferences();
    this.notifyListeners();
  }

  /**
   * Get current notification preferences
   */
  getPreferences(): NotificationPreferences {
    return { ...this.preferences };
  }

  /**
   * Get all notifications
   */
  getNotifications(): NotificationMessage[] {
    return [...this.notifications];
  }

  /**
   * Get registered notification components
   */
  getRegisteredComponents(): NotificationComponent[] {
    return [...NOTIFICATION_COMPONENTS];
  }

  /**
   * Reset preferences to defaults
   */
  resetPreferences(): void {
    this.preferences = { ...DEFAULT_NOTIFICATION_PREFERENCES };
    this.savePreferences();
    this.notifyListeners();
  }

  /**
   * Convenience methods for different severity levels
   */
  success(message: string, componentSource: string, autoHideDuration?: number): string | null {
    return this.showNotification(message, 'success', componentSource, autoHideDuration);
  }

  info(message: string, componentSource: string, autoHideDuration?: number): string | null {
    return this.showNotification(message, 'info', componentSource, autoHideDuration);
  }

  warning(message: string, componentSource: string, autoHideDuration?: number): string | null {
    return this.showNotification(message, 'warning', componentSource, autoHideDuration);
  }

  error(message: string, componentSource: string, autoHideDuration?: number): string | null {
    return this.showNotification(message, 'error', componentSource, autoHideDuration);
  }
}

// Export singleton instance
export const notificationService = new NotificationService();