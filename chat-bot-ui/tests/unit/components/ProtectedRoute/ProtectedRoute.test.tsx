// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ProtectedRoute smoke test — renders children when authenticated and
 * renders a loading indicator while auth is loading.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

let mockAuth = {
  isAuthenticated: true,
  isLoading: false,
  activeNavigator: undefined as string | undefined,
  error: null,
  signinRedirect: jest.fn(),
};

jest.mock('react-oidc-context', () => ({
  __esModule: true,
  useAuth: () => mockAuth,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// eslint-disable-next-line import/first
import { ProtectedRoute, setLoggingOut, isLoggingOut } from '../../../../src/components/ProtectedRoute/ProtectedRoute';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    setLoggingOut(false);
  });

  it('renders children when authenticated', () => {
    mockAuth = { ...mockAuth, isAuthenticated: true, isLoading: false };
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div data-testid="protected-content">ok</div>
        </ProtectedRoute>
      </BrowserRouter>,
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders a loading indicator while auth is loading', () => {
    mockAuth = { ...mockAuth, isAuthenticated: false, isLoading: true };
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>hidden</div>
        </ProtectedRoute>
      </BrowserRouter>,
    );
    expect(screen.getByLabelText(/loading authentication/i)).toBeInTheDocument();
  });

  it('exposes setLoggingOut + isLoggingOut as public helpers', () => {
    setLoggingOut(true);
    expect(isLoggingOut).toBe(true);
    setLoggingOut(false);
    expect(isLoggingOut).toBe(false);
  });
});
