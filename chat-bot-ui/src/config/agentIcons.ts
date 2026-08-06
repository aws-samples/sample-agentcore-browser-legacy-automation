// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Agent Icon Mapping — Maps agent_id strings to MUI icon components.
 *
 * Provides a client-side mapping from specialist agent IDs to visual icons
 * for use in AgentCard, AgentDrawer, and ObservabilityPanel components.
 * Unmapped agent IDs fall back to the DEFAULT_AGENT_ICON (SmartToy).
 *
 * @module config/agentIcons
 */

import type { SvgIconComponent } from '@mui/icons-material';
import {
  TrendingUp,
  EditNote,
  Psychology,
  Policy,
  Gavel,
  Computer,
  SmartToy,
} from '@mui/icons-material';

/** Maps known agent_id strings to their MUI icon component. */
export const AGENT_ICON_MAP: Record<string, SvgIconComponent> = {
  'financial-analyst': TrendingUp,
  'content-assistant': EditNote,
  'general-knowledge': Psychology,
  'hr-policy': Policy,
  'legal-compliance': Gavel,
  'it-helpdesk': Computer,
};

/** Fallback icon for agents not in AGENT_ICON_MAP. */
export const DEFAULT_AGENT_ICON: SvgIconComponent = SmartToy;

/**
 * Returns the MUI icon component for a given agent ID.
 * Never returns undefined or null — falls back to DEFAULT_AGENT_ICON.
 */
export function getAgentIcon(agentId: string): SvgIconComponent {
  return AGENT_ICON_MAP[agentId] || DEFAULT_AGENT_ICON;
}
