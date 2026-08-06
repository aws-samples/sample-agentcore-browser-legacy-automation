// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Notification System Types
 *
 * Comprehensive notification system with granular control settings
 */

export type NotificationSeverity = 'success' | 'info' | 'warning' | 'error';

export interface NotificationMessage {
  id: string;
  message: string;
  severity: NotificationSeverity;
  componentSource: string;
  timestamp: number;
  autoHideDuration?: number;
}

export interface NotificationPreferences {
  summaryView: boolean;
  liveConversation: boolean;
  voiceStatus: boolean;
  settingsModal: boolean;
  historyView: boolean;
  sessionManagement: boolean;
  textChat: boolean;
  agentDrawer: boolean;
}

export interface NotificationComponent {
  name: string;
  displayName: string;
  description: string;
  defaultEnabled: boolean;
}

export interface NotificationServiceConfig {
  maxNotifications: number;
  defaultAutoHideDuration: number;
  enabledByDefault: boolean;
}

export interface NotificationContextValue {
  notifications: NotificationMessage[];
  preferences: NotificationPreferences;
  showNotification: (
    message: string,
    severity: NotificationSeverity,
    componentSource: string,
    autoHideDuration?: number
  ) => void;
  dismissNotification: (id: string) => void;
  clearAllNotifications: () => void;
  updatePreferences: (preferences: Partial<NotificationPreferences>) => void;
  isComponentEnabled: (componentSource: string) => boolean;
  getRegisteredComponents: () => NotificationComponent[];
}

// Default notification preferences (all enabled by default)
export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  summaryView: true,
  liveConversation: true,
  voiceStatus: true,
  settingsModal: true,
  historyView: true,
  sessionManagement: true,
  textChat: true,
  agentDrawer: true,
};

// Registered notification components
export const NOTIFICATION_COMPONENTS: NotificationComponent[] = [
  {
    name: 'summaryView',
    displayName: 'Summary Generation',
    description: 'Summary generation and regeneration notifications',
    defaultEnabled: true,
  },
  {
    name: 'liveConversation',
    displayName: 'Live Conversation',
    description: 'Agent response notifications when not in the conversation view',
    defaultEnabled: true,
  },
  {
    name: 'voiceStatus',
    displayName: 'Voice System',
    description: 'Voice system error notifications',
    defaultEnabled: true,
  },
  {
    name: 'settingsModal',
    displayName: 'Settings',
    description: 'Settings save/reset and notification control notifications',
    defaultEnabled: true,
  },
  {
    name: 'historyView',
    displayName: 'History Actions',
    description: 'Session history cleared notifications',
    defaultEnabled: true,
  },
  {
    name: 'sessionManagement',
    displayName: 'Session Management',
    description: 'Session start, resume, pause, and error notifications',
    defaultEnabled: true,
  },
  {
    name: 'textChat',
    displayName: 'Text Chat',
    description: 'Text chat message and session notifications',
    defaultEnabled: true,
  },
  {
    name: 'agentDrawer',
    displayName: 'Agent Drawer',
    description: 'Agent selection and configuration notifications',
    defaultEnabled: true,
  },
];

// Default service configuration
export const DEFAULT_NOTIFICATION_CONFIG: NotificationServiceConfig = {
  maxNotifications: 5,
  defaultAutoHideDuration: 4000,
  enabledByDefault: true,
};