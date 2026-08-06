// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * SidebarFooter Component
 *
 * Persistent footer at the bottom of the sidebar with user avatar and
 * dropdown menu (Settings, Help, Sign Out).
 *
 * @module components/SidebarFooter
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Help as HelpIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useAuth } from 'react-oidc-context';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { setLoggingOut } from '../ProtectedRoute/ProtectedRoute';
import { performLogout } from '../../config/oidc';
import { SidebarFooterProps } from '../../types/ui.types';

export const SidebarFooter: React.FC<SidebarFooterProps> = ({
  isCollapsed,
  onOpenSettings,
  onOpenHelp,
}) => {
  const auth = useAuth();
  const { announceToScreenReader } = useAccessibility();
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  // Avatar initials from JWT profile (Requirement 2.3)
  const userName = auth.user?.profile?.name as string | undefined ?? '';
  const userEmail = auth.user?.profile?.email as string | undefined ?? '';
  const initials = (userName?.split(' ')[0]?.charAt(0) || '?').toUpperCase();

  /**
   * Full logout sequence using standard OIDC `signoutRedirect()`, which
   * resolves the IdP's `end_session_endpoint` via OIDC discovery. Works
   * uniformly for Amazon Cognito, Auth0, Okta, and Microsoft Entra ID.
   *
   * Order of operations:
   * 1. Set global flag so ProtectedRoute doesn't re-trigger signinRedirect.
   * 2. Stop silent renew to prevent race conditions.
   * 3. Clear OIDC storage (sessionStorage + localStorage) to ensure the
   *    redirect lands on a clean state.
   * 4. Call `removeUser()` (non-blocking — we redirect below regardless).
   * 5. Hand off to `performLogout(auth)` which invokes the discovered
   *    end-session endpoint with `post_logout_redirect_uri=<PUBLIC_PATH>login`.
   *    On failure we fall back to a local redirect so the UI never gets
   *    stuck on the app shell with stale credentials.
   */
  const handleLogout = useCallback(async () => {
    setMenuAnchor(null);
    announceToScreenReader('Signing out...');

    // 1. Set global flag to prevent ProtectedRoute from triggering signinRedirect
    setLoggingOut(true);

    // 2. Stop silent renew to prevent race conditions
    try {
      auth.stopSilentRenew();
    } catch (error) {
      console.warn('🔒 LOGOUT: Error stopping silent renew (continuing):', error);
    }

    // 3. Clear ALL OIDC storage BEFORE any async operations
    const sessionKeysToRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && (key.startsWith('oidc.') || key.includes('user:') || key.includes('auth'))) {
        sessionKeysToRemove.push(key);
      }
    }
    sessionKeysToRemove.forEach((key) => sessionStorage.removeItem(key));

    const localKeysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('oidc.') || key.includes('user:') || key.includes('auth'))) {
        localKeysToRemove.push(key);
      }
    }
    localKeysToRemove.forEach((key) => localStorage.removeItem(key));

    // 4. Clear user (non-blocking)
    auth.removeUser().catch((error) => {
      console.warn('🔒 LOGOUT: Error removing user (non-blocking):', error);
    });

    // 5. Hand off to the IdP's end-session endpoint via OIDC discovery
    try {
      await performLogout(auth);
    } catch (error) {
      console.warn('🔒 LOGOUT: signoutRedirect failed, falling back to local redirect:', error);
      window.location.href = `${window.location.origin}${__PUBLIC_PATH__}login`;
    }
  }, [auth, announceToScreenReader]);

  const handleSettingsClick = useCallback(() => {
    setMenuAnchor(null);
    onOpenSettings();
  }, [onOpenSettings]);

  const handleHelpClick = useCallback(() => {
    setMenuAnchor(null);
    onOpenHelp();
  }, [onOpenHelp]);

  const handleMenuOpen = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  }, []);

  const handleMenuClose = useCallback(() => {
    setMenuAnchor(null);
  }, []);

  return (
    <Box className="sidebar-footer" sx={{ borderTop: 1, borderColor: 'divider', px: 1.5, py: 1 }}>
      {/* User avatar area — settings accessible via avatar dropdown menu */}
      {!isCollapsed ? (
        /* Expanded: avatar circle + name + email, clickable to open menu */
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            cursor: 'pointer',
            borderRadius: 1,
            p: 0.75,
            transition: 'background-color 0.2s ease',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.04)',
            },
          }}
          onClick={handleMenuOpen}
          role="button"
          aria-label="Open user menu"
          aria-expanded={Boolean(menuAnchor)}
          aria-haspopup="true"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleMenuOpen(e as unknown as React.MouseEvent<HTMLElement>);
            }
          }}
        >
          <Avatar
            sx={{
              width: 32,
              height: 32,
              bgcolor: 'primary.main',
              fontSize: '14px',
              fontWeight: 600,
            }}
            aria-hidden="true"
          >
            {initials}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ fontSize: '14px', fontWeight: 600, color: 'text.primary' }}>
              {userName || 'Unknown User'}
            </Box>
            {userEmail && (
              <Box
                sx={{
                  fontSize: '12px',
                  color: 'text.secondary',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {userEmail}
              </Box>
            )}
          </Box>
        </Box>
      ) : (
        /* Collapsed: just the avatar IconButton, clickable to open menu */
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <IconButton
            size="small"
            onClick={handleMenuOpen}
            aria-label="Open user menu"
            aria-expanded={Boolean(menuAnchor)}
            aria-haspopup="true"
            sx={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              backgroundColor: 'primary.main',
              '&:hover': {
                backgroundColor: 'primary.dark',
              },
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: 'transparent',
                fontSize: '14px',
                fontWeight: 600,
                color: 'primary.contrastText',
              }}
            >
              {initials}
            </Avatar>
          </IconButton>
        </Box>
      )}

      {/* Avatar dropdown menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
        transformOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        role="menu"
        aria-label="User menu"
      >
        <MenuItem
          onClick={handleSettingsClick}
          role="menuitem"
          aria-label="Open settings"
        >
          <ListItemIcon aria-hidden="true">
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={handleHelpClick}
          role="menuitem"
          aria-label="Open help"
        >
          <ListItemIcon aria-hidden="true">
            <HelpIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Help</ListItemText>
        </MenuItem>
        <Divider />
        {auth.isAuthenticated && (
          <MenuItem
            onClick={handleLogout}
            role="menuitem"
            aria-label="Sign out of your account"
          >
            <ListItemIcon aria-hidden="true">
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Sign Out</ListItemText>
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
};
