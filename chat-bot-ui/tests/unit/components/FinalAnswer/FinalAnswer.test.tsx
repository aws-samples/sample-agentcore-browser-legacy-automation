// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * FinalAnswer smoke test — renders content and hides when empty.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { FinalAnswer } from '../../../../src/components/FinalAnswer/FinalAnswer';
import type { BrowserChatMessage } from '../../../../src/types/browser.types';

const base = (overrides: Partial<BrowserChatMessage> = {}): BrowserChatMessage => ({
  id: 'a1',
  role: 'assistant',
  content: '',
  timestamp: new Date().toISOString(),
  ...overrides,
});

describe('FinalAnswer', () => {
  it('renders content when present', () => {
    const { container } = render(<FinalAnswer message={base({ content: 'final' })} />);
    expect(container.textContent).toMatch(/final/);
  });

  it('renders nothing when content is empty and not an error', () => {
    const { container } = render(<FinalAnswer message={base({ content: '' })} />);
    expect(container.textContent).toBe('');
  });
});
