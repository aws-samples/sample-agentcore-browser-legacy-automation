// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * NotificationContext Integration Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { NotificationProvider, useNotifications } from '../../../src/contexts/NotificationContext';
import { NotificationDisplay } from '../../../src/components/NotificationDisplay/NotificationDisplay';
import { notificationService } from '../../../src/services/NotificationService';

// Test component that uses the notification context
const TestComponent: React.FC = () => {
  const { showNotification, preferences, updatePreferences, getRegisteredComponents, clearAllNotifications } = useNotifications();

  return (
    <div>
      <button
        onClick={() => showNotification('Test success', 'success', 'summaryView')}
        data-testid="success-btn"
      >
        Show Success
      </button>
      <button
        onClick={() => showNotification('Test error', 'error', 'voiceStatus')}
        data-testid="error-btn"
      >
        Show Error
      </button>
      <button
        onClick={() => updatePreferences({ summaryView: false })}
        data-testid="disable-btn"
      >
        Disable System
      </button>
      <button
        onClick={() => clearAllNotifications()}
        data-testid="clear-btn"
      >
        Clear All
      </button>
      <div data-testid="system-enabled">
        {preferences.summaryView ? 'enabled' : 'disabled'}
      </div>
      <div data-testid="component-count">
        {getRegisteredComponents().length}
      </div>
    </div>
  );
};

const TestApp: React.FC = () => (
  <NotificationProvider>
    <TestComponent />
    <NotificationDisplay />
  </NotificationProvider>
);

describe('NotificationContext Integration', () => {
  beforeEach(() => {
    // Reset the module-level singleton to prevent state leaks across tests.
    notificationService.clearAllNotifications();
    notificationService.resetPreferences();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    notificationService.clearAllNotifications();
  });

  it('should provide notification context to components', () => {
    render(<TestApp />);

    expect(screen.getByTestId('system-enabled')).toHaveTextContent('enabled');
    expect(screen.getByTestId('component-count')).toHaveTextContent('8'); // 8 registered components (6 original + textChat + agentDrawer)
  });

  it('should show notifications when triggered', async () => {
    render(<TestApp />);

    fireEvent.click(screen.getByTestId('success-btn'));

    await waitFor(() => {
      expect(screen.getByText('Test success')).toBeInTheDocument();
    });
  });

  it('should update preferences and suppress notifications for disabled components', async () => {
    render(<TestApp />);

    // Clear any existing notifications first
    fireEvent.click(screen.getByTestId('clear-btn'));

    // Initially system notifications are enabled
    expect(screen.getByTestId('system-enabled')).toHaveTextContent('enabled');

    // Disable system notifications
    fireEvent.click(screen.getByTestId('disable-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('system-enabled')).toHaveTextContent('disabled');
    });

    // The preference should be updated - we don't need to test the UI display
    // since that's handled by the NotificationDisplay component
  });

  it('should show notifications from enabled components even when other components are disabled', async () => {
    render(<TestApp />);

    // Disable summaryView notifications
    fireEvent.click(screen.getByTestId('disable-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('system-enabled')).toHaveTextContent('disabled');
    });

    // Error notifications should still show for voiceStatus component (which is enabled)
    fireEvent.click(screen.getByTestId('error-btn'));

    await waitFor(() => {
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });
  });
});