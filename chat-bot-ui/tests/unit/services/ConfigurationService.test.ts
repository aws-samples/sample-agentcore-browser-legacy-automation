// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ConfigurationService smoke test — singleton behaviour, localStorage
 * persistence, section-level reset, and subscribe/publish.
 */

import { ConfigurationService, configurationService } from '../../../src/services/ConfigurationService';

describe('ConfigurationService', () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset the singleton to defaults between tests.
    configurationService.resetSettings();
  });

  it('exports a singleton via getInstance() and the `configurationService` helper', () => {
    expect(ConfigurationService.getInstance()).toBe(configurationService);
  });

  it('returns default settings covering application/theme/notifications/oauth', () => {
    const settings = configurationService.getSettings();
    expect(settings.application.websocketReconnectInterval).toBe(3000);
    expect(settings.application.maxReconnectAttempts).toBe(5);
    expect(settings.theme.selectedTheme).toBeDefined();
    expect(settings.notifications.liveConversation).toBe(true);
    expect(settings.oauth).toBeDefined();
    expect(settings.oauth!.scope).toBe('openid profile email');
  });

  it('persists updated settings to localStorage under the chat-bot-ui key', () => {
    configurationService.updateSettings({
      application: {
        websocketReconnectInterval: 7000,
        maxReconnectAttempts: 9,
      },
    });

    const stored = localStorage.getItem('chat-bot-ui-settings');
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.application.websocketReconnectInterval).toBe(7000);
    expect(parsed.application.maxReconnectAttempts).toBe(9);
  });

  it('notifies subscribers when settings change', () => {
    const listener = jest.fn();
    const unsubscribe = configurationService.subscribe(listener);

    configurationService.updateSettings({
      application: { websocketReconnectInterval: 1234, maxReconnectAttempts: 2 },
    });
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    configurationService.updateSettings({
      application: { websocketReconnectInterval: 5678, maxReconnectAttempts: 3 },
    });
    expect(listener).toHaveBeenCalledTimes(1); // unchanged after unsubscribe
  });

  it('resetSettings(section) resets only the chosen section', () => {
    configurationService.updateSettings({
      application: { websocketReconnectInterval: 9999, maxReconnectAttempts: 1 },
      notifications: { liveConversation: false, settingsModal: false, historyView: false },
    });

    configurationService.resetSettings('application');
    const s = configurationService.getSettings();
    expect(s.application.websocketReconnectInterval).toBe(3000);
    expect(s.notifications.liveConversation).toBe(false); // unchanged
  });
});
