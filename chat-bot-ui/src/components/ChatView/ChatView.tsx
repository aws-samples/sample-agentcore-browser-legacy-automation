// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatView — Main chat container for the browser agent profile.
 *
 * Renders the scrollable message list using the Step Card UX:
 *   - User messages appear as normal chat bubbles.
 *   - Each assistant message is split into two distinct elements:
 *       1. A collapsible ReasoningTrace bundling all step cards for
 *          that turn (reasoning + actions + screenshots + HITL).
 *       2. A FinalAnswer card carrying the STREAM output as a first-
 *          class, visually distinct element.
 *   - Above the first assistant turn the SessionIndicator renders when
 *     a browser session is active.
 *   - The ChatInput at the bottom switches placeholder when a HITL
 *     prompt is pending, and is disabled while streaming or after a
 *     fatal (unrecoverable) error.
 *
 * Auto-scroll, input-disable logic, and HITL live-region announcements
 * all mirror the previous implementation exactly — this refactor only
 * changes the visual structure, not the interaction model.
 *
 * @module components/browser/ChatView
 */

import React, { useEffect, useRef } from 'react';
import { Box } from '@mui/material';
import type {
  BrowserChatMessage,
  BrowserSessionState,
  ChatMessage as ChatMessageType,
} from '../../types/browser.types';
import { ChatMessage } from '../ChatMessage/ChatMessage';
import { ChatInput } from '../ChatInput/ChatInput';
import { SessionIndicator } from '../SessionIndicator/SessionIndicator';
import { ReasoningTrace } from '../ReasoningTrace/ReasoningTrace';
import { FinalAnswer } from '../FinalAnswer/FinalAnswer';
import { groupMessageIntoSteps } from '../../utils/browserSteps';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import './ChatView.css';

export interface ChatViewProps {
  messages: BrowserChatMessage[];
  browserSession: BrowserSessionState;
  connectionState: string;
  isStreaming: boolean;
  onSendMessage: (content: string) => void;
  onStopBrowser: () => void;
  onToggleLiveView: () => void;
}

/**
 * Render a single assistant turn as a ReasoningTrace + FinalAnswer pair.
 * Only this assistant turn's artifacts appear — no mixing across turns.
 */
const AssistantTurn: React.FC<{
  message: BrowserChatMessage;
  isStreaming: boolean;
}> = ({ message, isStreaming }) => {
  const grouping = groupMessageIntoSteps(message);

  // Auto-collapse the trace when:
  //   - the final answer has landed (turn completed streaming), OR
  //   - an error was emitted on this turn, OR
  //   - a HITL prompt is engaged on this turn.
  // We still render the trace; we just leave it collapsed so the user
  // has to opt in to expand it.
  // Trace default is already false — no special logic needed since the
  // helper returns false unconditionally (see isTraceDefaultExpanded).

  return (
    <>
      {(grouping.steps.length > 0 || grouping.trailingReasoning.length > 0) && (
        <ReasoningTrace
          steps={grouping.steps}
          trailingReasoning={grouping.trailingReasoning}
          isStreaming={isStreaming && message.isStreaming === true}
          defaultExpanded={false}
        />
      )}
      <FinalAnswer message={message} />
    </>
  );
};

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  browserSession,
  connectionState: _connectionState,
  isStreaming,
  onSendMessage,
  onStopBrowser,
  onToggleLiveView,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { announceToScreenReader } = useAccessibility();
  const lastAnnouncedPromptIdRef = useRef<string | null>(null);

  // Auto-scroll to bottom on new messages, streaming tokens, or HITL / session
  // transitions. Mirrors the pattern used by TextChatView.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, isStreaming, browserSession.pendingHitl, browserSession.isActive]);

  // Announce new HITL prompts exactly once via the shared live region.
  useEffect(() => {
    const pending = browserSession.pendingHitl;
    if (pending && pending.promptId !== lastAnnouncedPromptIdRef.current) {
      lastAnnouncedPromptIdRef.current = pending.promptId;
      announceToScreenReader(`New prompt: ${pending.question}`, 'polite');
    } else if (!pending) {
      lastAnnouncedPromptIdRef.current = null;
    }
  }, [browserSession.pendingHitl, announceToScreenReader]);

  // Input-disable logic:
  //   1. An unrecoverable ERROR blocks the input until a NEW_SESSION resets
  //      `messages` — the session is fatally broken, there's nothing useful
  //      the user can send.
  //   2. Otherwise, the streaming gate disables the input — UNLESS a HITL
  //      prompt is pending. During a HITL pause the backend is actively
  //      waiting for the user's response and `isStreaming` is still true
  //      (ORCHESTRATION_END won't fire until Claude resumes), so we MUST
  //      override the streaming gate. Without this override the chat would
  //      deadlock: backend waits for the user, UI won't let the user send.
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const blockedByFatalError =
    !!lastMessage &&
    lastMessage.isError === true &&
    lastMessage.recoverable === false;
  const isAwaitingHitlResponse = browserSession.pendingHitl !== null;
  const inputDisabled =
    blockedByFatalError || (isStreaming && !isAwaitingHitlResponse);

  const inputPlaceholder = browserSession.pendingHitl
    ? 'Respond to the browser agent…'
    : 'Message the browser agent…';

  return (
    <Box
      data-testid="browser-chat-view"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        bgcolor: 'background.default',
      }}
    >
      {browserSession.isActive && (
        <Box sx={{ px: { xs: 2, sm: 3, md: 4 }, pt: 1.5 }}>
          <SessionIndicator
            stepCounter={browserSession.stepCounter}
            onStop={onStopBrowser}
            onToggleLiveView={onToggleLiveView}
          />
        </Box>
      )}

      <Box
        ref={scrollRef}
        role="log"
        aria-live="polite"
        data-testid="browser-message-list"
        sx={{
          flex: 1,
          overflowY: 'auto',
          px: { xs: 2, sm: 3, md: 4 },
          py: 2,
        }}
      >
        {messages.length === 0 ? (
          <div className="browser-empty-state" data-testid="browser-empty-state">
            Ask the browser agent to navigate or interact with a website.
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="browser-message-wrapper">
              {msg.role === 'user' ? (
                <ChatMessage message={msg as ChatMessageType} />
              ) : (
                <AssistantTurn message={msg} isStreaming={isStreaming} />
              )}
            </div>
          ))
        )}
      </Box>

      <ChatInput
        onSend={onSendMessage}
        disabled={inputDisabled}
        placeholder={inputPlaceholder}
      />
    </Box>
  );
};

export default ChatView;
