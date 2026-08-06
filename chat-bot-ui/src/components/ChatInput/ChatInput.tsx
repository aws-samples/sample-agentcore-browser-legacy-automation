// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * ChatInput — Text input area with send button and auto-resize.
 *
 * Uses a plain textarea (not MUI TextField) for precise alignment control.
 * Enter sends the message; Shift+Enter inserts a newline.
 *
 * @module components/ChatInput
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Box, IconButton } from '@mui/material';
import { ArrowUpward as SendIcon } from '@mui/icons-material';

export interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  /** Optional placeholder text override. */
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Message the browser agent…',
}) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
    }
  }, [value]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <Box
      data-testid="chat-input"
      sx={{ px: { xs: 2, sm: 3, md: 4 }, pb: 2, pt: 1.5, bgcolor: 'background.default' }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '8px',
          padding: '6px 6px 6px 16px',
          bgcolor: 'background.paper',
          borderRadius: '20px',
          border: 1,
          borderColor: 'divider',
          transition: 'border-color 0.15s ease',
          '&:focus-within': { borderColor: 'primary.main' },
        }}
      >
        <Box
          component="textarea"
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          value={value}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-label="Chat message input"
          data-testid="chat-input-field"
          sx={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: 'text.primary',
            fontFamily: 'inherit',
            fontSize: '0.9rem',
            lineHeight: 1.5,
            resize: 'none',
            outline: 'none',
            maxHeight: '150px',
            padding: '6px 0',
            '&::placeholder': { color: 'text.secondary', opacity: 0.6 },
            '&:disabled': { opacity: 0.5 },
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          data-testid="chat-send-button"
          sx={{
            bgcolor: 'primary.main',
            color: '#fff',
            width: 32,
            height: 32,
            flexShrink: 0,
            opacity: value.trim() && !disabled ? 1 : 0.4,
            transition: 'opacity 0.15s ease, background-color 0.15s ease',
            '&:hover': { bgcolor: 'primary.dark' },
            '&.Mui-disabled': { bgcolor: 'primary.main', color: '#fff', opacity: 0.4 },
          }}
        >
          <SendIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Box>
    </Box>
  );
};
