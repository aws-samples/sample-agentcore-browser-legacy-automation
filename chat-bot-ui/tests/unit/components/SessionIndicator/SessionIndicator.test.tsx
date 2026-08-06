// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SessionIndicator smoke test — renders and forwards the Stop / toggle callbacks.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AccessibilityProvider } from '../../../../src/contexts/AccessibilityContext';
import { SessionIndicator } from '../../../../src/components/SessionIndicator/SessionIndicator';

describe('SessionIndicator', () => {
  it('fires onStop when the Stop button is clicked', () => {
    const onStop = jest.fn();
    render(
      <AccessibilityProvider>
        <SessionIndicator stepCounter={3} onStop={onStop} onToggleLiveView={jest.fn()} />
      </AccessibilityProvider>,
    );
    fireEvent.click(screen.getByRole('button', { name: /stop/i }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });
});
