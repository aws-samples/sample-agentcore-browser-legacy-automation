// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * KeyboardShortcuts smoke test — opens the modal and verifies the
 * shortcut descriptions render.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { KeyboardShortcuts } from '../../../../src/components/KeyboardShortcuts/KeyboardShortcuts';

describe('KeyboardShortcuts', () => {
  it('renders nothing when closed', () => {
    render(<KeyboardShortcuts isOpen={false} onClose={jest.fn()} />);
    expect(screen.queryByText(/toggle sidebar/i)).not.toBeInTheDocument();
  });

  it('renders the shortcut list when open', () => {
    render(<KeyboardShortcuts isOpen={true} onClose={jest.fn()} />);
    expect(screen.getByText(/toggle sidebar/i)).toBeInTheDocument();
    expect(screen.getByText(/start new chat/i)).toBeInTheDocument();
  });
});
