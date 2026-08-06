// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Theme Configuration Tests
 * Testing Material-UI theme definitions and theme management
 */

import { createTheme } from '@mui/material/styles';
import {
  THEME_CONFIGS,
  THEME_MAP,
  getTheme,
  DEFAULT_THEME,
  lightTheme,
  darkTheme,
  blueTheme,
  highContrastTheme,
  compactLightTheme,
  compactDarkTheme,
  modernLightTheme,
  modernDarkTheme,
} from '../../../src/theme/themeConfig';
import { ThemeOption } from '../../../src/types/ui.types';

describe('Theme Configuration', () => {
  describe('THEME_CONFIGS', () => {
    test('should include all required theme configurations', () => {
      const expectedThemes: ThemeOption[] = [
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

      expect(THEME_CONFIGS).toHaveLength(expectedThemes.length);

      expectedThemes.forEach((themeName) => {
        const config = THEME_CONFIGS.find((cfg) => cfg.name === themeName);
        expect(config).toBeDefined();
        expect(config?.displayName).toBeTruthy();
        expect(config?.description).toBeTruthy();
      });
    });

    test('should have descriptive descriptions', () => {
      THEME_CONFIGS.forEach((config) => {
        expect(config.description).toBeTruthy();
        expect(config.description.length).toBeGreaterThan(10);
      });
    });

    test('should not contain sunlife theme', () => {
      expect(THEME_CONFIGS.find((c) => c.name === ('sunlife' as ThemeOption))).toBeUndefined();
    });
  });

  describe('Individual Themes', () => {
    test('lightTheme should have correct palette mode', () => {
      expect(lightTheme.palette.mode).toBe('light');
    });

    test('darkTheme should have correct palette mode', () => {
      expect(darkTheme.palette.mode).toBe('dark');
    });

    test('blueTheme should be a light-mode palette', () => {
      expect(blueTheme.palette.mode).toBe('light');
    });

    test('highContrastTheme should have maximum contrast colors', () => {
      expect(highContrastTheme.palette.mode).toBe('light');
      expect(highContrastTheme.palette.primary.main).toBe('#000000');
      expect(highContrastTheme.palette.background.default).toBe('#ffffff');
      expect(highContrastTheme.palette.text.primary).toBe('#000000');
      expect(highContrastTheme.palette.divider).toBe('#000000');
    });

    test('compactLightTheme should have light palette and compact sizing', () => {
      expect(compactLightTheme.palette.mode).toBe('light');
      expect(compactLightTheme.shape.borderRadius).toBe(10);
    });

    test('compactDarkTheme should have dark palette and compact sizing', () => {
      expect(compactDarkTheme.palette.mode).toBe('dark');
      expect(compactDarkTheme.shape.borderRadius).toBe(10);
    });

    test('modernLightTheme should be defined and light-mode', () => {
      expect(modernLightTheme.palette.mode).toBe('light');
    });

    test('modernDarkTheme should be defined and dark-mode', () => {
      expect(modernDarkTheme.palette.mode).toBe('dark');
    });
  });

  describe('Theme Typography', () => {
    test('standard themes should have consistent typography', () => {
      const themes = [lightTheme, darkTheme, blueTheme, highContrastTheme];

      themes.forEach((theme) => {
        expect(theme.typography.fontFamily).toBe('"Roboto", "Helvetica", "Arial", sans-serif');
        expect(theme.typography.h1.fontSize).toBe('2.5rem');
        expect(theme.typography.body1.fontSize).toBe('1rem');
        expect(theme.typography.body1.lineHeight).toBe(1.5);
      });
    });
  });

  describe('Theme Shape and Spacing', () => {
    test('standard themes should have consistent shape and spacing', () => {
      const themes = [lightTheme, darkTheme, blueTheme, highContrastTheme];

      themes.forEach((theme) => {
        expect(theme.shape.borderRadius).toBe(8);
        expect(theme.spacing(1)).toBe('8px');
      });
    });
  });

  describe('THEME_MAP', () => {
    test('should map all theme options to Material-UI themes', () => {
      const expectedThemes: ThemeOption[] = [
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

      expectedThemes.forEach((themeName) => {
        expect(THEME_MAP[themeName]).toBeDefined();
        expect(THEME_MAP[themeName].palette).toBeDefined();
      });
    });

    test('should not contain sunlife key', () => {
      expect((THEME_MAP as Record<string, unknown>)['sunlife']).toBeUndefined();
    });
  });

  describe('getTheme function', () => {
    test('should return correct theme for non-auto themes', () => {
      expect(getTheme('light')).toBe(lightTheme);
      expect(getTheme('dark')).toBe(darkTheme);
      expect(getTheme('blue')).toBe(blueTheme);
      expect(getTheme('high-contrast')).toBe(highContrastTheme);
      expect(getTheme('compact-light')).toBe(compactLightTheme);
      expect(getTheme('compact-dark')).toBe(compactDarkTheme);
      expect(getTheme('modern-light')).toBe(modernLightTheme);
      expect(getTheme('modern-dark')).toBe(modernDarkTheme);
    });

    test('should return light theme for auto when prefersDark is false', () => {
      expect(getTheme('auto', false)).toBe(lightTheme);
    });

    test('should return dark theme for auto when prefersDark is true', () => {
      expect(getTheme('auto', true)).toBe(darkTheme);
    });
  });

  describe('DEFAULT_THEME', () => {
    test('should be set to auto', () => {
      expect(DEFAULT_THEME).toBe('auto');
    });
  });

  describe('Theme Validation', () => {
    test('all themes should be valid Material-UI themes', () => {
      const themes = [
        lightTheme,
        darkTheme,
        blueTheme,
        highContrastTheme,
        compactLightTheme,
        compactDarkTheme,
        modernLightTheme,
        modernDarkTheme,
      ];

      themes.forEach((theme) => {
        expect(() => createTheme(theme)).not.toThrow();
        expect(theme.palette).toBeDefined();
        expect(theme.typography).toBeDefined();
      });
    });
  });
});
