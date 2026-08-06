// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * notification.types.ts smoke test — verifies the runtime constants are
 * exported and have the expected shape.
 */

import {
  DEFAULT_NOTIFICATION_PREFERENCES,
  DEFAULT_NOTIFICATION_CONFIG,
  NOTIFICATION_COMPONENTS,
} from '../../../src/types/notification.types';

describe('notification.types runtime exports', () => {
  it('DEFAULT_NOTIFICATION_PREFERENCES defines a boolean for every registered component', () => {
    expect(DEFAULT_NOTIFICATION_PREFERENCES).toBeDefined();
    expect(typeof DEFAULT_NOTIFICATION_PREFERENCES).toBe('object');
    const prefsRecord = DEFAULT_NOTIFICATION_PREFERENCES as unknown as Record<string, boolean>;
    NOTIFICATION_COMPONENTS.forEach((component) => {
      expect(typeof prefsRecord[component.name]).toBe('boolean');
    });
  });

  it('DEFAULT_NOTIFICATION_CONFIG defines maxNotifications and defaultAutoHideDuration', () => {
    expect(typeof DEFAULT_NOTIFICATION_CONFIG.maxNotifications).toBe('number');
    expect(DEFAULT_NOTIFICATION_CONFIG.maxNotifications).toBeGreaterThan(0);
    expect(typeof DEFAULT_NOTIFICATION_CONFIG.defaultAutoHideDuration).toBe('number');
  });

  it('NOTIFICATION_COMPONENTS is a non-empty array of descriptor objects', () => {
    expect(Array.isArray(NOTIFICATION_COMPONENTS)).toBe(true);
    expect(NOTIFICATION_COMPONENTS.length).toBeGreaterThan(0);
    NOTIFICATION_COMPONENTS.forEach((c) => {
      expect(typeof c.name).toBe('string');
      expect(typeof c.displayName).toBe('string');
      expect(typeof c.description).toBe('string');
      expect(typeof c.defaultEnabled).toBe('boolean');
    });
  });
});
