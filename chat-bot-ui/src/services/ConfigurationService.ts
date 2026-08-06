// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ConfigurationService — Centralized settings management for the blog UI.
 *
 * Provides default values, localStorage persistence, and a subscribe/publish
 * API for UI components to react to settings changes.
 */

import { ConfigurationSettings } from '../types/settings.types';
import { DEFAULT_THEME } from '../theme/themeConfig';

// Webpack DefinePlugin variables for OAuth defaults
declare const __OIDC_AUTHORITY__: string;
declare const __OIDC_CLIENT_ID__: string;
declare const __OIDC_AUDIENCE__: string;
declare const __OIDC_SCOPE__: string;

const STORAGE_KEY = 'chat-bot-ui-settings';

export class ConfigurationService {
  private static instance: ConfigurationService;
  private settings: ConfigurationSettings;
  private listeners: Array<(settings: ConfigurationSettings) => void> = [];

  private constructor() {
    this.settings = this.getDefaultSettings();
    this.loadFromStorage();
  }

  public static getInstance(): ConfigurationService {
    if (!ConfigurationService.instance) {
      ConfigurationService.instance = new ConfigurationService();
    }
    return ConfigurationService.instance;
  }

  private getDefaultSettings(): ConfigurationSettings {
    return {
      application: {
        websocketReconnectInterval: 3000,
        maxReconnectAttempts: 5,
      },
      theme: {
        selectedTheme: DEFAULT_THEME,
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        borderRadius: 8,
        spacing: 8,
        scrollbarWidth: '8px',
        scrollbarBorderRadius: '4px',
      },
      notifications: {
        liveConversation: true,
        settingsModal: true,
        historyView: true,
      },
      oauth: {
        authority: __OIDC_AUTHORITY__ || undefined,
        clientId: __OIDC_CLIENT_ID__ || undefined,
        authorityType: 'auth0',
        audience: __OIDC_AUDIENCE__ || undefined,
        scope: __OIDC_SCOPE__ || 'openid profile email',
      },
    };
  }

  public getSettings(): ConfigurationSettings {
    return { ...this.settings };
  }

  public getDefaults(): ConfigurationSettings {
    return this.getDefaultSettings();
  }

  public updateSettings(newSettings: Partial<ConfigurationSettings>): void {
    this.settings = { ...this.settings, ...newSettings };
    this.saveToStorage();
    this.notifyListeners();
  }

  public resetSettings(section?: keyof ConfigurationSettings): void {
    const defaults = this.getDefaultSettings();

    if (section) {
      this.settings = {
        ...this.settings,
        [section]: defaults[section],
      };
    } else {
      this.settings = defaults;
    }

    this.saveToStorage();
    this.notifyListeners();
  }

  public subscribe(listener: (settings: ConfigurationSettings) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  private saveToStorage(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.settings));
    } catch (error) {
      console.warn('Failed to save settings to localStorage:', error);
    }
  }

  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedSettings = JSON.parse(stored);
        this.settings = { ...this.settings, ...parsedSettings };
      }
    } catch (error) {
      console.warn('Failed to load settings from localStorage:', error);
      this.settings = this.getDefaultSettings();
      this.saveToStorage();
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener(this.settings);
      } catch (error) {
        console.error('Error in settings listener:', error);
      }
    });
  }
}

export const configurationService = ConfigurationService.getInstance();
