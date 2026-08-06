// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Login smoke test — verifies the login card renders and the sign-in
 * button calls auth.signinRedirect.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

const signinRedirect = jest.fn();
let mockAuth: {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: { message: string } | null;
  signinRedirect: jest.Mock;
} = {
  isAuthenticated: false,
  isLoading: false,
  error: null,
  signinRedirect,
};

jest.mock('react-oidc-context', () => ({
  __esModule: true,
  useAuth: () => mockAuth,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// eslint-disable-next-line import/first
import { Login } from '../../../../src/components/Login/Login';

describe('Login', () => {
  beforeEach(() => {
    signinRedirect.mockReset();
    mockAuth = { isAuthenticated: false, isLoading: false, error: null, signinRedirect };
  });

  it('renders the Sign In button when not authenticated', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>,
    );
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls auth.signinRedirect when Sign In is clicked', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(signinRedirect).toHaveBeenCalledTimes(1);
  });

  it('shows a loading indicator while auth.isLoading is true', () => {
    mockAuth = { isAuthenticated: false, isLoading: true, error: null, signinRedirect };
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>,
    );
    expect(screen.getByLabelText(/checking authentication status/i)).toBeInTheDocument();
  });
});
