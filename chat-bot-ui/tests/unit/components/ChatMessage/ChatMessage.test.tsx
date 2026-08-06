// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatMessage smoke test — renders both user and assistant variants.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from '../../../../src/components/ChatMessage/ChatMessage';
import type { ChatMessage as ChatMessageType } from '../../../../src/types/browser.types';

describe('ChatMessage', () => {
  it('renders a user message with its content and test id', () => {
    const msg: ChatMessageType = {
      id: 'user-1',
      role: 'user',
      content: 'Hello, agent',
      timestamp: new Date().toISOString(),
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByTestId('chat-message-user-1')).toBeInTheDocument();
    expect(screen.getByText('Hello, agent')).toBeInTheDocument();
  });

  it('renders an assistant message', () => {
    const msg: ChatMessageType = {
      id: 'assistant-1',
      role: 'assistant',
      content: 'Response text',
      timestamp: new Date().toISOString(),
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByTestId('chat-message-assistant-1')).toBeInTheDocument();
  });
});
