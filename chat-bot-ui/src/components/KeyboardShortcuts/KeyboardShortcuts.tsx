// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * KeyboardShortcuts Component
 * Displays available keyboard shortcuts in a modal overlay
 */

import React from 'react';
import { Box, Typography, IconButton, Modal, Paper } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { useKeyboardNavigation } from '../../hooks/useKeyboardNavigation';

export interface KeyboardShortcutsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcuts: React.FC<KeyboardShortcutsProps> = ({
  isOpen,
  onClose,
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Focus management for modal
  const { trapFocus } = useKeyboardNavigation({
    onEscape: onClose,
  });

  // Set up focus trap when modal opens
  React.useEffect(() => {
    if (isOpen && containerRef.current) {
      const cleanup = trapFocus(containerRef.current);

      // Focus the first focusable element after a short delay to ensure rendering is complete
      setTimeout(() => {
        const firstButton = containerRef.current?.querySelector('button') as HTMLElement;
        if (firstButton) {
          firstButton.focus();
        }
      }, 100);

      return cleanup;
    }
  }, [isOpen, trapFocus]);

  const shortcuts = [
    { key: 'Ctrl + B', description: 'Toggle sidebar' },
    { key: 'Ctrl + N', description: 'Start new chat' },
    { key: 'Ctrl + ,', description: 'Open settings' },
    { key: 'Ctrl + /', description: 'Show keyboard shortcuts' },
    { key: 'Escape', description: 'Close modal or overlay' },
    { key: 'Tab', description: 'Navigate between elements' },
    { key: 'Shift + Tab', description: 'Navigate backwards' },
    { key: 'Enter', description: 'Activate focused element' },
    { key: 'Space', description: 'Activate buttons and toggles' },
    { key: 'Arrow Keys', description: 'Navigate menu items' },
  ];

  if (!isOpen) return null;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      aria-labelledby="keyboard-shortcuts-title"
      aria-describedby="keyboard-shortcuts-description"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
      }}
    >
      <Paper
        ref={containerRef}
        className="keyboard-shortcuts"
        sx={{
          position: 'relative',
          maxWidth: 500,
          width: '100%',
          maxHeight: '80vh',
          overflow: 'auto',
          p: 3,
          outline: 'none',
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-title"
        aria-describedby="keyboard-shortcuts-description"
      >
        {/* Close button */}
        <IconButton
          onClick={onClose}
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
          }}
          aria-label="Close keyboard shortcuts"
        >
          <CloseIcon />
        </IconButton>

        {/* Title */}
        <Typography
          id="keyboard-shortcuts-title"
          variant="h5"
          component="h2"
          sx={{ mb: 2, pr: 5 }}
        >
          Keyboard Shortcuts
        </Typography>

        {/* Description */}
        <Typography
          id="keyboard-shortcuts-description"
          variant="body2"
          color="text.secondary"
          sx={{ mb: 3 }}
        >
          Use these keyboard shortcuts to navigate the application more efficiently.
        </Typography>

        {/* Shortcuts list */}
        <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
          {shortcuts.map((shortcut, index) => (
            <Box
              key={index}
              component="li"
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 1.5,
                borderBottom: index < shortcuts.length - 1 ? '1px solid' : 'none',
                borderColor: 'divider',
              }}
            >
              <Typography variant="body2" sx={{ flex: 1 }}>
                {shortcut.description}
              </Typography>
              <Box
                component="kbd"
                sx={{
                  backgroundColor: 'grey.100',
                  color: 'text.primary',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  border: '1px solid',
                  borderColor: 'grey.300',
                  minWidth: 'fit-content',
                  textAlign: 'center',
                }}
              >
                {shortcut.key}
              </Box>
            </Box>
          ))}
        </Box>

        {/* Additional help text */}
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 3, display: 'block' }}
        >
          Press Escape to close this dialog, or click the close button above.
        </Typography>
      </Paper>
    </Modal>
  );
};

export default KeyboardShortcuts;