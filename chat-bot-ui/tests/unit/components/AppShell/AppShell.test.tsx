// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AppShell smoke test — verifies the shell renders with mocked OIDC auth.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

const mockAuth = {
  isAuthenticated: true,
  isLoading: false,
  user: { access_token: 'test-token', profile: { name: 'Test User' } },
  signinRedirect: jest.fn(),
  signoutRedirect: jest.fn(),
  removeUser: jest.fn(),
  stopSilentRenew: jest.fn(),
  events: { removeUserSignedOut: jest.fn() },
};

jest.mock('react-oidc-context', () => ({
  __esModule: true,
  useAuth: () => mockAuth,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// eslint-disable-next-line import/first
import { NotificationProvider } from '../../../../src/contexts/NotificationContext';
// eslint-disable-next-line import/first
import { AccessibilityProvider } from '../../../../src/contexts/AccessibilityContext';
// eslint-disable-next-line import/first
import { AppShell } from '../../../../src/components/AppShell/AppShell';

describe('AppShell', () => {
  it('renders the sidebar and main landmarks', () => {
    render(
      <NotificationProvider>
        <AccessibilityProvider>
          <BrowserRouter>
            <AppShell />
          </BrowserRouter>
        </AccessibilityProvider>
      </NotificationProvider>,
    );

    expect(screen.getByRole('navigation', { name: /sidebar/i })).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
