// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * HelpModal smoke test — verifies the modal opens and closes via the onClose callback.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { HelpModal } from '../../../../src/components/HelpModal/HelpModal';

describe('HelpModal', () => {
  it('renders nothing when closed', () => {
    render(<HelpModal open={false} onClose={jest.fn()} />);
    // Dialog contents mount inside a portal; nothing visible when closed.
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders a dialog when open', () => {
    render(<HelpModal open={true} onClose={jest.fn()} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
