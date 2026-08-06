// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * LiveView smoke test — renders placeholder when no URL, iframe when URL set.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { LiveView } from '../../../../src/components/LiveView/LiveView';

describe('LiveView', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <LiveView open={false} onClose={jest.fn()} liveViewUrl={null} onRequestRefresh={jest.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders a waiting placeholder when open but no URL is set', () => {
    render(
      <LiveView open={true} onClose={jest.fn()} liveViewUrl={null} onRequestRefresh={jest.fn()} />,
    );
    expect(screen.getByText(/waiting for live view/i)).toBeInTheDocument();
  });

  it('renders an iframe when a URL is present', () => {
    const { container } = render(
      <LiveView
        open={true}
        onClose={jest.fn()}
        liveViewUrl="https://live.example.com"
        onRequestRefresh={jest.fn()}
      />,
    );
    const iframe = container.querySelector('iframe');
    expect(iframe).not.toBeNull();
    expect(iframe?.getAttribute('src')).toBe('https://live.example.com');
  });
});
