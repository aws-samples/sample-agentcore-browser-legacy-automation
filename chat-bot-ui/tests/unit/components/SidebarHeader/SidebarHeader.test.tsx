// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SidebarHeader smoke test — renders and forwards toggle clicks.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SidebarHeader } from '../../../../src/components/SidebarHeader/SidebarHeader';

describe('SidebarHeader', () => {
  it('renders the toggle button and forwards clicks', () => {
    const onToggleSidebar = jest.fn();
    render(
      <SidebarHeader
        isCollapsed={false}
        onToggleSidebar={onToggleSidebar}
        onNewChat={jest.fn()}
      />,
    );

    const toggle = screen.getByRole('button', { name: /toggle sidebar/i });
    fireEvent.click(toggle);
    expect(onToggleSidebar).toHaveBeenCalledTimes(1);
  });
});
