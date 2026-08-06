// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SidebarFooter smoke test — renders the avatar button and forwards clicks.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

const mockAuth = {
  isAuthenticated: true,
  user: { profile: { name: 'Alice', email: 'alice@example.com' } },
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
import { AccessibilityProvider } from '../../../../src/contexts/AccessibilityContext';
// eslint-disable-next-line import/first
import { SidebarFooter } from '../../../../src/components/SidebarFooter/SidebarFooter';

describe('SidebarFooter', () => {
  it('opens the menu on avatar click', () => {
    render(
      <AccessibilityProvider>
        <SidebarFooter
          isCollapsed={false}
          onOpenSettings={jest.fn()}
          onOpenHelp={jest.fn()}
        />
      </AccessibilityProvider>,
    );
    // Click the avatar button — the menu (portal) should open with menu items.
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]);
    expect(screen.getByRole('menuitem', { name: /settings/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /sign out/i })).toBeInTheDocument();
  });
});
