// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * AppShell — Single layout shell that composes sidebar, top bar, and content
 * area for the browser-agent blog reference implementation.
 *
 * Renders `<AgentContent />` as the single content view. There is no profile
 * router, voice pathway, or agent drawer. The sidebar shows the session list
 * sourced from the agent content's onSessionsChange callback.
 *
 * @module components/AppShell
 */

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { Box, IconButton, Typography, useMediaQuery, useTheme } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

import { useAccessibility } from '../../contexts/AccessibilityContext';
import {
  useKeyboardNavigation,
  getDefaultKeyboardShortcuts,
} from '../../hooks/useKeyboardNavigation';
import { configurationService } from '../../services/ConfigurationService';
import { notificationService } from '../../services/NotificationService';
import type { ConfigurationSettings } from '../../types/settings.types';
import type { SessionInfo } from '../../types/browser.types';

import { SidebarHeader } from '../SidebarHeader/SidebarHeader';
import { SessionList } from '../SessionList/SessionList';
import { SidebarFooter } from '../SidebarFooter/SidebarFooter';
import { TopBar } from '../TopBar/TopBar';
import {
  AgentContent,
  AgentContentHandle,
} from '../AgentContent/AgentContent';
import SettingsModal from '../SettingsModal/SettingsModal';
import { HelpModal } from '../HelpModal';
import { KeyboardShortcuts } from '../KeyboardShortcuts/KeyboardShortcuts';

import './AppShell.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SIDEBAR_WIDTH = 280;
const SIDEBAR_COLLAPSED_WIDTH = 60;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const AppShell: React.FC = () => {
  // -----------------------------------------------------------------------
  // Context hooks
  // -----------------------------------------------------------------------
  const { announceToScreenReader } = useAccessibility();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // -----------------------------------------------------------------------
  // Local state
  // -----------------------------------------------------------------------
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [currentSettings, setCurrentSettings] = useState<ConfigurationSettings>(
    configurationService.getSettings(),
  );

  // Session data received via callback from AgentContent
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Ref for imperative agent content actions
  const agentContentRef = useRef<AgentContentHandle | null>(null);

  // -----------------------------------------------------------------------
  // Sidebar toggle
  // -----------------------------------------------------------------------
  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      announceToScreenReader(next ? 'Sidebar collapsed' : 'Sidebar expanded');
      return next;
    });
  }, [announceToScreenReader]);

  // -----------------------------------------------------------------------
  // Session callback
  // -----------------------------------------------------------------------
  const handleSessionsChange = useCallback(
    (nextSessions: SessionInfo[], activeId: string | null) => {
      setSessions(nextSessions);
      setActiveSessionId(activeId);
    },
    [],
  );

  // -----------------------------------------------------------------------
  // New Chat dispatch
  // -----------------------------------------------------------------------
  const handleNewChat = useCallback(() => {
    agentContentRef.current?.handleNewChat();
    announceToScreenReader('New chat started');
  }, [announceToScreenReader]);

  const handleResumeSession = useCallback((sessionId: string) => {
    agentContentRef.current?.handleResumeSession?.(sessionId);
  }, []);

  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      agentContentRef.current?.handleDeleteSession?.(sessionId);
      announceToScreenReader('Session deleted');
    },
    [announceToScreenReader],
  );

  // -----------------------------------------------------------------------
  // Settings handlers
  // -----------------------------------------------------------------------
  const handleOpenSettings = useCallback(() => {
    setCurrentSettings(configurationService.getSettings());
    setShowSettings(true);
  }, []);

  const handleCloseSettings = useCallback(() => {
    setShowSettings(false);
  }, []);

  const handleSaveSettings = useCallback(
    (newSettings: ConfigurationSettings) => {
      configurationService.updateSettings(newSettings);
      setCurrentSettings(newSettings);
      setShowSettings(false);
      notificationService.success('Settings saved successfully', 'settingsModal');
      announceToScreenReader('Settings saved successfully');
    },
    [announceToScreenReader],
  );

  const handleResetSettings = useCallback(
    (section?: keyof ConfigurationSettings) => {
      configurationService.resetSettings(section);
      setCurrentSettings(configurationService.getSettings());
      const message = section
        ? `${section} settings reset to defaults`
        : 'All settings reset to defaults';
      notificationService.info(message, 'settingsModal');
      announceToScreenReader(message);
    },
    [announceToScreenReader],
  );

  useEffect(() => {
    const unsubscribe = configurationService.subscribe((newSettings) => {
      setCurrentSettings(newSettings);
    });
    return unsubscribe;
  }, []);

  // -----------------------------------------------------------------------
  // Help modal handler
  // -----------------------------------------------------------------------
  const handleOpenHelp = useCallback(() => {
    setShowHelpModal(true);
  }, []);

  // -----------------------------------------------------------------------
  // Keyboard navigation
  // -----------------------------------------------------------------------
  const shortcuts = useMemo(
    () =>
      getDefaultKeyboardShortcuts(
        handleToggleSidebar,
        handleNewChat,
        handleOpenSettings,
        () => setShowKeyboardShortcuts(true),
      ),
    [handleToggleSidebar, handleNewChat, handleOpenSettings],
  );

  useKeyboardNavigation({
    shortcuts,
    enabled: true,
  });

  // -----------------------------------------------------------------------
  // Mobile overlay
  // -----------------------------------------------------------------------
  const [showOverlay, setShowOverlay] = useState(false);

  useEffect(() => {
    if (isMobile) {
      setShowOverlay(!sidebarCollapsed);
    } else {
      setShowOverlay(false);
    }
  }, [sidebarCollapsed, isMobile]);

  const handleOverlayClick = useCallback(() => {
    if (isMobile) {
      setSidebarCollapsed(true);
      announceToScreenReader('Sidebar closed');
    }
  }, [isMobile, announceToScreenReader]);

  // Auto-collapse on mobile
  useEffect(() => {
    const handleResize = () => {
      const currentIsMobile = window.innerWidth <= theme.breakpoints.values.md;
      if (currentIsMobile && !sidebarCollapsed) {
        setSidebarCollapsed(true);
        announceToScreenReader('Sidebar automatically collapsed for mobile view');
      }
    };

    let resizeTimeout: ReturnType<typeof setTimeout>;
    const debouncedResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(handleResize, 150);
    };

    handleResize();
    window.addEventListener('resize', debouncedResize);
    return () => {
      window.removeEventListener('resize', debouncedResize);
      clearTimeout(resizeTimeout);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Escape key closes sidebar on mobile
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobile && !sidebarCollapsed) {
        setSidebarCollapsed(true);
      }
    };
    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [isMobile, sidebarCollapsed]);

  // -----------------------------------------------------------------------
  // Content margin calculation
  // -----------------------------------------------------------------------
  const mainContentMargin = isMobile
    ? '0px'
    : sidebarCollapsed
      ? `${SIDEBAR_COLLAPSED_WIDTH}px`
      : `${SIDEBAR_WIDTH}px`;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <Box
      className="app-shell"
      sx={{ display: 'flex', height: '100vh', width: '100%', overflow: 'hidden', position: 'relative' }}
    >
      {/* Skip to main content */}
      <Box
        component="a"
        href="#main-content"
        className="skip-to-main"
        sx={{
          position: 'absolute',
          top: '-40px',
          left: '6px',
          backgroundColor: 'primary.main',
          color: 'primary.contrastText',
          padding: '8px 16px',
          textDecoration: 'none',
          borderRadius: '4px',
          fontSize: '14px',
          fontWeight: 600,
          zIndex: 9999,
          transition: 'top 0.2s ease',
          '&:focus': { top: '6px' },
        }}
      >
        Skip to main content
      </Box>

      {/* Mobile overlay */}
      {isMobile && (
        <Box
          className={`sidebar-overlay ${showOverlay ? 'visible' : ''}`}
          onClick={handleOverlayClick}
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1250,
            opacity: showOverlay ? 1 : 0,
            visibility: showOverlay ? 'visible' : 'hidden',
            transition: 'opacity 0.3s ease, visibility 0.3s ease',
          }}
        />
      )}

      {/* Sidebar */}
      <Box
        className={`app-sidebar ${sidebarCollapsed ? 'collapsed' : 'expanded'}`}
        role="navigation"
        aria-label="Sidebar"
        sx={{
          position: 'fixed',
          left: 0,
          top: 0,
          height: '100vh',
          width: sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH,
          minWidth: sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH,
          maxWidth: sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH,
          backgroundColor: 'background.paper',
          borderRight: 1,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          zIndex: 1300,
          transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          willChange: 'width, transform',
        }}
      >
        <SidebarHeader
          isCollapsed={sidebarCollapsed}
          onToggleSidebar={handleToggleSidebar}
          onNewChat={handleNewChat}
        />

        {/* New Chat button */}
        <Box
          sx={{
            px: sidebarCollapsed ? 0.5 : 2,
            py: 1,
            display: 'flex',
            justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <IconButton
            onClick={handleNewChat}
            aria-label="New Chat"
            sx={{
              borderRadius: sidebarCollapsed ? '50%' : 'var(--shape-borderRadius, 10px)',
              width: sidebarCollapsed ? 40 : '100%',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
              gap: 1,
              px: sidebarCollapsed ? 0 : 2,
              py: 1,
              border: sidebarCollapsed ? 'none' : '1px dashed',
              borderColor: 'divider',
              color: 'text.secondary',
              '&:hover': { backgroundColor: 'action.hover', borderColor: 'text.secondary', color: 'text.primary' },
            }}
          >
            <AddIcon fontSize="small" />
            {!sidebarCollapsed && (
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                New Chat
              </Typography>
            )}
          </IconButton>
        </Box>

        {/* Session list */}
        <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          <SessionList
            sessions={sessions}
            activeSessionId={activeSessionId}
            onResumeSession={handleResumeSession}
            onDeleteSession={handleDeleteSession}
            isCollapsed={sidebarCollapsed}
          />
        </Box>

        {/* Sidebar footer */}
        <SidebarFooter
          isCollapsed={sidebarCollapsed}
          onOpenSettings={handleOpenSettings}
          onOpenHelp={handleOpenHelp}
        />
      </Box>

      {/* Main area */}
      <Box
        className="app-main"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          marginLeft: mainContentMargin,
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative',
          zIndex: 1,
          willChange: 'margin-left',
        }}
      >
        <TopBar />
        <Box
          id="main-content"
          component="main"
          role="main"
          sx={{ flex: 1, overflow: 'hidden', display: 'flex' }}
        >
          <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <AgentContent
              ref={agentContentRef}
              onSessionsChange={handleSessionsChange}
            />
          </Box>
        </Box>
      </Box>

      {/* Modals */}
      <SettingsModal
        isOpen={showSettings}
        onClose={handleCloseSettings}
        onSave={handleSaveSettings}
        onReset={handleResetSettings}
        currentSettings={currentSettings}
      />
      <HelpModal open={showHelpModal} onClose={() => setShowHelpModal(false)} />
      <KeyboardShortcuts
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
      />

      {/* Screen reader live region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id="screen-reader-announcements"
      />
    </Box>
  );
};

export default AppShell;
