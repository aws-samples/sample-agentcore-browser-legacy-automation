// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Settings Modal Component — Configuration interface for the blog UI.
 *
 * Single-profile reference implementation — voice/interview sections
 * removed. Exposes: application tuning, theme, notifications, OAuth overrides.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  SettingsApplications as SettingsApplicationsIcon,
  Palette as PaletteIcon,
  Person as PersonIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';

import {
  ConfigurationSettings,
  SettingsModalProps,
  SettingsSection,
  SETTINGS_SECTIONS,
} from '../../types/settings.types';
import { configurationService } from '../../services/ConfigurationService';

import { ApplicationSettingsSection } from './sections/ApplicationSettingsSection';
import { ThemeSettingsSection } from './sections/ThemeSettingsSection';
import { NotificationSettingsSection } from './sections/NotificationSettingsSection';
import { OAuthSettingsSection } from './sections/OAuthSettingsSection';

// Icon mapping function
const getIconComponent = (iconName: string) => {
  const iconMap: Record<string, React.ComponentType> = {
    settings_applications: SettingsApplicationsIcon,
    palette: PaletteIcon,
    notifications: NotificationsIcon,
    security: SecurityIcon,
  };

  return iconMap[iconName] || PersonIcon;
};

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  currentSettings,
}) => {
  const [selectedSection, setSelectedSection] = useState<SettingsSection>('application');
  const [localSettings, setLocalSettings] = useState<ConfigurationSettings>(currentSettings);
  const [hasChanges, setHasChanges] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState<SettingsSection | 'all' | null>(null);

  useEffect(() => {
    setLocalSettings(currentSettings);
    setHasChanges(false);
  }, [currentSettings]);

  useEffect(() => {
    const changed = JSON.stringify(localSettings) !== JSON.stringify(currentSettings);
    setHasChanges(changed);
  }, [localSettings, currentSettings]);

  const handleSectionChange = useCallback((section: SettingsSection) => {
    setSelectedSection(section);
  }, []);

  const handleSettingsChange = useCallback(
    (section: SettingsSection, sectionSettings: unknown) => {
      setLocalSettings((prev) => ({
        ...prev,
        [section]: sectionSettings,
      }));
    },
    [],
  );

  const handleSave = useCallback(() => {
    onSave(localSettings);
    setHasChanges(false);
  }, [localSettings, onSave]);

  const handleReset = useCallback((section?: SettingsSection) => {
    if (section) {
      const defaults = configurationService.getDefaults();
      setLocalSettings((prev) => ({
        ...prev,
        [section]: defaults[section],
      }));
    } else {
      setLocalSettings(configurationService.getDefaults());
    }
    setShowResetConfirm(null);
  }, []);

  const handleClose = useCallback(() => {
    if (hasChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        setLocalSettings(currentSettings);
        setHasChanges(false);
        onClose();
      }
    } else {
      onClose();
    }
  }, [hasChanges, currentSettings, onClose]);

  const renderSectionContent = () => {
    const sectionSettings = localSettings[selectedSection];
    const onChange = (newSettings: unknown) => handleSettingsChange(selectedSection, newSettings);

    switch (selectedSection) {
      case 'application':
        return (
          <ApplicationSettingsSection
            settings={sectionSettings as ConfigurationSettings['application']}
            onChange={onChange as (s: ConfigurationSettings['application']) => void}
          />
        );
      case 'theme':
        return (
          <ThemeSettingsSection
            settings={sectionSettings as ConfigurationSettings['theme']}
            onChange={onChange as (s: ConfigurationSettings['theme']) => void}
          />
        );
      case 'notifications':
        return <NotificationSettingsSection />;
      case 'oauth':
        return (
          <OAuthSettingsSection
            settings={(sectionSettings as ConfigurationSettings['oauth']) || {}}
            onChange={onChange as (s: ConfigurationSettings['oauth']) => void}
          />
        );
      default:
        return <Typography>Section not implemented</Typography>;
    }
  };

  const selectedSectionConfig = SETTINGS_SECTIONS.find((s) => s.key === selectedSection);

  return (
    <>
      <Dialog
        open={isOpen}
        onClose={handleClose}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            height: '80vh',
            maxHeight: '800px',
          },
        }}
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h5" component="h2">
              Settings
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 0, display: 'flex', height: '100%' }}>
          {/* Left Menu */}
          <Box
            sx={{
              width: 280,
              borderRight: 1,
              borderColor: 'divider',
              bgcolor: 'background.paper',
            }}
          >
            <List sx={{ p: 1 }}>
              {SETTINGS_SECTIONS.map((section) => (
                <ListItem key={section.key} disablePadding sx={{ mb: 0.5 }}>
                  <ListItemButton
                    selected={selectedSection === section.key}
                    onClick={() => handleSectionChange(section.key)}
                    sx={{
                      borderRadius: 1,
                      '&.Mui-selected': {
                        bgcolor: 'primary.main',
                        color: 'primary.contrastText',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                        },
                        '& .MuiListItemIcon-root': {
                          color: 'primary.contrastText',
                        },
                      },
                    }}
                  >
                    <ListItemIcon>
                      {React.createElement(getIconComponent(section.icon))}
                    </ListItemIcon>
                    <ListItemText
                      primary={section.title}
                      secondary={
                        selectedSection === section.key ? section.description : undefined
                      }
                      secondaryTypographyProps={{
                        sx: { color: 'inherit', opacity: 0.8, fontSize: '0.75rem' },
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Box>

          {/* Right Content */}
          <Box sx={{ flex: 1, p: 3, overflow: 'auto' }}>
            <Box mb={2}>
              <Typography variant="h6" gutterBottom>
                {selectedSectionConfig?.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {selectedSectionConfig?.description}
              </Typography>
            </Box>

            <Divider sx={{ mb: 3 }} />

            {renderSectionContent()}

            {/* Section Reset Button */}
            <Box mt={4} pt={2} borderTop={1} borderColor="divider">
              <Button
                variant="outlined"
                color="warning"
                onClick={() => setShowResetConfirm(selectedSection)}
                size="small"
              >
                Reset {selectedSectionConfig?.title} to Defaults
              </Button>
            </Box>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Button
            variant="outlined"
            color="error"
            onClick={() => setShowResetConfirm('all')}
          >
            Reset All
          </Button>
          <Box sx={{ flex: 1 }} />
          {hasChanges && (
            <Typography variant="body2" color="warning.main" sx={{ mr: 2 }}>
              You have unsaved changes
            </Typography>
          )}
          <Button onClick={handleClose} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSave} variant="contained" disabled={!hasChanges}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reset Confirmation Dialog */}
      <Dialog open={showResetConfirm !== null} onClose={() => setShowResetConfirm(null)}>
        <DialogTitle>Confirm Reset</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to reset{' '}
            {showResetConfirm === 'all'
              ? 'all settings'
              : SETTINGS_SECTIONS.find((s) => s.key === showResetConfirm)?.title}{' '}
            to their default values? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowResetConfirm(null)}>Cancel</Button>
          <Button
            onClick={() =>
              handleReset(showResetConfirm === 'all' ? undefined : (showResetConfirm as SettingsSection))
            }
            color="error"
            variant="contained"
          >
            Reset
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default SettingsModal;
