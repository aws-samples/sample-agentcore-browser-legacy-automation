// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { useMediaQuery, GlobalStyles } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import { ThemeOption } from '../../types/ui.types';
import { getTheme, DEFAULT_THEME } from '../../theme/themeConfig';
import { configurationService } from '../../services/ConfigurationService';

// Theme context
interface ThemeContextType {
  currentTheme: ThemeOption;
  setTheme: (theme: ThemeOption) => void;
  availableThemes: ThemeOption[];
  systemPrefersDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Custom hook to use theme context
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeManager');
  }
  return context;
};

// Theme storage key
const THEME_STORAGE_KEY = 'browser-agent-ui-theme';

interface ThemeManagerProps {
  children: ReactNode;
}

export const ThemeManager: React.FC<ThemeManagerProps> = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState<ThemeOption>(DEFAULT_THEME);
  const systemPrefersDark = useMediaQuery('(prefers-color-scheme: dark)');

  // Available theme options
  const availableThemes: ThemeOption[] = ['auto', 'light', 'dark', 'blue', 'high-contrast'];

  // Load theme from ConfigurationService on mount and subscribe to changes
  useEffect(() => {
    // Get initial theme from configuration service
    const settings = configurationService.getSettings();
    setCurrentTheme(settings.theme.selectedTheme);

    // Subscribe to configuration changes
    const unsubscribe = configurationService.subscribe((newSettings) => {
      setCurrentTheme(newSettings.theme.selectedTheme);
    });

    return unsubscribe;
  }, []);

  // Set theme function with ConfigurationService integration
  const setTheme = (theme: ThemeOption): void => {
    setCurrentTheme(theme);

    // Update the configuration service instead of localStorage directly
    configurationService.updateSettings({
      theme: {
        ...configurationService.getSettings().theme,
        selectedTheme: theme
      }
    });
  };

  // Get the actual Material-UI theme based on current selection and system preference
  const muiTheme = getTheme(currentTheme, systemPrefersDark);

  const contextValue: ThemeContextType = {
    currentTheme,
    setTheme,
    availableThemes,
    systemPrefersDark,
  };

  // Create CSS custom properties from the theme
  const themeVariables = {
    ':root': {
      '--mui-palette-primary-main': muiTheme.palette.primary.main,
      '--mui-palette-primary-light': muiTheme.palette.primary.light,
      '--mui-palette-primary-dark': muiTheme.palette.primary.dark,
      '--mui-palette-primary-contrastText': muiTheme.palette.primary.contrastText,
      '--mui-palette-secondary-main': muiTheme.palette.secondary.main,
      '--mui-palette-secondary-light': muiTheme.palette.secondary.light,
      '--mui-palette-secondary-dark': muiTheme.palette.secondary.dark,
      '--mui-palette-secondary-contrastText': muiTheme.palette.secondary.contrastText,
      '--mui-palette-background-default': muiTheme.palette.background.default,
      '--mui-palette-background-paper': muiTheme.palette.background.paper,
      '--mui-palette-text-primary': muiTheme.palette.text.primary,
      '--mui-palette-text-secondary': muiTheme.palette.text.secondary,
      '--mui-palette-divider': muiTheme.palette.divider,
      '--mui-palette-action-hover': muiTheme.palette.action.hover,
      '--mui-palette-action-selected': muiTheme.palette.action.selected,
      '--mui-palette-error-main': muiTheme.palette.error.main,
      '--mui-palette-warning-main': muiTheme.palette.warning.main,
      '--mui-palette-info-main': muiTheme.palette.info.main,
      '--mui-palette-success-main': muiTheme.palette.success.main,
      '--mui-typography-fontFamily': muiTheme.typography.fontFamily,
    }
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      <ThemeProvider theme={muiTheme}>
        <CssBaseline />
        <GlobalStyles styles={themeVariables} />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};