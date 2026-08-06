// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Login Component
 *
 * Displays login UI for the Browser Agent.
 * Uses useAuth hook from react-oidc-context for OAuth2/OIDC authentication.
 *
 * @module components/Login
 */

import React, { useEffect, useCallback } from 'react';
import { useAuth } from 'react-oidc-context';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  CircularProgress,
  Typography,
  Alert,
  Paper,
} from '@mui/material';
import { Login as LoginIcon } from '@mui/icons-material';
import './Login.css';

/**
 * Login component that handles OAuth2/OIDC authentication flow.
 *
 * Features:
 * - Displays product branding
 * - "Sign In" button that initiates OAuth redirect
 * - Shows loading indicator during authentication check
 * - Displays error messages when authentication fails
 * - Automatically redirects to main app when authenticated
 * - Full accessibility support with ARIA labels and keyboard navigation
 */
export const Login: React.FC = () => {
  const auth = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (auth.isAuthenticated) {
      navigate('/');
    }
  }, [auth.isAuthenticated, navigate]);

  const handleLogin = useCallback((): void => {
    auth.signinRedirect();
  }, [auth]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent): void => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleLogin();
      }
    },
    [handleLogin]
  );

  if (auth.isLoading) {
    return (
      <Box
        className="login-container"
        role="main"
        aria-label="Loading authentication"
        aria-busy="true"
      >
        <Paper
          elevation={3}
          className="login-card"
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            p: 4,
          }}
        >
          <CircularProgress
            size={48}
            aria-label="Checking authentication status"
            sx={{ mb: 2 }}
          />
          <Typography variant="body1" color="text.secondary" aria-live="polite">
            Checking authentication...
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box className="login-container" role="main" aria-label="Login page">
      <Paper elevation={3} className="login-card" sx={{ p: 4, maxWidth: 440 }}>
        {/* Product Branding */}
        <Box sx={{ mb: 3, textAlign: 'center' }}>
          <Typography
            variant="h4"
            component="h1"
            className="login-title"
            sx={{ fontWeight: 600, mb: 0.5 }}
          >
            Browser Agent
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            AI-Powered Web Automation
          </Typography>
        </Box>

        {/* Welcome */}
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
            Welcome
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Sign in to give the agent a web task in plain language.
          </Typography>
        </Box>

        {/* Error Display */}
        {auth.error && (
          <Alert severity="error" sx={{ mb: 3 }} role="alert" aria-live="assertive">
            <Typography variant="body2">
              {auth.error.message || 'Authentication failed. Please try again.'}
            </Typography>
          </Alert>
        )}

        {/* Sign In Button */}
        <Button
          variant="contained"
          color="primary"
          size="large"
          fullWidth
          onClick={handleLogin}
          onKeyDown={handleKeyDown}
          startIcon={<LoginIcon />}
          aria-label="Sign in with your organization account"
          sx={{ py: 1.5, fontSize: '1rem', fontWeight: 500 }}
        >
          Sign In
        </Button>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', textAlign: 'center', mt: 3 }}
        >
          You will be redirected to your organization&apos;s login page
        </Typography>
      </Paper>
    </Box>
  );
};

export default Login;
