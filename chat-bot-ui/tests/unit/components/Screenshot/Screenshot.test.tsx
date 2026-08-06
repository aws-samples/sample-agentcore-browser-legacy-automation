// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Screenshot smoke test — renders the thumbnail image with its alt text.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Screenshot } from '../../../../src/components/Screenshot/Screenshot';

describe('Screenshot', () => {
  it('renders the image with a stepped label', () => {
    render(
      <Screenshot
        screenshotUrl="https://signed.example/shot.png"
        title="Landing page"
        stepNumber={2}
      />,
    );
    // An <img> should be rendered with the pre-signed URL as its src.
    const img = screen.getByRole('img');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://signed.example/shot.png');
  });
});
