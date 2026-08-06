// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * NotificationService Unit Tests
 */

import { notificationService } from '../../../src/services/NotificationService';
import { DEFAULT_NOTIFICATION_PREFERENCES } from '../../../src/types/notification.types';

describe('NotificationService', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Reset preferences to defaults
    notificationService.resetPreferences();
  });

  afterEach(() => {
    // Clear all notifications after each test
    notificationService.clearAllNotifications();
  });

  describe('showNotification', () => {
    it('should show notification when component is enabled', () => {
      const id = notificationService.showNotification(
        'Test message',
        'success',
        'summaryView'
      );

      expect(id).toBeTruthy();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toBe('Test message');
      expect(notifications[0].severity).toBe('success');
      expect(notifications[0].componentSource).toBe('summaryView');
    });

    it('should not show notification when component is disabled', () => {
      // Disable summaryView notifications
      notificationService.updatePreferences({ summaryView: false });

      const id = notificationService.showNotification(
        'Test message',
        'success',
        'summaryView'
      );

      expect(id).toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(0);
    });

    it('should limit notifications to maxNotifications', () => {
      // Show 6 notifications (more than the default limit of 5)
      for (let i = 0; i < 6; i++) {
        notificationService.showNotification(
          `Message ${i}`,
          'info',
          'summaryView'
        );
      }

      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(5); // Should be limited to 5
      expect(notifications[0].message).toBe('Message 5'); // Newest first
    });
  });

  describe('preferences', () => {
    it('should load default preferences', () => {
      const preferences = notificationService.getPreferences();
      expect(preferences).toEqual(DEFAULT_NOTIFICATION_PREFERENCES);
    });

    it('should update and persist preferences', () => {
      const newPreferences = { summaryView: false, voiceStatus: false };
      notificationService.updatePreferences(newPreferences);

      const preferences = notificationService.getPreferences();
      expect(preferences.summaryView).toBe(false);
      expect(preferences.voiceStatus).toBe(false);
      expect(preferences.liveConversation).toBe(true); // Should remain unchanged
    });

    it('should persist preferences to localStorage', () => {
      const newPreferences = { voiceStatus: false };
      notificationService.updatePreferences(newPreferences);

      // Create a new service instance to test persistence
      const stored = localStorage.getItem('notification-preferences');
      expect(stored).toBeTruthy();

      const parsed = JSON.parse(stored!);
      expect(parsed.voiceStatus).toBe(false);
    });
  });

  describe('convenience methods', () => {
    it('should show success notification', () => {
      const id = notificationService.success('Success message', 'summaryView');

      expect(id).toBeTruthy();
      const notifications = notificationService.getNotifications();
      expect(notifications[0].severity).toBe('success');
    });

    it('should show error notification', () => {
      const id = notificationService.error('Error message', 'voiceStatus');

      expect(id).toBeTruthy();
      const notifications = notificationService.getNotifications();
      expect(notifications[0].severity).toBe('error');
    });

    it('should show warning notification', () => {
      const id = notificationService.warning('Warning message', 'liveConversation');

      expect(id).toBeTruthy();
      const notifications = notificationService.getNotifications();
      expect(notifications[0].severity).toBe('warning');
    });

    it('should show info notification', () => {
      const id = notificationService.info('Info message', 'summaryView');

      expect(id).toBeTruthy();
      const notifications = notificationService.getNotifications();
      expect(notifications[0].severity).toBe('info');
    });
  });

  describe('dismissNotification', () => {
    it('should dismiss specific notification', () => {
      const id1 = notificationService.success('Message 1', 'summaryView');
      const id2 = notificationService.success('Message 2', 'summaryView');

      expect(notificationService.getNotifications()).toHaveLength(2);

      notificationService.dismissNotification(id1!);
      const notifications = notificationService.getNotifications();

      expect(notifications).toHaveLength(1);
      expect(notifications[0].id).toBe(id2);
    });
  });

  describe('clearAllNotifications', () => {
    it('should clear all notifications', () => {
      notificationService.success('Message 1', 'summaryView');
      notificationService.success('Message 2', 'summaryView');

      expect(notificationService.getNotifications()).toHaveLength(2);

      notificationService.clearAllNotifications();
      expect(notificationService.getNotifications()).toHaveLength(0);
    });
  });

  describe('isComponentEnabled', () => {
    it('should return true for enabled components', () => {
      expect(notificationService.isComponentEnabled('summaryView')).toBe(true);
    });

    it('should return false for disabled components', () => {
      notificationService.updatePreferences({ summaryView: false });
      expect(notificationService.isComponentEnabled('summaryView')).toBe(false);
    });

    it('should return true for unknown components (default)', () => {
      expect(notificationService.isComponentEnabled('unknownComponent')).toBe(true);
    });
  });
});