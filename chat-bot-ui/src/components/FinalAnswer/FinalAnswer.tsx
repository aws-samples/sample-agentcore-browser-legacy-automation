// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * FinalAnswer — Renders the synthesized STREAM answer as a distinct,
 * privileged card visually separated from the reasoning trace.
 *
 * The browser-agent turn produces two outputs for the UI: the action
 * trace (reasoning + actions + screenshots) and the final natural-
 * language answer streamed via STREAM frames. Mixing both in a single
 * assistant bubble is what made the prior UX unreadable; this card
 * gives the final answer its own home.
 *
 * Markdown rendering is delegated to the existing common `ChatMessage`
 * component so links, lists, inline code, and formatting stay consistent
 * with the rest of the chat UI. We forward the message unchanged but
 * omit the browser-specific artifact fields (screenshots / actions /
 * hitlPrompt) — those are already being rendered inside the trace.
 *
 * Empty state: when `content` is empty (turn still streaming, or a pure
 * handoff with no final answer), the component renders nothing. The
 * trace carries the visible state on its own.
 *
 * @module components/browser/FinalAnswer
 */

import React from 'react';
import type { BrowserChatMessage, ChatMessage as ChatMessageType } from '../../types/browser.types';
import { ChatMessage } from '../ChatMessage/ChatMessage';
import './FinalAnswer.css';

export interface FinalAnswerProps {
  /** The assistant message to render as the final answer. */
  message: BrowserChatMessage;
}

export const FinalAnswer: React.FC<FinalAnswerProps> = ({ message }) => {
  // If there's no content and no error to surface, render nothing — the
  // trace alone is enough.
  const hasContent = typeof message.content === 'string' && message.content.length > 0;
  if (!hasContent && !message.isError) {
    return null;
  }

  // Strip the browser-specific artifact fields so the shared ChatMessage
  // component only has to care about text + error state. We keep the
  // original id/role/timestamp/agentMetadata so downstream styling (e.g.
  // streaming cursor, error badge) works as designed.
  const cleaned: ChatMessageType = {
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
    isStreaming: message.isStreaming,
    isError: message.isError,
    recoverable: message.recoverable,
    agentMetadata: message.agentMetadata,
  };

  return (
    <section
      className="browser-final-answer"
      data-testid="browser-final-answer"
      aria-label="Browser agent final answer"
    >
      <div className="browser-final-answer-label">Final answer</div>
      <div className="browser-final-answer-body">
        <ChatMessage message={cleaned} />
      </div>
    </section>
  );
};

export default FinalAnswer;
