// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * WebSocket URL builder for AgentCore connection.
 *
 * Constructs the full WebSocket URL with OIDC access token and profile ID
 * as query parameters for authenticated, profile-aware connections.
 *
 * @module utils/websocket
 */

/**
 * Build a WebSocket URL with authentication token and profile ID.
 *
 * @param token - OIDC access token for authentication
 * @param profileId - Active profile ID for routing
 * @returns Full WebSocket URL: `{__WEBSOCKET_URL__}?token={token}&profile={profileId}`
 */
export const buildWebSocketUrl = (token: string, profileId: string): string => {
  const base = __WEBSOCKET_URL__.replace(/\/+$/, '');
  return `${base}/ws?token=${encodeURIComponent(token)}&profile=${encodeURIComponent(profileId)}`;
};
