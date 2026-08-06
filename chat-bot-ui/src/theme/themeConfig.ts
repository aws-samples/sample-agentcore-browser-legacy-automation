// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { createTheme, Theme, ThemeOptions } from '@mui/material/styles';
import { ThemeOption, ThemeConfig } from '../types/ui.types';

// Theme configuration definitions
export const THEME_CONFIGS: ThemeConfig[] = [
  {
    name: 'auto',
    displayName: 'Auto (System)',
    description: 'Automatically follows your system theme preference'
  },
  {
    name: 'light',
    displayName: 'Light',
    description: 'Light theme with improved contrast'
  },
  {
    name: 'dark',
    displayName: 'Dark',
    description: 'Professional dark mode'
  },
  {
    name: 'blue',
    displayName: 'Blue',
    description: 'Clean blue theme'
  },
  {
    name: 'high-contrast',
    displayName: 'High Contrast',
    description: 'Maximum accessibility with stark contrasts'
  },
  {
    name: 'compact-dark',
    displayName: 'Compact Dark',
    description: 'Compact dark theme with reduced spacing'
  },
  {
    name: 'compact-light',
    displayName: 'Compact Light',
    description: 'Compact light theme with reduced spacing'
  },
  {
    name: 'modern-dark',
    displayName: 'Modern Dark',
    description: 'Modern dark theme with indigo accent'
  },
  {
    name: 'modern-light',
    displayName: 'Modern Light',
    description: 'Modern light theme with indigo accent'
  }
];

// Base theme configuration shared across all themes
const baseThemeOptions: ThemeOptions = {
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.43,
    },
  },
  shape: {
    borderRadius: 8,
  },
  spacing: 8,
  components: {
    // Global component overrides
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: 'rgba(0,0,0,0.2)',
            borderRadius: '4px',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
};

// Light theme (improved darker variant)
export const lightTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a1a',
      secondary: '#424242',
    },
    divider: '#bdbdbd',
    action: {
      hover: 'rgba(0, 0, 0, 0.04)',
      selected: 'rgba(0, 0, 0, 0.08)',
    },
    success: {
      main: '#4caf50',
    },
    warning: {
      main: '#ff9800',
    },
    error: {
      main: '#f44336',
    },
    info: {
      main: '#2196f3',
    },
  },
});

// Dark theme
export const darkTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
      light: '#e3f2fd',
      dark: '#42a5f5',
      contrastText: '#000000',
    },
    secondary: {
      main: '#f48fb1',
      light: '#ffc1e3',
      dark: '#bf5f82',
      contrastText: '#000000',
    },
    background: {
      default: '#1a1a1a',
      paper: '#2d2d2d',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b3b3b3',
    },
    divider: '#404040',
    action: {
      hover: 'rgba(255, 255, 255, 0.08)',
      selected: 'rgba(255, 255, 255, 0.12)',
    },
    success: {
      main: '#66bb6a',
    },
    warning: {
      main: '#ffb74d',
    },
    error: {
      main: '#ef5350',
    },
    info: {
      main: '#42a5f5',
    },
  },
});

// Blue theme (clean blue)
export const blueTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#0d47a1',
      light: '#5472d3',
      dark: '#002171',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    background: {
      default: '#e3f2fd',
      paper: '#ffffff',
    },
    text: {
      primary: '#0d47a1',
      secondary: '#1565c0',
    },
    divider: '#90caf9',
    action: {
      hover: 'rgba(13, 71, 161, 0.04)',
      selected: 'rgba(13, 71, 161, 0.08)',
    },
    success: {
      main: '#2e7d32',
    },
    warning: {
      main: '#f57c00',
    },
    error: {
      main: '#c62828',
    },
    info: {
      main: '#1565c0',
    },
  },
});

// High contrast theme
export const highContrastTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#000000',
      light: '#333333',
      dark: '#000000',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ffffff',
      light: '#ffffff',
      dark: '#cccccc',
      contrastText: '#000000',
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
    text: {
      primary: '#000000',
      secondary: '#333333',
    },
    divider: '#000000',
    action: {
      hover: 'rgba(0, 0, 0, 0.1)',
      selected: 'rgba(0, 0, 0, 0.2)',
    },
    success: {
      main: '#006600',
    },
    warning: {
      main: '#cc6600',
    },
    error: {
      main: '#cc0000',
    },
    info: {
      main: '#0066cc',
    },
  },
});

// Compact base theme options — Inter font, smaller sizes, tighter spacing
const compactBaseThemeOptions: ThemeOptions = {
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: 13.6, // ~0.85rem base
    h1: { fontSize: '2rem', fontWeight: 600 },
    h2: { fontSize: '1.65rem', fontWeight: 600 },
    h3: { fontSize: '1.4rem', fontWeight: 600 },
    h4: { fontSize: '1.2rem', fontWeight: 600 },
    h5: { fontSize: '1.05rem', fontWeight: 600 },
    h6: { fontSize: '0.85rem', fontWeight: 600 },
    body1: { fontSize: '0.85rem', lineHeight: 1.55 },
    body2: { fontSize: '0.775rem', lineHeight: 1.43 },
    caption: { fontSize: '0.7rem' },
  },
  shape: { borderRadius: 10 },
  spacing: 6,
  components: {
    ...baseThemeOptions.components,
  },
};

// Compact Dark theme — mock-ui inspired dark palette with indigo accent
export const compactDarkTheme = createTheme({
  ...compactBaseThemeOptions,
  palette: {
    mode: 'dark',
    primary: {
      main: '#818cf8',
      light: '#a5b4fc',
      dark: '#6366f1',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#f48fb1',
      light: '#ffc1e3',
      dark: '#bf5f82',
      contrastText: '#000000',
    },
    background: {
      default: '#0f0f0f',
      paper: '#171717',
    },
    text: {
      primary: '#e5e5e5',
      secondary: '#a3a3a3',
      disabled: 'rgba(255,255,255,0.15)',
    },
    divider: '#2a2a2a',
    action: {
      hover: '#262626',
      selected: '#303030',
      disabledBackground: '#2a2a2a',
    },
    success: { main: '#4ade80' },
    warning: { main: '#fbbf24' },
    error: { main: '#f87171' },
    info: { main: '#818cf8' },
  },
});

// Compact Light theme — compact sizing with light palette
export const compactLightTheme = createTheme({
  ...compactBaseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#6366f1',
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a1a',
      secondary: '#525252',
    },
    divider: '#e5e5e5',
    action: {
      hover: 'rgba(0, 0, 0, 0.04)',
      selected: 'rgba(0, 0, 0, 0.08)',
    },
    success: { main: '#22c55e' },
    warning: { main: '#f59e0b' },
    error: { main: '#ef4444' },
    info: { main: '#6366f1' },
  },
});

// ---------------------------------------------------------------------------
// Modern themes — Roboto font (same as Auto), mock-ui color palette
// ---------------------------------------------------------------------------

// Modern Dark theme — Auto font family with mock-ui dark palette
export const modernDarkTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'dark',
    primary: {
      main: '#818cf8',
      light: '#a5b4fc',
      dark: '#6366f1',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#f48fb1',
      light: '#ffc1e3',
      dark: '#bf5f82',
      contrastText: '#000000',
    },
    background: {
      default: '#0f0f0f',
      paper: '#171717',
    },
    text: {
      primary: '#e5e5e5',
      secondary: '#a3a3a3',
      disabled: 'rgba(255,255,255,0.15)',
    },
    divider: '#2a2a2a',
    action: {
      hover: '#262626',
      selected: '#303030',
      disabledBackground: '#2a2a2a',
    },
    success: { main: '#4ade80' },
    warning: { main: '#fbbf24' },
    error: { main: '#f87171' },
    info: { main: '#818cf8' },
  },
});

// Modern Light theme — Auto font family with clean light palette and indigo accent
export const modernLightTheme = createTheme({
  ...baseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#6366f1',
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
      contrastText: '#ffffff',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
    },
    text: {
      primary: '#171717',
      secondary: '#525252',
    },
    divider: '#e5e5e5',
    action: {
      hover: 'rgba(0, 0, 0, 0.04)',
      selected: 'rgba(0, 0, 0, 0.08)',
    },
    success: { main: '#22c55e' },
    warning: { main: '#f59e0b' },
    error: { main: '#ef4444' },
    info: { main: '#6366f1' },
  },
});

// Theme mapping
export const THEME_MAP: Record<ThemeOption, Theme> = {
  auto: lightTheme, // Will be dynamically set based on system preference
  light: lightTheme,
  dark: darkTheme,
  blue: blueTheme,
  'high-contrast': highContrastTheme,
  'compact-light': compactLightTheme,
  'compact-dark': compactDarkTheme,
  'modern-dark': modernDarkTheme,
  'modern-light': modernLightTheme,
};

// Get theme by name
export const getTheme = (themeName: ThemeOption, prefersDark?: boolean): Theme => {
  if (themeName === 'auto') {
    return prefersDark ? darkTheme : lightTheme;
  }
  return THEME_MAP[themeName];
};

// Default theme
export const DEFAULT_THEME: ThemeOption = 'auto';
