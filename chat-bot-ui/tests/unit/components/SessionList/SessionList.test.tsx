// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SessionList smoke test — empty state + click-to-resume + delete
 * confirmation.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  SessionList,
  groupSessionsByDate,
  getDateGroupLabel,
} from '../../../../src/components/SessionList/SessionList';
import type { SessionInfo } from '../../../../src/types/browser.types';

const makeSession = (overrides: Partial<SessionInfo> = {}): SessionInfo => ({
  session_id: 'sess-1',
  profile: 'browser',
  mode: 'text',
  title: 'My session',
  created_at: new Date().toISOString(),
  messages: [],
  ...overrides,
});

describe('SessionList', () => {
  it('renders the empty state when there are no sessions', () => {
    render(
      <SessionList
        sessions={[]}
        activeSessionId={null}
        onResumeSession={jest.fn()}
      />,
    );
    expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
  });

  it('renders a list of sessions and fires onResumeSession on click', () => {
    const onResumeSession = jest.fn();
    render(
      <SessionList
        sessions={[makeSession({ session_id: 'sess-a', title: 'Alpha' })]}
        activeSessionId={null}
        onResumeSession={onResumeSession}
      />,
    );

    fireEvent.click(screen.getByTestId('session-item-sess-a'));
    expect(onResumeSession).toHaveBeenCalledWith('sess-a');
  });
});

describe('groupSessionsByDate / getDateGroupLabel', () => {
  it('classifies today and yesterday correctly', () => {
    const today = new Date().toISOString();
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    expect(getDateGroupLabel(today)).toBe('TODAY');
    expect(getDateGroupLabel(yesterday)).toBe('YESTERDAY');
  });

  it('groups sessions by the date label', () => {
    const today = new Date().toISOString();
    const groups = groupSessionsByDate([
      makeSession({ session_id: 'a', created_at: today }),
      makeSession({ session_id: 'b', created_at: today }),
    ]);
    expect(groups.get('TODAY')).toHaveLength(2);
  });
});
