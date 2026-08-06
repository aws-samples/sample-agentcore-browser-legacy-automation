// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * TopBar smoke test — verifies the bar renders with its test id.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { TopBar } from '../../../../src/components/TopBar/TopBar';

describe('TopBar', () => {
  it('renders the top-bar landmark', () => {
    render(<TopBar />);
    expect(screen.getByTestId('top-bar')).toBeInTheDocument();
  });
});
