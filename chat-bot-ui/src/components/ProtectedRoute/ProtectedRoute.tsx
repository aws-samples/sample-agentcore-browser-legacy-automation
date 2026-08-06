// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Protected Route Component
 *
 * Wraps routes that require authentication.
 * Uses useAuth hook from react-oidc-context to check authentication state
 * and redirect unauthenticated users to the login page.
 *
 * @module components/ProtectedRoute
 */

import React, { useEffect, useRef } from 'react';
import { useAuth } from 'react-oidc-context';
import { useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

/**
 * Global flag to indicate logout is in progress.
 * This prevents ProtectedRoute from triggering redirect during logout.
 * Set to true before logout redirect, automatically resets on page load.
 */
export let isLoggingOut = false;

/**
 * Set the logging out flag. Call this before initiating logout redirect.
 */
export const setLoggingOut = (value: boolean): void => {
  isLoggingOut = value;
};

/**
 * Props for the ProtectedRoute component.
 */
export interface ProtectedRouteProps {
  /** Child components to render when authenticated */
  children: React.ReactNode;
}

/**
 * ProtectedRoute component that guards routes requiring authentication.
 *
 * Features:
 * - Displays loading indicator while checking authentication state
 * - Redirects to /login page when not authenticated (user chooses when to login)
 * - Renders children only when user is authenticated
 * - Prevents multiple redirect calls using ref tracking
 * - Respects global isLoggingOut flag to prevent redirect during logout
 *
 * @param props - Component props containing children to render
 * @returns Loading indicator, null (during redirect), or children (when authenticated)
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const auth = useAuth();
  const navigate = useNavigate();
  // Track if we've already initiated a redirect to prevent multiple calls
  const hasInitiatedRedirect = useRef(false);

  // Handle redirect to login page when not authenticated (Requirement 5.4)
  useEffect(() => {
    // CRITICAL: Don't redirect if logout is in progress
    if (isLoggingOut) {
      console.log('🔒 PROTECTED_ROUTE: Logout in progress, skipping redirect');
      return;
    }

    // Only redirect if:
    // - Not authenticated
    // - Not currently loading
    // - No active navigator (not in the middle of a redirect)
    // - Haven't already initiated a redirect
    if (
      !auth.isAuthenticated &&
      !auth.isLoading &&
      !auth.activeNavigator &&
      !hasInitiatedRedirect.current
    ) {
      hasInitiatedRedirect.current = true;
      // Redirect to login page instead of directly to IdP
      // This gives users control over when to initiate OAuth flow
      // and allows for future multiple login options (social, enterprise, etc.)
      console.log('🔒 PROTECTED_ROUTE: Not authenticated, redirecting to /login');
      navigate('/login', { replace: true });
    }
  }, [auth, auth.isAuthenticated, auth.isLoading, auth.activeNavigator, navigate]);

  // Reset redirect flag when authentication state changes
  useEffect(() => {
    if (auth.isAuthenticated) {
      hasInitiatedRedirect.current = false;
    }
  }, [auth.isAuthenticated]);

  // Show loading state while checking authentication (Requirement 5.3)
  if (auth.isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          backgroundColor: 'background.default',
        }}
        role="main"
        aria-label="Loading"
        aria-busy="true"
      >
        <CircularProgress
          size={48}
          aria-label="Loading authentication"
          sx={{ mb: 2 }}
        />
        <Typography
          variant="body1"
          color="text.secondary"
          aria-live="polite"
        >
          Loading...
        </Typography>
      </Box>
    );
  }

  // If not authenticated, render nothing while redirect happens
  // (Requirement 5.4 - redirect to /login is called in useEffect)
  if (!auth.isAuthenticated) {
    return null;
  }

  // Render children when authenticated (Requirement 5.5)
  return <>{children}</>;
};

export default ProtectedRoute;
