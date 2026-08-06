// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from 'react-oidc-context';
import { ThemeManager } from './components/ThemeManager/ThemeManager';
import { getOidcConfig } from './config/oidc';
import App from './App';
import './styles/main.css';

/**
 * Callback handler to clean URL after OAuth login.
 * Removes authorization code and state parameters from URL.
 */
const onSigninCallback = (): void => {
  // Remove the code and state from the URL after successful login
  window.history.replaceState({}, document.title, window.location.pathname);
};

const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);

// ThemeManager owns MUI + CSS theme state. AuthProvider sits above App so
// useAuth() hooks work throughout the tree. Notification and Accessibility
// providers live inside App (see App.tsx).
root.render(
  <ThemeManager>
    <AuthProvider {...getOidcConfig()} onSigninCallback={onSigninCallback}>
      <App />
    </AuthProvider>
  </ThemeManager>
);

