// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * settings.types.ts smoke test — compile-only types; we just verify the
 * module is importable so coverage machinery sees it.
 */

import * as settingsTypes from '../../../src/types/settings.types';

describe('settings.types', () => {
  it('module is importable', () => {
    expect(settingsTypes).toBeDefined();
    expect(typeof settingsTypes).toBe('object');
  });
});
