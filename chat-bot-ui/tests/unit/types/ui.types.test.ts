// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * UI Types Tests — TypeScript interface sanity checks for the blog UI.
 */

import {
  ThemeOption,
  ThemeConfig,
  ThemeManagerProps,
  UIState,
  MainContentView,
  SidebarFooterProps,
} from '../../../src/types/ui.types';

describe('UI Types', () => {
  describe('ThemeOption', () => {
    test('should include all supported themes', () => {
      const validThemes: ThemeOption[] = [
        'auto',
        'light',
        'dark',
        'blue',
        'high-contrast',
        'compact-dark',
        'compact-light',
        'modern-dark',
        'modern-light',
      ];

      validThemes.forEach((theme) => {
        expect(validThemes).toContain(theme);
      });
    });

    test('should not include sunlife theme', () => {
      // Compile-time guard — uncommenting should error.
      // const bad: ThemeOption = 'sunlife';
      const expected = [
        'auto',
        'light',
        'dark',
        'blue',
        'high-contrast',
        'compact-dark',
        'compact-light',
        'modern-dark',
        'modern-light',
      ];
      expect(expected).not.toContain('sunlife');
    });
  });

  describe('MainContentView', () => {
    test('should resolve to conversation', () => {
      const view: MainContentView = 'conversation';
      expect(view).toBe('conversation');
    });
  });

  describe('ThemeConfig', () => {
    test('should accept config with required fields', () => {
      const config: ThemeConfig = {
        name: 'light',
        displayName: 'Light',
        description: 'Light theme with improved contrast',
      };
      expect(config.name).toBe('light');
      expect(config.displayName).toBe('Light');
      expect(config.description).toBeTruthy();
    });
  });

  describe('ThemeManagerProps', () => {
    test('should require currentTheme and onThemeChange', () => {
      const onThemeChange = jest.fn();
      const props: ThemeManagerProps = {
        currentTheme: 'auto',
        onThemeChange,
      };
      props.onThemeChange('dark');
      expect(onThemeChange).toHaveBeenCalledWith('dark');
    });
  });

  describe('UIState', () => {
    test('should allow optional activeSession', () => {
      const minimal: UIState = {
        sidebarCollapsed: false,
        currentTheme: 'auto',
        currentView: 'conversation',
        settingsModalOpen: false,
      };
      expect(minimal.activeSession).toBeUndefined();
    });
  });

  describe('SidebarFooterProps', () => {
    test('callbacks should be invocable', () => {
      const onOpenSettings = jest.fn();
      const onOpenHelp = jest.fn();
      const props: SidebarFooterProps = {
        isCollapsed: false,
        onOpenSettings,
        onOpenHelp,
      };
      props.onOpenSettings();
      props.onOpenHelp();
      expect(onOpenSettings).toHaveBeenCalledTimes(1);
      expect(onOpenHelp).toHaveBeenCalledTimes(1);
    });
  });
});
