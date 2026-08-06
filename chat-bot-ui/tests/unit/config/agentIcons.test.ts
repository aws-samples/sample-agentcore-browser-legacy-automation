// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * agentIcons.ts Tests
 *
 * Tests for AGENT_ICON_MAP, DEFAULT_AGENT_ICON, and getAgentIcon:
 * known IDs return mapped icons, unknown IDs return default, never undefined/null.
 */

import {
  TrendingUp,
  EditNote,
  Psychology,
  Policy,
  Gavel,
  Computer,
  SmartToy,
} from '@mui/icons-material';
import { AGENT_ICON_MAP, DEFAULT_AGENT_ICON, getAgentIcon } from '../../../src/config/agentIcons';

describe('agentIcons', () => {
  it('maps known agent IDs to their expected icons', () => {
    expect(AGENT_ICON_MAP['financial-analyst']).toBe(TrendingUp);
    expect(AGENT_ICON_MAP['content-assistant']).toBe(EditNote);
    expect(AGENT_ICON_MAP['general-knowledge']).toBe(Psychology);
    expect(AGENT_ICON_MAP['hr-policy']).toBe(Policy);
    expect(AGENT_ICON_MAP['legal-compliance']).toBe(Gavel);
    expect(AGENT_ICON_MAP['it-helpdesk']).toBe(Computer);
  });

  it('returns DEFAULT_AGENT_ICON (SmartToy) for unknown agent IDs', () => {
    expect(DEFAULT_AGENT_ICON).toBe(SmartToy);
    expect(getAgentIcon('unknown-agent')).toBe(SmartToy);
    expect(getAgentIcon('')).toBe(SmartToy);
  });

  it('getAgentIcon returns mapped icon for known IDs', () => {
    expect(getAgentIcon('financial-analyst')).toBe(TrendingUp);
    expect(getAgentIcon('it-helpdesk')).toBe(Computer);
  });

  it('getAgentIcon never returns undefined or null', () => {
    const testIds = ['financial-analyst', 'unknown', '', 'random-id', '123'];
    for (const id of testIds) {
      const icon = getAgentIcon(id);
      expect(icon).not.toBeUndefined();
      expect(icon).not.toBeNull();
    }
  });
});
