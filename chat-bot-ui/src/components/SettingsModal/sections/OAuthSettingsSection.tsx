// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * OAuth Settings Section - Identity Provider Configuration
 *
 * Allows runtime configuration of OAuth/OIDC settings with smart field visibility.
 * Values override webpack defaults when set.
 * Fields are shown/hidden based on the selected Authority Type.
 *
 * Display Logic:
 * - Shows webpack build-time defaults as current values
 * - Users can override defaults via Settings modal
 * - Empty overrides fall back to webpack defaults
 *
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  TextField,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  Alert,
  Button,
  Snackbar,
  Divider,
  Collapse
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Clear as ClearIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import type { OAuthConfig, AuthorityType } from '../../../types/settings.types';

// Webpack DefinePlugin variables (build-time defaults)
declare const __OIDC_AUTHORITY__: string;
declare const __OIDC_CLIENT_ID__: string;
declare const __OIDC_AUDIENCE__: string;
declare const __OIDC_SCOPE__: string;

/**
 * Authority Type options with IdP-specific metadata for smart field visibility.
 * Each IdP has different requirements for audience/resource parameters.
 *
 */
interface AuthorityTypeOption {
  value: AuthorityType;
  label: string;
  description: string;
  authorityPlaceholder: string;
  authorityHelperText: string;
  showAudience: boolean;
  audienceRequired: boolean;
  audienceHelperText: string;
  audienceHiddenReason: string;
}

const AUTHORITY_TYPE_OPTIONS: AuthorityTypeOption[] = [
  {
    value: 'auth0',
    label: 'Auth0',
    description: 'Auth0 Identity Platform',
    authorityPlaceholder: 'https://dev-xxxxx.auth0.com',
    authorityHelperText: 'Your Auth0 tenant domain URL',
    showAudience: true,
    audienceRequired: true,
    audienceHelperText: 'Required for Auth0 to return JWT access tokens instead of opaque tokens',
    audienceHiddenReason: ''
  },
  {
    value: 'okta',
    label: 'Okta',
    description: 'Okta Identity Cloud',
    authorityPlaceholder: 'https://dev-xxxxx.okta.com',
    authorityHelperText: 'Your Okta org URL (audience is implicit in Authorization Server URL)',
    showAudience: false,
    audienceRequired: false,
    audienceHelperText: '',
    audienceHiddenReason: 'Audience is implicit in the Authorization Server URL (e.g., /oauth2/default).'
  },
  {
    value: 'cognito',
    label: 'Amazon Cognito',
    description: 'AWS Cognito User Pools',
    authorityPlaceholder: 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxx',
    authorityHelperText: 'Your Cognito User Pool URL (audience is handled via scopes)',
    showAudience: false,
    audienceRequired: false,
    audienceHelperText: '',
    audienceHiddenReason: 'Use Resource Server identifiers in OAuth scopes instead (e.g., api://resource-server/scope).'
  },
  {
    value: 'entra',
    label: 'Microsoft Entra ID',
    description: 'Azure Active Directory (Azure AD)',
    authorityPlaceholder: 'https://login.microsoftonline.com/{tenant-id}',
    authorityHelperText: 'Your Entra ID tenant URL (audience is handled via scopes)',
    showAudience: false,
    audienceRequired: false,
    audienceHelperText: '',
    audienceHiddenReason: 'Use scope format: api://{app-id}/.default'
  },
  {
    value: 'standard_oidc',
    label: 'Standard OIDC',
    description: 'Generic OIDC-compliant provider',
    authorityPlaceholder: 'https://your-oidc-provider.com',
    authorityHelperText: 'Your OIDC provider URL',
    showAudience: true,
    audienceRequired: false,
    audienceHelperText: 'Optional - RFC 8707 resource parameter for OIDC providers that support it',
    audienceHiddenReason: ''
  }
];

interface OAuthSettingsSectionProps {
  settings: OAuthConfig;
  onChange: (settings: OAuthConfig) => void;
}

export const OAuthSettingsSection: React.FC<OAuthSettingsSectionProps> = ({
  settings,
  onChange
}) => {
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [showRefreshNotice, setShowRefreshNotice] = useState(false);

  /**
   * Get effective values (user override or webpack default).
   * This ensures we always display the actual values being used.
   */
  const effectiveValues = useMemo(() => ({
    authority: settings.authority || __OIDC_AUTHORITY__ || '',
    clientId: settings.clientId || __OIDC_CLIENT_ID__ || '',
    authorityType: settings.authorityType || 'auth0',
    audience: settings.audience || __OIDC_AUDIENCE__ || '',
    redirectUri: settings.redirectUri || `${window.location.origin}/callback`,
    logoutRedirectUri: settings.logoutRedirectUri || `${window.location.origin}/login`,
    scope: settings.scope || 'openid profile email'
  }), [settings]);

  /**
   * Get current authority type configuration with IdP-specific metadata.
   */
  const currentAuthorityType = useMemo((): AuthorityTypeOption => {
    const type = effectiveValues.authorityType;
    return AUTHORITY_TYPE_OPTIONS.find(o => o.value === type) || AUTHORITY_TYPE_OPTIONS[0];
  }, [effectiveValues.authorityType]);

  const handleChange = useCallback((field: keyof OAuthConfig, value: string) => {
    onChange({
      ...settings,
      [field]: value || undefined // Remove empty strings
    });
    // Show refresh notice when settings change
    setShowRefreshNotice(true);
  }, [settings, onChange]);

  /**
   * Handle Authority Type change with smart audience clearing.
   * When switching to an IdP that doesn't use audience, clear the audience value.
   */
  const handleAuthorityTypeChange = useCallback((newType: AuthorityType) => {
    const typeConfig = AUTHORITY_TYPE_OPTIONS.find(o => o.value === newType);
    const newSettings: OAuthConfig = {
      ...settings,
      authorityType: newType,
    };

    // Clear audience if the new IdP doesn't use it
    if (typeConfig && !typeConfig.showAudience && settings.audience) {
      newSettings.audience = undefined;
    }

    onChange(newSettings);
    setShowRefreshNotice(true);
  }, [settings, onChange]);

  /**
   * Clear all OAuth overrides and reset to webpack defaults.
   */
  const handleClearOverrides = useCallback(() => {
    // Clear all OAuth settings to use webpack defaults
    onChange({});
    setShowSuccessMessage(true);
    setShowRefreshNotice(true);
  }, [onChange]);

  /**
   * Check if any overrides are set
   */
  const hasOverrides = Boolean(
    settings.authority ||
    settings.clientId ||
    settings.redirectUri ||
    settings.logoutRedirectUri ||
    settings.scope ||
    settings.authorityType ||
    settings.audience
  );

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure OAuth/OIDC settings for authentication. The displayed values show your current active configuration (webpack defaults or your overrides). Changes require a page refresh to take effect.
      </Typography>

      {/* Refresh Required Notice */}
      {showRefreshNotice && (
        <Alert
          severity="warning"
          sx={{ mb: 3 }}
          icon={<RefreshIcon />}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => window.location.reload()}
            >
              Refresh Now
            </Button>
          }
        >
          <Typography variant="body2">
            <strong>Page refresh required.</strong> OAuth settings changes will take effect after refreshing the page.
          </Typography>
        </Alert>
      )}

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 3 }}>
        Changes to OAuth settings require a page refresh to take effect. Use the &quot;Clear Overrides&quot; button to reset to webpack defaults.
      </Alert>

      <Grid container spacing={3}>
        {/* Authority Type Selection */}
        <Grid item xs={12}>
          <FormControl fullWidth>
            <InputLabel>Identity Provider Type</InputLabel>
            <Select
              value={effectiveValues.authorityType}
              onChange={(e) => handleAuthorityTypeChange(e.target.value as AuthorityType)}
              label="Identity Provider Type"
            >
              {AUTHORITY_TYPE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              {currentAuthorityType.description}
            </FormHelperText>
          </FormControl>
        </Grid>

        {/* Authority URL */}
        <Grid item xs={12}>
          <TextField
            label="Authority (IdP URL)"
            value={effectiveValues.authority}
            onChange={(e) => handleChange('authority', e.target.value)}
            fullWidth
            placeholder={currentAuthorityType.authorityPlaceholder}
            helperText={currentAuthorityType.authorityHelperText}
          />
        </Grid>

        {/* Client ID */}
        <Grid item xs={12}>
          <TextField
            label="Client ID"
            value={effectiveValues.clientId}
            onChange={(e) => handleChange('clientId', e.target.value)}
            fullWidth
            placeholder="your-spa-client-id"
            helperText="OAuth2 SPA client ID from your Identity Provider"
          />
        </Grid>

        {/* API Audience - Conditionally shown based on Authority Type */}
        <Grid item xs={12}>
          <Collapse in={currentAuthorityType.showAudience} timeout={300}>
            <TextField
              label={`API Audience${currentAuthorityType.audienceRequired ? ' (Required)' : ' (Optional)'}`}
              value={effectiveValues.audience}
              onChange={(e) => handleChange('audience', e.target.value)}
              fullWidth
              placeholder="https://your-api.example.com/api"
              helperText={currentAuthorityType.audienceHelperText}
              required={currentAuthorityType.audienceRequired}
              sx={{ mb: currentAuthorityType.showAudience ? 0 : -3 }}
            />
          </Collapse>
          <Collapse in={!currentAuthorityType.showAudience} timeout={300}>
            <Alert
              severity="info"
              icon={<InfoIcon />}
              sx={{ mt: 0 }}
            >
              <Typography variant="body2">
                <strong>API Audience not required for {currentAuthorityType.label}.</strong>
                {' '}{currentAuthorityType.audienceHiddenReason}
              </Typography>
            </Alert>
          </Collapse>
        </Grid>

        {/* Redirect URI */}
        <Grid item xs={12}>
          <TextField
            label="Redirect URI"
            value={effectiveValues.redirectUri}
            onChange={(e) => handleChange('redirectUri', e.target.value)}
            fullWidth
            placeholder={`${window.location.origin}/callback`}
            helperText="OAuth callback URL (default: current origin + /callback)"
          />
        </Grid>

        {/* Logout Redirect URI */}
        <Grid item xs={12}>
          <TextField
            label="Logout Redirect URI"
            value={effectiveValues.logoutRedirectUri}
            onChange={(e) => handleChange('logoutRedirectUri', e.target.value)}
            fullWidth
            placeholder={`${window.location.origin}/login`}
            helperText="Post-logout redirect URL (default: current origin + /login)"
          />
        </Grid>

        {/* Scopes */}
        <Grid item xs={12}>
          <TextField
            label="OAuth Scopes"
            value={effectiveValues.scope}
            onChange={(e) => handleChange('scope', e.target.value)}
            fullWidth
            placeholder="openid profile email"
            helperText="Space-separated OAuth scopes (default: openid profile email)"
          />
        </Grid>

        {/* Clear Overrides Section */}
        <Grid item xs={12}>
          <Divider sx={{ my: 2 }} />
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              bgcolor: hasOverrides ? 'warning.light' : 'grey.100',
              borderRadius: 1,
              border: 1,
              borderColor: hasOverrides ? 'warning.main' : 'grey.300'
            }}
          >
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {hasOverrides ? 'Custom Overrides Active' : 'Using Webpack Defaults'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {hasOverrides
                  ? 'You have custom OAuth settings configured. Click "Clear Overrides" to reset to webpack build-time defaults.'
                  : 'All OAuth settings are using webpack build-time defaults.'}
              </Typography>
            </Box>
            <Button
              variant="outlined"
              color="warning"
              startIcon={<ClearIcon />}
              onClick={handleClearOverrides}
              disabled={!hasOverrides}
              sx={{ ml: 2, whiteSpace: 'nowrap' }}
            >
              Clear Overrides
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Success Message Snackbar */}
      <Snackbar
        open={showSuccessMessage}
        autoHideDuration={4000}
        onClose={() => setShowSuccessMessage(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setShowSuccessMessage(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          OAuth settings cleared successfully. Refresh the page to apply changes.
        </Alert>
      </Snackbar>
    </Box>
  );
};
