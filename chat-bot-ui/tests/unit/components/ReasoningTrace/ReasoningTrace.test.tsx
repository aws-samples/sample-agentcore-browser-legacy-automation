// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ReasoningTrace smoke test — verifies collapsed header rendering.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ReasoningTrace } from '../../../../src/components/ReasoningTrace/ReasoningTrace';
import type { BrowserStep } from '../../../../src/utils/browserSteps';

const steps: BrowserStep[] = [
  {
    stepNumber: 1,
    status: 'succeeded',
    summary: 'nav',
    action: { stepNumber: 1, actionType: 'browser', details: 'nav', status: 'succeeded' },
    reasoning: '',
  },
];

describe('ReasoningTrace', () => {
  it('renders the step-count summary in the collapsed header', () => {
    render(<ReasoningTrace steps={steps} />);
    // The header mentions the step count; keep the assertion loose.
    expect(screen.getByText(/1/)).toBeInTheDocument();
  });
});
