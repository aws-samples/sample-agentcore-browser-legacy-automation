# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ----------------------------------------------------------
#                       S3
# ----------------------------------------------------------
variable "bucket_name" {
  type        = string
  description = "S3 bucket name"
}

variable "bucket_tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}

variable "versioning_enabled" {
  type        = bool
  description = "Enable bucket versioning"
  default     = false
}

variable "force_destroy" {
  type        = bool
  description = "Allow Terraform to destroy the bucket even if it contains objects (including versioned objects)"
  default     = false
}

