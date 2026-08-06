// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SidebarHeader — Sidebar header component.
 *
 * Displays a fixed "Chat" label with a chat icon and a fold/expand control.
 * Voice-specific pathways have been removed for the single-profile blog
 * reference implementation.
 *
 * @module components/SidebarHeader
 */

import React from 'react';
import { Box, Typography, IconButton, Tooltip } from '@mui/material';
import { Chat, MenuOpen, Menu, Add as AddIcon } from '@mui/icons-material';

export interface SidebarHeaderProps {
  isCollapsed: boolean;
  onToggleSidebar: () => void;
  /** Called when the "New Chat" button is clicked. */
  onNewChat?: () => void;
}

export const SidebarHeader: React.FC<SidebarHeaderProps> = ({
  isCollapsed,
  onToggleSidebar,
  onNewChat,
}) => {
  return (
    <Box
      onClick={onToggleSidebar}
      role="button"
      tabIndex={0}
      aria-label="Toggle sidebar"
      aria-pressed={!isCollapsed}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggleSidebar();
        }
      }}
      sx={{
        display: 'flex',
        alignItems: 'center',
        padding: isCollapsed ? '12px 8px' : '8px 12px',
        cursor: 'pointer',
        borderRadius: '8px',
        transition:
          'background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1), padding 0.3s cubic-bezier(0.4, 0, 0.2, 1), gap 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        gap: isCollapsed ? 0 : '12px',
        minHeight: '48px',
        justifyContent: isCollapsed ? 'center' : 'flex-start',
        overflow: 'hidden',
        '&:hover': { backgroundColor: 'action.hover' },
        '&:focus-visible': {
          outline: '2px solid',
          outlineColor: 'primary.main',
          outlineOffset: '2px',
        },
      }}
      data-testid="sidebar-header"
    >
      {isCollapsed ? (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Chat fontSize="small" aria-hidden="true" sx={{ color: 'primary.main' }} />
        </Box>
      ) : (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
            <Chat fontSize="small" aria-hidden="true" sx={{ color: 'primary.main' }} />
          </Box>

          <Typography
            variant="body2"
            fontWeight={600}
            noWrap
            sx={{ flex: 1, minWidth: 0 }}
          >
            Chat
          </Typography>

          {onNewChat && (
            <Tooltip title="New Chat" placement="bottom">
              <IconButton
                size="small"
                aria-label="New Chat"
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  onNewChat();
                }}
                sx={{ flexShrink: 0 }}
                data-testid="new-chat-button"
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}

          <IconButton
            size="small"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              onToggleSidebar();
            }}
            sx={{ flexShrink: 0 }}
            data-testid="sidebar-fold-button"
          >
            {isCollapsed ? <Menu fontSize="small" /> : <MenuOpen fontSize="small" />}
          </IconButton>
        </>
      )}
    </Box>
  );
};
