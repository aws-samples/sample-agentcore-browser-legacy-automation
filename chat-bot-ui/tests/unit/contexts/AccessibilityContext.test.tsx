// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AccessibilityContext Tests
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AccessibilityProvider, useAccessibility } from '../../../src/contexts/AccessibilityContext';

// Test component that uses the accessibility context
const TestComponent: React.FC = () => {
  const {
    settings,
    updateSettings,
    announceToScreenReader,
    isHighContrast,
    isReducedMotion,
    toggleHighContrast,
    toggleReducedMotion,
  } = useAccessibility();

  return (
    <div>
      <div data-testid="high-contrast">{isHighContrast.toString()}</div>
      <div data-testid="reduced-motion">{isReducedMotion.toString()}</div>
      <div data-testid="font-size">{settings.fontSize}</div>

      <button onClick={toggleHighContrast}>Toggle High Contrast</button>
      <button onClick={toggleReducedMotion}>Toggle Reduced Motion</button>
      <button onClick={() => updateSettings({ fontSize: 'large' })}>
        Set Large Font
      </button>
      <button onClick={() => announceToScreenReader('Test announcement')}>
        Announce
      </button>
    </div>
  );
};

describe('AccessibilityContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();

    // Reset document attributes
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.className = '';
  });

  it('provides default accessibility settings', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    expect(screen.getByTestId('high-contrast')).toHaveTextContent('false');
    expect(screen.getByTestId('reduced-motion')).toHaveTextContent('false');
    expect(screen.getByTestId('font-size')).toHaveTextContent('medium');
  });

  it('toggles high contrast mode', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    const toggleButton = screen.getByText('Toggle High Contrast');

    act(() => {
      fireEvent.click(toggleButton);
    });

    expect(screen.getByTestId('high-contrast')).toHaveTextContent('true');
    expect(document.documentElement).toHaveAttribute('data-theme', 'high-contrast');
    expect(document.documentElement).toHaveClass('theme-high-contrast');
  });

  it('toggles reduced motion mode', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    const toggleButton = screen.getByText('Toggle Reduced Motion');

    act(() => {
      fireEvent.click(toggleButton);
    });

    expect(screen.getByTestId('reduced-motion')).toHaveTextContent('true');
  });

  it('updates font size setting', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    const fontButton = screen.getByText('Set Large Font');

    act(() => {
      fireEvent.click(fontButton);
    });

    expect(screen.getByTestId('font-size')).toHaveTextContent('large');
  });

  it('persists settings to localStorage', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    const toggleButton = screen.getByText('Toggle High Contrast');

    act(() => {
      fireEvent.click(toggleButton);
    });

    const savedSettings = JSON.parse(localStorage.getItem('browser-agent-accessibility-settings') || '{}');
    expect(savedSettings.highContrast).toBe(true);
  });

  it('loads settings from localStorage', () => {
    // Pre-populate localStorage
    const settings = {
      highContrast: true,
      reducedMotion: false,
      screenReaderMode: false,
      keyboardNavigation: true,
      fontSize: 'large',
      announcements: true,
    };
    localStorage.setItem('browser-agent-accessibility-settings', JSON.stringify(settings));

    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    expect(screen.getByTestId('high-contrast')).toHaveTextContent('true');
    expect(screen.getByTestId('font-size')).toHaveTextContent('large');
  });

  it('creates screen reader announcements', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    const announceButton = screen.getByText('Announce');

    act(() => {
      fireEvent.click(announceButton);
    });

    // Check that an announcement element was created
    const announcement = document.querySelector('[aria-live="polite"]');
    expect(announcement).toBeInTheDocument();
    expect(announcement).toHaveTextContent('Test announcement');
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAccessibility must be used within an AccessibilityProvider');

    consoleSpy.mockRestore();
  });
});