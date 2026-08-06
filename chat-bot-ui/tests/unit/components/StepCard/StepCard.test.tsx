// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * StepCard smoke test — verifies rendering for a succeeded action step.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StepCard } from '../../../../src/components/StepCard/StepCard';
import type { BrowserStep } from '../../../../src/utils/browserSteps';

const step: BrowserStep = {
  stepNumber: 1,
  status: 'succeeded',
  summary: 'click the button',
  action: {
    stepNumber: 1,
    actionType: 'browser',
    details: 'click the button',
    status: 'succeeded',
  },
  reasoning: '',
};

describe('StepCard', () => {
  it('renders the step summary in the header', () => {
    render(<StepCard step={step} />);
    expect(screen.getByText(/click the button/i)).toBeInTheDocument();
  });
});
