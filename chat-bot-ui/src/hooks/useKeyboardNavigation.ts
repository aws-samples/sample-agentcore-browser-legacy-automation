// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * useKeyboardNavigation Hook
 * Provides keyboard navigation and accessibility features for the Browser Agent UI
 */

import { useEffect, useCallback, useRef } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  action: () => void;
  description: string;
  preventDefault?: boolean;
}

export interface UseKeyboardNavigationProps {
  shortcuts?: KeyboardShortcut[];
  onEscape?: () => void;
  onEnter?: () => void;
  onArrowUp?: () => void;
  onArrowDown?: () => void;
  onArrowLeft?: () => void;
  onArrowRight?: () => void;
  onTab?: (event: KeyboardEvent) => void;
  enabled?: boolean;
}

export const useKeyboardNavigation = ({
  shortcuts = [],
  onEscape,
  onEnter,
  onArrowUp,
  onArrowDown,
  onArrowLeft,
  onArrowRight,
  onTab,
  enabled = true,
}: UseKeyboardNavigationProps = {}) => {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  // Handle keyboard events
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    const { key, ctrlKey, altKey, shiftKey, metaKey } = event;

    // Handle basic navigation keys
    switch (key) {
      case 'Escape':
        if (onEscape) {
          event.preventDefault();
          onEscape();
        }
        break;
      case 'Enter':
        if (onEnter) {
          event.preventDefault();
          onEnter();
        }
        break;
      case 'ArrowUp':
        if (onArrowUp) {
          event.preventDefault();
          onArrowUp();
        }
        break;
      case 'ArrowDown':
        if (onArrowDown) {
          event.preventDefault();
          onArrowDown();
        }
        break;
      case 'ArrowLeft':
        if (onArrowLeft) {
          event.preventDefault();
          onArrowLeft();
        }
        break;
      case 'ArrowRight':
        if (onArrowRight) {
          event.preventDefault();
          onArrowRight();
        }
        break;
      case 'Tab':
        if (onTab) {
          onTab(event);
        }
        break;
    }

    // Handle custom shortcuts
    for (const shortcut of shortcutsRef.current) {
      const keyMatches = shortcut.key.toLowerCase() === key.toLowerCase();
      const ctrlMatches = (shortcut.ctrlKey ?? false) === ctrlKey;
      const altMatches = (shortcut.altKey ?? false) === altKey;
      const shiftMatches = (shortcut.shiftKey ?? false) === shiftKey;
      const metaMatches = (shortcut.metaKey ?? false) === metaKey;

      if (keyMatches && ctrlMatches && altMatches && shiftMatches && metaMatches) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.action();
        break;
      }
    }
  }, [enabled, onEscape, onEnter, onArrowUp, onArrowDown, onArrowLeft, onArrowRight, onTab]);

  // Set up event listeners
  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);

  // Focus management utilities
  const focusElement = useCallback((selector: string) => {
    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
      element.focus();
    }
  }, []);

  const focusFirstFocusableElement = useCallback((container?: HTMLElement) => {
    const containerElement = container || document.body;
    const focusableElements = containerElement.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    if (firstElement) {
      firstElement.focus();
    }
  }, []);

  const focusLastFocusableElement = useCallback((container?: HTMLElement) => {
    const containerElement = container || document.body;
    const focusableElements = containerElement.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
    if (lastElement) {
      lastElement.focus();
    }
  }, []);

  // Trap focus within a container (useful for modals)
  const trapFocus = useCallback((container: HTMLElement) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    container.addEventListener('keydown', handleTabKey);
    return () => {
      container.removeEventListener('keydown', handleTabKey);
    };
  }, []);

  // Announce to screen readers
  const announceToScreenReader = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }, []);

  return {
    focusElement,
    focusFirstFocusableElement,
    focusLastFocusableElement,
    trapFocus,
    announceToScreenReader,
  };
};

// Default keyboard shortcuts for the application
export const getDefaultKeyboardShortcuts = (
  onToggleSidebar: () => void,
  onNewChat: () => void,
  onOpenSettings: () => void,
  onShowKeyboardShortcuts: () => void
): KeyboardShortcut[] => [
  {
    key: 'b',
    ctrlKey: true,
    action: onToggleSidebar,
    description: 'Toggle sidebar',
  },
  {
    key: 'n',
    ctrlKey: true,
    action: onNewChat,
    description: 'Start new chat',
  },
  {
    key: ',',
    ctrlKey: true,
    action: onOpenSettings,
    description: 'Open settings',
  },
  {
    key: '/',
    ctrlKey: true,
    action: onShowKeyboardShortcuts,
    description: 'Show keyboard shortcuts',
  },
  {
    key: 'Escape',
    action: () => {
      // Close any open modals or overlays
      const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape' });
      document.dispatchEvent(escapeEvent);
    },
    description: 'Close modal or overlay',
    preventDefault: false,
  },
];

// Hook for managing focus within a specific component
export const useFocusManagement = (containerRef: React.RefObject<HTMLElement>) => {
  const { focusFirstFocusableElement, focusLastFocusableElement, trapFocus } = useKeyboardNavigation();

  const focusFirst = useCallback(() => {
    if (containerRef.current) {
      focusFirstFocusableElement(containerRef.current);
    }
  }, [containerRef, focusFirstFocusableElement]);

  const focusLast = useCallback(() => {
    if (containerRef.current) {
      focusLastFocusableElement(containerRef.current);
    }
  }, [containerRef, focusLastFocusableElement]);

  const enableFocusTrap = useCallback(() => {
    if (containerRef.current) {
      return trapFocus(containerRef.current);
    }
  }, [containerRef, trapFocus]);

  return {
    focusFirst,
    focusLast,
    enableFocusTrap,
  };
};

export default useKeyboardNavigation;