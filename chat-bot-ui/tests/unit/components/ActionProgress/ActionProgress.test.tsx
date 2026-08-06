// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ActionProgress smoke test — renders step number, action type, and details.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ActionProgress } from '../../../../src/components/ActionProgress/ActionProgress';

describe('ActionProgress', () => {
  it('renders the step label, action type, and details', () => {
    render(
      <ActionProgress
        stepNumber={3}
        actionType="navigate"
        details="https://example.com"
        status="succeeded"
      />,
    );
    expect(screen.getByText('#3')).toBeInTheDocument();
    expect(screen.getByText(/navigate/i)).toBeInTheDocument();
  });

  it('omits the result toggle when result is empty', () => {
    render(
      <ActionProgress
        stepNumber={1}
        actionType="browser"
        details="x"
        status="succeeded"
      />,
    );
    expect(screen.queryByRole('button', { name: /expand/i })).not.toBeInTheDocument();
  });
});
