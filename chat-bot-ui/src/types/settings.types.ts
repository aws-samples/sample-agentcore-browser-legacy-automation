// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Settings Types - Configuration interfaces for the browser-agent blog UI.
 *
 * This project is the single-profile blog reference implementation. The voice
 * / interview settings from the source project have been removed. The modal
 * exposes: application tuning, theme, notifications, and OAuth overrides.
 */

export interface ConfigurationSettings {
  /** Core app configuration (WebSocket + reconnect tuning). */
  application: {
    websocketReconnectInterval: number;
    maxReconnectAttempts: number;
  };

  /** Theme configuration. */
  theme: {
    selectedTheme:
      | 'auto'
      | 'light'
      | 'dark'
      | 'blue'
      | 'high-contrast'
      | 'compact-dark'
      | 'compact-light'
      | 'modern-dark'
      | 'modern-light';
    fontFamily: string;
    borderRadius: number;
    spacing: number;
    scrollbarWidth: string;
    scrollbarBorderRadius: string;
  };

  /** Notification toggles. */
  notifications: {
    liveConversation: boolean;
    settingsModal: boolean;
    historyView: boolean;
  };

  /** OAuth runtime overrides. */
  oauth?: OAuthConfig;
}

/**
 * Supported Identity Provider types.
 * Each IdP has a different logout URL pattern.
 */
export type AuthorityType = 'auth0' | 'okta' | 'cognito' | 'entra' | 'standard_oidc';

/**
 * OAuth Configuration Interface — allows runtime override of OIDC settings
 * via the Settings modal.
 */
export interface OAuthConfig {
  authority?: string;
  clientId?: string;
  redirectUri?: string;
  logoutRedirectUri?: string;
  scope?: string;
  authorityType?: AuthorityType;
  audience?: string;
}

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (settings: ConfigurationSettings) => void;
  onReset: (section?: keyof ConfigurationSettings) => void;
  currentSettings: ConfigurationSettings;
}

export type SettingsSection = keyof ConfigurationSettings;

export interface SettingsSectionConfig {
  key: SettingsSection;
  title: string;
  description: string;
  icon: string;
}

export const SETTINGS_SECTIONS: SettingsSectionConfig[] = [
  {
    key: 'application',
    title: 'Application',
    description: 'Core app configuration',
    icon: 'settings_applications',
  },
  {
    key: 'theme',
    title: 'Theme',
    description: 'UI theme configuration',
    icon: 'palette',
  },
  {
    key: 'notifications',
    title: 'Notifications',
    description: 'Notification preferences and controls',
    icon: 'notifications',
  },
  {
    key: 'oauth',
    title: 'OAuth / OIDC',
    description: 'Identity Provider authentication settings',
    icon: 'security',
  },
];
