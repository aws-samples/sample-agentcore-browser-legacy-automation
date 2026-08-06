// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AgentContent — Content-only component for the browser agent.
 *
 * Single-profile blog reference implementation. Owns the
 * `useBrowserChatSession` hook, manages WebSocket lifecycle against the
 * OIDC token, reports session-list changes up to `AppShell` via
 * `onSessionsChange`, and exposes session-management callbacks via a
 * `React.forwardRef` imperative handle.
 *
 * The render tree wires `ChatView` (message list + input) and `LiveView` (DCV
 * panel) side-by-side, toggled by a local `liveViewOpen` flag. The LiveView
 * panel collapses to zero width when closed — ChatView expands to fill the row.
 *
 * @module components/AgentContent
 */

import React, { useEffect, useImperativeHandle } from 'react';
import { Box } from '@mui/material';
import { useAuth } from 'react-oidc-context';

import { useBrowserChatSession } from '../../hooks/useBrowserChatSession';
import type { SessionInfo } from '../../types/browser.types';

import { ChatView } from '../ChatView/ChatView';
import { LiveView } from '../LiveView/LiveView';
import './AgentContent.css';

export interface AgentContentProps {
  onSessionsChange?: (
    sessions: SessionInfo[],
    activeSessionId: string | null,
  ) => void;
}

export interface AgentContentHandle {
  handleNewChat: () => void;
  handleResumeSession: (sessionId: string) => void;
  handleDeleteSession: (sessionId: string) => void;
}

export const AgentContent = React.forwardRef<
  AgentContentHandle,
  AgentContentProps
>(({ onSessionsChange }, ref) => {
  const auth = useAuth();

  const {
    connectionState,
    sessionId,
    messages,
    sessions,
    isStreaming,
    browserSession,
    sendMessage,
    stopBrowser,
    requestLiveViewUrl,
    newSession,
    resumeSession,
    deleteSession,
    connect,
  } = useBrowserChatSession();

  const [liveViewOpen, setLiveViewOpen] = React.useState<boolean>(false);

  // ------------------------------------------------------------------
  // Expose session-management callbacks to AppShell via imperative handle
  // ------------------------------------------------------------------
  useImperativeHandle(
    ref,
    () => ({
      handleNewChat: () => newSession(),
      handleResumeSession: (sid: string) => resumeSession(sid),
      handleDeleteSession: (sid: string) => deleteSession(sid),
    }),
    [newSession, resumeSession, deleteSession],
  );

  // ------------------------------------------------------------------
  // Report session changes to AppShell for the merged SessionList
  // ------------------------------------------------------------------
  useEffect(() => {
    onSessionsChange?.(sessions, sessionId);
  }, [sessions, sessionId, onSessionsChange]);

  // ------------------------------------------------------------------
  // Connect once the OIDC access token is available (Req 12.3).
  // The hook's internal unmount cleanup handles disconnect on logout.
  // ------------------------------------------------------------------
  useEffect(() => {
    const token = auth.user?.access_token;
    if (!token) return;
    connect(token, 'browser');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.user?.access_token]);

  // ------------------------------------------------------------------
  // Token-unavailable placeholder — do not call connect until the OIDC
  // token resolves.
  // ------------------------------------------------------------------
  if (!auth.user?.access_token) {
    return (
      <Box
        className="agent-content agent-content--loading"
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          width: '100%',
          color: 'text.secondary',
          fontSize: '0.9rem',
        }}
        role="status"
        aria-live="polite"
        data-testid="agent-content-loading"
      >
        Connecting…
      </Box>
    );
  }

  return (
    <Box
      className="agent-content"
      sx={{
        display: 'flex',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
      }}
      data-testid="agent-content"
    >
      <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <ChatView
          messages={messages}
          browserSession={browserSession}
          connectionState={connectionState}
          isStreaming={isStreaming}
          onSendMessage={sendMessage}
          onStopBrowser={stopBrowser}
          onToggleLiveView={() => setLiveViewOpen((v) => !v)}
        />
      </Box>
      {liveViewOpen && (
        <Box
          sx={{
            flex: '0 0 40%',
            maxWidth: '540px',
            minWidth: '320px',
            borderLeft: 1,
            borderColor: 'divider',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <LiveView
            open={liveViewOpen}
            onClose={() => setLiveViewOpen(false)}
            liveViewUrl={browserSession.liveViewUrl}
            onRequestRefresh={requestLiveViewUrl}
          />
        </Box>
      )}
    </Box>
  );
});

AgentContent.displayName = 'AgentContent';

export default AgentContent;
