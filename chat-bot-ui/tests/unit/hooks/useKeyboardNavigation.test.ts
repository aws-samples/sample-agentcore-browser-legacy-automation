// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * useKeyboardNavigation smoke test — verifies keyboard event wiring,
 * default shortcut definitions, and the focus-management helpers.
 */

import { renderHook, act } from '@testing-library/react';
import {
  useKeyboardNavigation,
  getDefaultKeyboardShortcuts,
} from '../../../src/hooks/useKeyboardNavigation';

describe('useKeyboardNavigation', () => {
  it('calls onEscape when Escape is pressed while enabled', () => {
    const onEscape = jest.fn();
    renderHook(() => useKeyboardNavigation({ onEscape, enabled: true }));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });

    expect(onEscape).toHaveBeenCalledTimes(1);
  });

  it('does not call handlers when disabled', () => {
    const onEscape = jest.fn();
    renderHook(() => useKeyboardNavigation({ onEscape, enabled: false }));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });

    expect(onEscape).not.toHaveBeenCalled();
  });

  it('dispatches a registered custom shortcut when its modifier set matches', () => {
    const action = jest.fn();
    const shortcuts = [
      {
        key: 'b',
        ctrlKey: true,
        action,
        description: 'toggle sidebar',
      },
    ];
    renderHook(() => useKeyboardNavigation({ shortcuts }));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', ctrlKey: true }));
    });

    expect(action).toHaveBeenCalledTimes(1);
  });

  it('exposes focus-management helpers', () => {
    const { result } = renderHook(() => useKeyboardNavigation());
    expect(typeof result.current.focusElement).toBe('function');
    expect(typeof result.current.focusFirstFocusableElement).toBe('function');
    expect(typeof result.current.focusLastFocusableElement).toBe('function');
    expect(typeof result.current.trapFocus).toBe('function');
    expect(typeof result.current.announceToScreenReader).toBe('function');
  });
});

describe('getDefaultKeyboardShortcuts', () => {
  it('wires the four app-level shortcuts plus an Escape handler', () => {
    const onToggleSidebar = jest.fn();
    const onNewChat = jest.fn();
    const onOpenSettings = jest.fn();
    const onShowKeyboardShortcuts = jest.fn();

    const shortcuts = getDefaultKeyboardShortcuts(
      onToggleSidebar,
      onNewChat,
      onOpenSettings,
      onShowKeyboardShortcuts,
    );

    const byKey = (key: string) => shortcuts.find((s) => s.key === key);
    expect(byKey('b')?.ctrlKey).toBe(true);
    expect(byKey('n')?.ctrlKey).toBe(true);
    expect(byKey(',')?.ctrlKey).toBe(true);
    expect(byKey('/')?.ctrlKey).toBe(true);
    expect(byKey('Escape')).toBeDefined();

    byKey('b')!.action();
    byKey('n')!.action();
    byKey(',')!.action();
    byKey('/')!.action();

    expect(onToggleSidebar).toHaveBeenCalledTimes(1);
    expect(onNewChat).toHaveBeenCalledTimes(1);
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    expect(onShowKeyboardShortcuts).toHaveBeenCalledTimes(1);
  });
});
