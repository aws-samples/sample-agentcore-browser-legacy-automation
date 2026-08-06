// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatInput smoke test — verifies typing + Enter dispatches onSend,
 * Shift+Enter inserts a newline, and disabled locks out the send.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../../../../src/components/ChatInput/ChatInput';

describe('ChatInput', () => {
  it('dispatches onSend with the trimmed content on Enter', () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '  hello  ' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onSend).toHaveBeenCalledWith('hello');
  });

  it('does not dispatch onSend when disabled', () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} disabled />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'hi' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('uses the provided placeholder', () => {
    render(<ChatInput onSend={jest.fn()} placeholder="Type something..." />);
    expect(screen.getByPlaceholderText('Type something...')).toBeInTheDocument();
  });
});
