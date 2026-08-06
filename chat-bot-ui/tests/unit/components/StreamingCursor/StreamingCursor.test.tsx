// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * StreamingCursor smoke test — verifies the cursor renders with the
 * expected aria-hidden + test id.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StreamingCursor } from '../../../../src/components/StreamingCursor/StreamingCursor';

describe('StreamingCursor', () => {
  it('renders a span with the streaming-cursor test id', () => {
    render(<StreamingCursor />);
    const cursor = screen.getByTestId('streaming-cursor');
    expect(cursor).toBeInTheDocument();
    expect(cursor).toHaveAttribute('aria-hidden', 'true');
  });
});
