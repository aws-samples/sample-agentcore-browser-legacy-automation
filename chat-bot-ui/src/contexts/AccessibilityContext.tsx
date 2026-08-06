// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AccessibilityContext - Provides accessibility features and settings
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface AccessibilitySettings {
  highContrast: boolean;
  reducedMotion: boolean;
  screenReaderMode: boolean;
  keyboardNavigation: boolean;
  fontSize: 'small' | 'medium' | 'large';
  announcements: boolean;
}

export interface AccessibilityContextType {
  settings: AccessibilitySettings;
  updateSettings: (newSettings: Partial<AccessibilitySettings>) => void;
  announceToScreenReader: (message: string, priority?: 'polite' | 'assertive') => void;
  isHighContrast: boolean;
  isReducedMotion: boolean;
  isScreenReaderMode: boolean;
  toggleHighContrast: () => void;
  toggleReducedMotion: () => void;
  toggleScreenReaderMode: () => void;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

export const useAccessibility = (): AccessibilityContextType => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  // Load settings from localStorage or use defaults
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    const saved = localStorage.getItem('browser-agent-accessibility-settings');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (error) {
        console.warn('Failed to parse accessibility settings from localStorage:', error);
      }
    }

    // Default settings based on system preferences
    return {
      highContrast: window.matchMedia('(prefers-contrast: high)').matches,
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      screenReaderMode: false,
      keyboardNavigation: true,
      fontSize: 'medium',
      announcements: true,
    };
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('browser-agent-accessibility-settings', JSON.stringify(settings));
  }, [settings]);

  // Listen for system preference changes
  useEffect(() => {
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, highContrast: e.matches }));
    };

    const handleMotionChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, reducedMotion: e.matches }));
    };

    contrastQuery.addEventListener('change', handleContrastChange);
    motionQuery.addEventListener('change', handleMotionChange);

    return () => {
      contrastQuery.removeEventListener('change', handleContrastChange);
      motionQuery.removeEventListener('change', handleMotionChange);
    };
  }, []);

  // Apply accessibility settings to document
  useEffect(() => {
    const root = document.documentElement;

    // Apply high contrast theme
    if (settings.highContrast) {
      root.setAttribute('data-theme', 'high-contrast');
      root.classList.add('theme-high-contrast');
    } else {
      root.classList.remove('theme-high-contrast');
      if (root.getAttribute('data-theme') === 'high-contrast') {
        root.removeAttribute('data-theme');
      }
    }

    // Apply reduced motion
    if (settings.reducedMotion) {
      root.style.setProperty('--animation-duration', '0.01ms');
      root.style.setProperty('--transition-duration', '0.01ms');
    } else {
      root.style.removeProperty('--animation-duration');
      root.style.removeProperty('--transition-duration');
    }

    // Apply font size
    switch (settings.fontSize) {
      case 'small':
        root.style.setProperty('--base-font-size', '14px');
        break;
      case 'large':
        root.style.setProperty('--base-font-size', '18px');
        break;
      default:
        root.style.setProperty('--base-font-size', '16px');
        break;
    }

    // Apply screen reader mode
    if (settings.screenReaderMode) {
      root.classList.add('screen-reader-mode');
    } else {
      root.classList.remove('screen-reader-mode');
    }
  }, [settings]);

  const updateSettings = useCallback((newSettings: Partial<AccessibilitySettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  const announceToScreenReader = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!settings.announcements) return;

    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
      if (document.body.contains(announcement)) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }, [settings.announcements]);

  const toggleHighContrast = useCallback(() => {
    setSettings(prev => ({ ...prev, highContrast: !prev.highContrast }));
  }, []);

  const toggleReducedMotion = useCallback(() => {
    setSettings(prev => ({ ...prev, reducedMotion: !prev.reducedMotion }));
  }, []);

  const toggleScreenReaderMode = useCallback(() => {
    setSettings(prev => ({ ...prev, screenReaderMode: !prev.screenReaderMode }));
  }, []);

  const value: AccessibilityContextType = {
    settings,
    updateSettings,
    announceToScreenReader,
    isHighContrast: settings.highContrast,
    isReducedMotion: settings.reducedMotion,
    isScreenReaderMode: settings.screenReaderMode,
    toggleHighContrast,
    toggleReducedMotion,
    toggleScreenReaderMode,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
};

export default AccessibilityContext;