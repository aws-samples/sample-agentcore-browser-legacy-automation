# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "repository_url" {
  value = aws_ecr_repository.ecr_repository.repository_url
}
