// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SettingsModal smoke test — verifies the dialog renders when open.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import SettingsModal from '../../../../src/components/SettingsModal/SettingsModal';
import { configurationService } from '../../../../src/services/ConfigurationService';

describe('SettingsModal', () => {
  it('renders a dialog when isOpen is true', () => {
    render(
      <SettingsModal
        isOpen={true}
        onClose={jest.fn()}
        onSave={jest.fn()}
        onReset={jest.fn()}
        currentSettings={configurationService.getSettings()}
      />,
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders nothing when isOpen is false', () => {
    render(
      <SettingsModal
        isOpen={false}
        onClose={jest.fn()}
        onSave={jest.fn()}
        onReset={jest.fn()}
        currentSettings={configurationService.getSettings()}
      />,
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
