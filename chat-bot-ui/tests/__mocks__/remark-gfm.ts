// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Jest mock for remark-gfm — no-op remark plugin. Activated via
 * jest.config.js `moduleNameMapper`. Returns an identity transformer so
 * react-markdown pipelines don't choke when tests load the mock.
 */

const remarkGfm = () => (tree: unknown) => tree;
export default remarkGfm;
