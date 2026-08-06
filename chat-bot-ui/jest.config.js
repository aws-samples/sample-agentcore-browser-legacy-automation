// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Jest configuration for chat-bot-ui React TypeScript project
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: [
    '<rootDir>/src/setupTests.ts'
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.json'
    }],
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  testMatch: [
    '<rootDir>/tests/**/*.(test|spec).(ts|tsx|js)',
    '<rootDir>/src/**/*.(test|spec).(ts|tsx|js)'
  ],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|svg|ttf|woff|woff2)$': '<rootDir>/tests/jest-transform-stub.js',
    '^react-markdown$': '<rootDir>/tests/__mocks__/react-markdown.tsx',
    '^remark-gfm$': '<rootDir>/tests/__mocks__/remark-gfm.ts'
  },
  modulePaths: ['<rootDir>/src'],
  moduleDirectories: ['node_modules', '<rootDir>/src'],
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/setupTests.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/dist/',
    '<rootDir>/build/'
  ],
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@mui|@emotion|react-markdown|remark-.*|rehype-.*|unified|bail|is-plain-obj|trough|vfile|unist-.*|mdast-.*|micromark.*|decode-named-character-reference|character-entities|property-information|hast-.*|space-separated-tokens|comma-separated-tokens|web-namespaces|zwitch|html-void-elements))'
  ],
  clearMocks: true,
  restoreMocks: true,
  verbose: true
};
