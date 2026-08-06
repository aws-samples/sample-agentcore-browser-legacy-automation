// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * App — Root component for the single-profile browser-agent chat UI.
 *
 * Providers: NotificationContext (notifications) and AccessibilityContext
 * (keyboard-nav / reduced-motion preferences). OIDC is set up at index.tsx
 * via react-oidc-context.
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { NotificationProvider } from './contexts/NotificationContext';
import { AccessibilityProvider } from './contexts/AccessibilityContext';
import { AppShell } from './components/AppShell/AppShell';
import { Login } from './components/Login/Login';
import { ProtectedRoute } from './components/ProtectedRoute/ProtectedRoute';
import { NotificationDisplay } from './components/NotificationDisplay/NotificationDisplay';

const App: React.FC = () => (
  <NotificationProvider>
    <AccessibilityProvider>
      <BrowserRouter basename={__PUBLIC_PATH__.replace(/\/$/, '')}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          />
        </Routes>
        <NotificationDisplay />
      </BrowserRouter>
    </AccessibilityProvider>
  </NotificationProvider>
);

export default App;
