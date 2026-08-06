// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatView smoke test — empty state + user message rendering.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { AccessibilityProvider } from '../../../../src/contexts/AccessibilityContext';
import { ChatView } from '../../../../src/components/ChatView/ChatView';
import type {
  BrowserChatMessage,
  BrowserSessionState,
} from '../../../../src/types/browser.types';

const INITIAL_SESSION: BrowserSessionState = {
  isActive: false,
  liveViewUrl: null,
  stepCounter: 0,
  pendingHitl: null,
};

const wrap = (children: React.ReactNode) => (
  <AccessibilityProvider>{children}</AccessibilityProvider>
);

describe('ChatView', () => {
  it('renders the empty state when there are no messages', () => {
    render(
      wrap(
        <ChatView
          messages={[]}
          browserSession={INITIAL_SESSION}
          connectionState="connected"
          isStreaming={false}
          onSendMessage={jest.fn()}
          onStopBrowser={jest.fn()}
          onToggleLiveView={jest.fn()}
        />,
      ),
    );
    expect(screen.getByTestId('browser-empty-state')).toBeInTheDocument();
  });

  it('renders a user message', () => {
    const msg: BrowserChatMessage = {
      id: 'u1',
      role: 'user',
      content: 'open wikipedia',
      timestamp: new Date().toISOString(),
    };
    render(
      wrap(
        <ChatView
          messages={[msg]}
          browserSession={INITIAL_SESSION}
          connectionState="connected"
          isStreaming={false}
          onSendMessage={jest.fn()}
          onStopBrowser={jest.fn()}
          onToggleLiveView={jest.fn()}
        />,
      ),
    );
    expect(screen.getByText(/open wikipedia/i)).toBeInTheDocument();
  });
});
