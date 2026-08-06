// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AgentContent smoke test — renders inside mocked auth + notification
 * providers and verifies the chat view is mounted.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';

const mockAuth = {
  isAuthenticated: true,
  isLoading: false,
  user: { access_token: 'test-token' },
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
import { AgentContent } from '../../../../src/components/AgentContent/AgentContent';

describe('AgentContent', () => {
  it('renders the chat view inside the providers', () => {
    render(
      <NotificationProvider>
        <AccessibilityProvider>
          <AgentContent onSessionsChange={jest.fn()} />
        </AccessibilityProvider>
      </NotificationProvider>,
    );

    expect(screen.getByTestId('browser-chat-view')).toBeInTheDocument();
  });
});
