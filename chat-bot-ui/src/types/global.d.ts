// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Global TypeScript declarations for webpack DefinePlugin variables.
 *
 * These constants are injected at compile time via webpack.config.js DefinePlugin.
 * They provide configuration for WebSocket connections and OIDC authentication.
 */

// WebSocket URL - full ALB URL for AgentCore deployment
// Example: wss://gateway-alb-xxx.us-west-2.elb.amazonaws.com
declare const __WEBSOCKET_URL__: string;

// Development mode flag - true when NODE_ENV !== 'production'
declare const __DEV_MODE__: boolean;

// OIDC configuration (IdP-agnostic — supports Auth0, Okta, Cognito, Entra ID)
declare const __OIDC_AUTHORITY__: string;
declare const __OIDC_CLIENT_ID__: string;
declare const __OIDC_AUDIENCE__: string;
declare const __OIDC_SCOPE__: string;

// Public path for OIDC redirect URIs (matches webpack output.publicPath).
// '/' for the single-profile reference implementation.
declare const __PUBLIC_PATH__: string;
