// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SessionList — Sidebar session history list.
 *
 * Displays all sessions for the browser agent in a single scrollable list.
 * The currently active session is highlighted. Sessions are stored in SPA
 * memory only (React state) — no localStorage. Cleared on page refresh.
 *
 * @module components/SessionList
 */

import React, { useState } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Fade,
} from '@mui/material';
import {
  Chat as ChatIcon,
  DeleteOutline as DeleteIcon,
} from '@mui/icons-material';
import type { SessionInfo } from '../../types/browser.types';

export interface SessionListProps {
  /** All sessions (SPA memory only). */
  sessions: SessionInfo[];
  /** The currently active session ID. */
  activeSessionId: string | null;
  /** Called when a session is clicked — triggers RESUME_SESSION. */
  onResumeSession: (sessionId: string) => void;
  /** Called when a session delete is confirmed. */
  onDeleteSession?: (sessionId: string) => void;
  /** Whether the sidebar is collapsed (hides text, shows icons only). */
  isCollapsed?: boolean;
}

/** Format an ISO timestamp for display. */
function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

/** Classify a date into a display group label. */
export function getDateGroupLabel(iso: string): string {
  const date = new Date(iso);
  if (isNaN(date.getTime())) return 'UNKNOWN';
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.floor(
    (startOfToday.getTime() - startOfDate.getTime()) / (1000 * 60 * 60 * 24),
  );

  if (diffDays === 0) return 'TODAY';
  if (diffDays === 1) return 'YESTERDAY';
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/** Group sorted sessions under date headers. */
export function groupSessionsByDate(sessions: SessionInfo[]): Map<string, SessionInfo[]> {
  const groups = new Map<string, SessionInfo[]>();
  for (const session of sessions) {
    const label = getDateGroupLabel(session.created_at);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(session);
  }
  return groups;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  activeSessionId,
  onResumeSession,
  onDeleteSession,
  isCollapsed = false,
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);

  if (sessions.length === 0) {
    return isCollapsed ? null : (
      <Box sx={{ px: 2, py: 1.5 }}>
        <Typography variant="caption" color="text.secondary">
          No sessions yet
        </Typography>
      </Box>
    );
  }

  return (
    <List
      dense
      disablePadding
      data-testid="session-list"
      role="list"
      aria-label="Session history"
      sx={{
        overflowY: 'auto',
        flex: 1,
        '&::-webkit-scrollbar': { width: '4px' },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'action.disabled',
          borderRadius: '2px',
        },
      }}
    >
      {(() => {
        const groups = groupSessionsByDate(sessions);
        const elements: React.ReactNode[] = [];
        groups.forEach((groupSessions, label) => {
          if (!isCollapsed) {
            elements.push(
              <Typography
                key={`group-${label}`}
                variant="caption"
                color="text.secondary"
                data-testid={`date-group-${label}`}
                sx={{
                  display: 'block',
                  textTransform: 'uppercase',
                  px: 2,
                  pt: 1.5,
                  pb: 0.5,
                }}
              >
                {label}
              </Typography>,
            );
          }
          groupSessions.forEach((session) => {
            const isActive = session.session_id === activeSessionId;
            const isHovered = hoveredId === session.session_id;
            const isConfirming = confirmingDeleteId === session.session_id;

            const handleClick = () => {
              if (isActive || isConfirming) return;
              onResumeSession(session.session_id);
            };

            const handleDeleteClick = (e: React.MouseEvent) => {
              e.stopPropagation();
              setConfirmingDeleteId(session.session_id);
            };

            const handleConfirmDelete = (e: React.MouseEvent) => {
              e.stopPropagation();
              setConfirmingDeleteId(null);
              onDeleteSession?.(session.session_id);
            };

            const handleCancelDelete = (e: React.MouseEvent) => {
              e.stopPropagation();
              setConfirmingDeleteId(null);
            };

            elements.push(
              <ListItem
                key={session.session_id}
                disablePadding
                onMouseEnter={() => setHoveredId(session.session_id)}
                onMouseLeave={() => {
                  setHoveredId(null);
                  if (isConfirming) setConfirmingDeleteId(null);
                }}
              >
                {isConfirming ? (
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      minHeight: 44,
                      px: 2,
                      mx: 0.5,
                      mb: 0.25,
                      borderRadius: 1,
                      bgcolor: 'error.dark',
                      color: 'error.contrastText',
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 500 }}>
                      Delete?
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Typography
                        variant="caption"
                        onClick={handleConfirmDelete}
                        sx={{
                          cursor: 'pointer',
                          fontWeight: 700,
                          textDecoration: 'underline',
                          '&:hover': { opacity: 0.8 },
                        }}
                      >
                        Yes
                      </Typography>
                      <Typography variant="caption" sx={{ mx: 0.25 }}>
                        /
                      </Typography>
                      <Typography
                        variant="caption"
                        onClick={handleCancelDelete}
                        sx={{
                          cursor: 'pointer',
                          opacity: 0.8,
                          '&:hover': { opacity: 1 },
                        }}
                      >
                        No
                      </Typography>
                    </Box>
                  </Box>
                ) : (
                  <ListItemButton
                    selected={isActive}
                    onClick={handleClick}
                    aria-current={isActive ? 'true' : undefined}
                    aria-label={`Session: ${session.title}`}
                    data-testid={`session-item-${session.session_id}`}
                    sx={{
                      minHeight: 44,
                      justifyContent: isCollapsed ? 'center' : 'initial',
                      px: isCollapsed ? 1 : 2,
                      borderRadius: 1,
                      mx: 0.5,
                      mb: 0.25,
                      '&.Mui-selected': {
                        backgroundColor: 'action.selected',
                        '&:hover': { backgroundColor: 'action.selected' },
                      },
                    }}
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: 0,
                        mr: isCollapsed ? 0 : 1.5,
                        justifyContent: 'center',
                        color: isActive ? 'primary.main' : 'text.secondary',
                      }}
                    >
                      <ChatIcon fontSize="small" />
                    </ListItemIcon>

                    {!isCollapsed && (
                      <>
                        <ListItemText
                          primary={
                            <Typography
                              variant="body2"
                              noWrap
                              sx={{
                                fontWeight: isActive ? 600 : 400,
                                color: isActive ? 'text.primary' : 'text.secondary',
                              }}
                            >
                              {session.title}
                            </Typography>
                          }
                          secondary={
                            <Typography variant="caption" color="text.disabled" noWrap>
                              {formatTimestamp(session.created_at)}
                            </Typography>
                          }
                          sx={{ my: 0 }}
                        />
                        {onDeleteSession && (
                          <Fade in={isHovered}>
                            <IconButton
                              size="small"
                              onClick={handleDeleteClick}
                              aria-label={`Delete session: ${session.title}`}
                              sx={{
                                ml: 0.5,
                                flexShrink: 0,
                                color: 'text.disabled',
                                '&:hover': { color: 'error.main' },
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Fade>
                        )}
                      </>
                    )}
                  </ListItemButton>
                )}
              </ListItem>,
            );
          });
        });
        return elements;
      })()}
    </List>
  );
};
