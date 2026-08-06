// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Jest mock for react-markdown — returns the children as plain text so tests
 * can assert on the rendered content without needing the ESM v9 package to
 * be transformed by babel-jest.
 *
 * Activated via jest.config.js `moduleNameMapper`.
 */

import React from 'react';

const MockReactMarkdown: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div data-testid="markdown-content">{children}</div>
);

export default MockReactMarkdown;
