// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ThemeManager smoke test — renders children and exposes theme context.
 */

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { ThemeManager, useTheme } from '../../../../src/components/ThemeManager/ThemeManager';

const ThemeConsumer: React.FC = () => {
  const { currentTheme, setTheme } = useTheme();
  return (
    <div>
      <div data-testid="theme">{currentTheme}</div>
      <button onClick={() => setTheme('dark')}>dark</button>
    </div>
  );
};

describe('ThemeManager', () => {
  it('renders children and exposes a usable theme context', () => {
    render(
      <ThemeManager>
        <ThemeConsumer />
      </ThemeManager>,
    );
    expect(screen.getByTestId('theme')).toBeInTheDocument();
  });

  it('updates the context when setTheme is called', () => {
    render(
      <ThemeManager>
        <ThemeConsumer />
      </ThemeManager>,
    );
    act(() => {
      screen.getByText('dark').click();
    });
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });
});
