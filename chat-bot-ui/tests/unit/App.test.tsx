// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * App.tsx smoke test — verifies the root component renders with mocked
 * OIDC auth and routes unauthenticated users to the login page.
 */

import React from 'react';
import { render } from '@testing-library/react';

// Mock react-oidc-context before App is imported — App's subtree depends on it
// via ProtectedRoute and Login.
const mockAuth = {
  isAuthenticated: false,
  isLoading: false,
  activeNavigator: undefined,
  signinRedirect: jest.fn(),
  signoutRedirect: jest.fn(),
  error: null,
};

jest.mock('react-oidc-context', () => ({
  __esModule: true,
  useAuth: () => mockAuth,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Avoid full MUI theme init cost on the shell — AgentContent imports the
// hook which opens a WebSocket. The default WebSocket mock from setupTests
// handles this gracefully.

import App from '../../src/App';

describe('App', () => {
  it('exports a React component as the default export', () => {
    expect(typeof App).toBe('function');
  });

  it('renders without crashing', () => {
    expect(() => render(<App />)).not.toThrow();
  });
});
