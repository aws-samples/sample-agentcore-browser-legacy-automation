// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatMessage — Renders a single user or assistant chat message.
 *
 * User messages are right-aligned bubbles. Assistant messages are left-aligned
 * with an avatar, Markdown rendering via react-markdown + remark-gfm,
 * and ObservabilityPanel + SourceCards as siblings below the content.
 *
 * @module components/ChatMessage
 */

import React from 'react';
import { Avatar, Box, Paper, Typography } from '@mui/material';
import { SmartToy as AssistantIcon } from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage as ChatMessageType } from '../../types/browser.types';
import { StreamingCursor } from '../StreamingCursor/StreamingCursor';

export interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <Box
        data-testid={`chat-message-${message.id}`}
        sx={{
          display: 'flex',
          justifyContent: 'flex-end',
          mb: 1.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            px: 2,
            py: 1,
            maxWidth: '75%',
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            borderRadius: 2,
          }}
        >
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>
        </Paper>
      </Box>
    );
  }

  // Assistant message
  return (
    <Box
      data-testid={`chat-message-${message.id}`}
      sx={{ display: 'flex', gap: 1.5, mb: 1.5, alignItems: 'flex-start' }}
    >
      <Avatar
        sx={{
          width: 28,
          height: 28,
          bgcolor: 'action.selected',
          mt: 0.5,
        }}
        aria-hidden="true"
      >
        <AssistantIcon sx={{ fontSize: 16, color: 'primary.main' }} />
      </Avatar>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        {/* Markdown content — compact font sizing to match mock-ui (0.85rem base) */}
        <Box
          sx={{
            fontSize: '0.85rem',
            lineHeight: 1.65,
            '& p': { m: 0, mb: 1 },
            '& p:last-child': { mb: 0 },
            '& h1': { fontSize: '1.1rem', fontWeight: 600, mt: 1, mb: 0.5 },
            '& h2': { fontSize: '1rem', fontWeight: 600, mt: 1, mb: 0.5 },
            '& h3': { fontSize: '0.925rem', fontWeight: 600, mt: 0.5, mb: 0.5 },
            '& h4': { fontSize: '0.875rem', fontWeight: 600, mt: 0.5, mb: 0.5 },
            '& pre': {
              bgcolor: 'action.hover',
              p: 1.5,
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.8rem',
            },
            '& code': {
              fontFamily: 'monospace',
              fontSize: '0.8rem',
            },
            '& table': {
              borderCollapse: 'collapse',
              width: '100%',
              mb: 1,
              fontSize: '0.8rem',
            },
            '& th, & td': {
              border: '1px solid',
              borderColor: 'divider',
              px: 1,
              py: 0.5,
              textAlign: 'left',
            },
            '& a': {
              color: 'primary.main',
              textDecoration: 'underline',
            },
            '& ul, & ol': {
              pl: 2.5,
              mb: 1,
            },
            '& li': {
              mb: 0.25,
            },
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
          {message.isStreaming && <StreamingCursor />}
        </Box>
      </Box>
    </Box>
  );
};
