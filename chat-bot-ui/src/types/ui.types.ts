// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * UI Types — shared across the browser-agent blog UI.
 */

// Main Content Area Types — only "conversation" survives in the single-profile blueprint
export type MainContentView = 'conversation';

// Theme Management Types
export type ThemeOption =
  | 'auto'
  | 'light'
  | 'dark'
  | 'blue'
  | 'high-contrast'
  | 'compact-dark'
  | 'compact-light'
  | 'modern-dark'
  | 'modern-light';

export interface ThemeConfig {
  name: ThemeOption;
  displayName: string;
  description: string;
}

export interface ThemeManagerProps {
  currentTheme: ThemeOption;
  onThemeChange: (theme: ThemeOption) => void;
}

// UI State Management Types
export interface UIState {
  sidebarCollapsed: boolean;
  currentTheme: ThemeOption;
  activeSession?: string;
  currentView: MainContentView;
  settingsModalOpen: boolean;
}

// Sidebar Footer Types
export interface SidebarFooterProps {
  isCollapsed: boolean;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
}
