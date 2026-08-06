// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  SmartToy as AgentIcon,
  Psychology as ReasoningIcon,
  PhotoCamera as ScreenshotIcon,
  Visibility as LiveViewIcon,
  PanTool as HitlIcon,
  History as HistoryIcon,
  Settings as SettingsIcon,
  Keyboard as KeyboardIcon,
} from '@mui/icons-material';

interface HelpModalProps {
  open: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ open, onClose }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="help-modal-title"
      aria-describedby="help-modal-description"
    >
      <DialogTitle
        id="help-modal-title"
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pb: 1,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            🤖 Browser Agent
          </Typography>
          <Chip
            label="1.0.0"
            size="small"
            color="primary"
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
        </Box>
        <IconButton
          onClick={onClose}
          aria-label="Close help"
          sx={{ color: 'text.secondary' }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Box id="help-modal-description">
          {/* Overview */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            🚀 Overview
          </Typography>
          <Typography variant="body1" paragraph sx={{ color: 'text.secondary' }}>
            Browser Agent is an AI-powered digital worker that drives real websites in a
            managed cloud browser. Describe a task in plain language and the agent reasons
            over each page, clicks, fills, and navigates on your behalf — pausing to ask you
            for confirmation when a step needs a human decision.
          </Typography>

          <Divider sx={{ my: 3 }} />

          {/* Getting started */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            ⌨️ Getting started
          </Typography>
          <Box sx={{ pl: 2 }}>
            <Typography variant="body2" paragraph sx={{ color: 'text.secondary', mb: 1 }}>
              1. Type an instruction in the chat box, for example:
              <em> “Search Wikipedia for 'Amazon Rainforest' and summarize the top result.”</em>
            </Typography>
            <Typography variant="body2" paragraph sx={{ color: 'text.secondary', mb: 1 }}>
              2. Press Enter (or the send button) to start the run.
            </Typography>
            <Typography variant="body2" paragraph sx={{ color: 'text.secondary' }}>
              3. Watch the agent work and answer any confirmation prompts it raises.
            </Typography>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* What you'll see */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            👀 What you'll see during a run
          </Typography>
          <List dense>
            <ListItem>
              <ListItemIcon><ReasoningIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="Reasoning trace"
                secondary="The agent's thinking streams in as it decides what to do next."
              />
            </ListItem>
            <ListItem>
              <ListItemIcon><AgentIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="Action steps"
                secondary="Each browser action (click, fill, navigate) appears as a card with start and complete status."
              />
            </ListItem>
            <ListItem>
              <ListItemIcon><ScreenshotIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="Screenshots"
                secondary="A snapshot of the page is shown after key steps so you can follow along."
              />
            </ListItem>
            <ListItem>
              <ListItemIcon><LiveViewIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="Live view (optional)"
                secondary="Open the live-view panel to watch the browser session in real time."
              />
            </ListItem>
          </List>

          <Divider sx={{ my: 3 }} />

          {/* Human-in-the-loop */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            🖐️ Human-in-the-loop
          </Typography>
          <Box sx={{ pl: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <HitlIcon color="secondary" fontSize="small" sx={{ mt: 0.5 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Before a critical action, the agent may pause and ask you to confirm or
                choose an option. Respond in the prompt to resume the same browser session.
                If you don't reply within the timeout, the agent decides whether to retry,
                try a different approach, or stop.
              </Typography>
            </Box>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Sessions & navigation */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            🧭 Sessions & navigation
          </Typography>
          <List dense>
            <ListItem>
              <ListItemIcon><HistoryIcon fontSize="small" /></ListItemIcon>
              <ListItemText primary="Session history" secondary="Browse and resume previous sessions from the sidebar." />
            </ListItem>
            <ListItem>
              <ListItemIcon><SettingsIcon fontSize="small" /></ListItemIcon>
              <ListItemText primary="Settings" secondary="Configure the WebSocket URL, theme, and preferences." />
            </ListItem>
            <ListItem>
              <ListItemIcon><KeyboardIcon fontSize="small" /></ListItemIcon>
              <ListItemText
                primary="Keyboard shortcuts"
                secondary="Ctrl/Cmd+B toggles the sidebar, Ctrl/Cmd+N starts a new chat, and Ctrl/Cmd+/ shows all shortcuts."
              />
            </ListItem>
          </List>

          <Divider sx={{ my: 3 }} />

          {/* Need help */}
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            💬 Need help?
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            See the project README and the companion AWS blog post for architecture details,
            deployment steps, and troubleshooting.
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button
          onClick={onClose}
          variant="contained"
          color="primary"
          sx={{ minWidth: 100 }}
        >
          Got it! 👍
        </Button>
      </DialogActions>
    </Dialog>
  );
};
