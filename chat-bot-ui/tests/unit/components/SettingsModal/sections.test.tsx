// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SettingsModal sections smoke test — each section renders when given default settings.
 *
 * Each section component accepts a narrow slice of `ConfigurationSettings`
 * (not the whole object), so we pass `defaults.application`, `defaults.theme`,
 * and `defaults.oauth` respectively. The `NotificationSettingsSection` takes
 * no props — it reads preferences from `NotificationContext`.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { NotificationProvider } from '../../../../src/contexts/NotificationContext';
import { configurationService } from '../../../../src/services/ConfigurationService';
import { ApplicationSettingsSection } from '../../../../src/components/SettingsModal/sections/ApplicationSettingsSection';
import { ThemeSettingsSection } from '../../../../src/components/SettingsModal/sections/ThemeSettingsSection';
import { NotificationSettingsSection } from '../../../../src/components/SettingsModal/sections/NotificationSettingsSection';
import { OAuthSettingsSection } from '../../../../src/components/SettingsModal/sections/OAuthSettingsSection';

describe('SettingsModal sections', () => {
  const defaults = configurationService.getDefaults();
  const onChange = jest.fn();

  it('ApplicationSettingsSection renders without crashing', () => {
    expect(() =>
      render(
        <ApplicationSettingsSection settings={defaults.application} onChange={onChange} />,
      ),
    ).not.toThrow();
  });

  it('ThemeSettingsSection renders without crashing', () => {
    expect(() =>
      render(<ThemeSettingsSection settings={defaults.theme} onChange={onChange} />),
    ).not.toThrow();
  });

  it('NotificationSettingsSection renders inside NotificationProvider', () => {
    expect(() =>
      render(
        <NotificationProvider>
          <NotificationSettingsSection />
        </NotificationProvider>,
      ),
    ).not.toThrow();
  });

  it('OAuthSettingsSection renders without crashing', () => {
    expect(() =>
      render(
        <OAuthSettingsSection settings={defaults.oauth ?? {}} onChange={onChange} />,
      ),
    ).not.toThrow();
  });
});
