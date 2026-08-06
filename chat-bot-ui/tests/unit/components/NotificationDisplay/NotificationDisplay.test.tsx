// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * NotificationDisplay smoke test — renders inside NotificationProvider
 * and surfaces triggered notifications.
 *
 * Regression guard for the NotificationProvider memoization fix: before
 * `showNotification` was wrapped in useCallback, a `useEffect([showNotification])`
 * consumer like the `Fire` helper below would create an infinite render loop
 * because each service-triggered re-render produced a new `showNotification`
 * reference. The hang this test used to exhibit was that loop, not the
 * Snackbar auto-hide timer.
 */

import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { NotificationProvider, useNotifications } from '../../../../src/contexts/NotificationContext';
import { NotificationDisplay } from '../../../../src/components/NotificationDisplay/NotificationDisplay';
import { notificationService } from '../../../../src/services/NotificationService';

const Fire: React.FC = () => {
  const { showNotification } = useNotifications();
  React.useEffect(() => {
    showNotification('hello from test', 'info', 'textChat');
  }, [showNotification]);
  return null;
};

describe('NotificationDisplay', () => {
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

  it('renders a notification surfaced via showNotification', async () => {
    render(
      <NotificationProvider>
        <NotificationDisplay />
        <Fire />
      </NotificationProvider>,
    );

    await waitFor(() => expect(screen.getByText(/hello from test/i)).toBeInTheDocument(), {
      timeout: 1500,
    });
  }, 3000);
});
