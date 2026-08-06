# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "common_tags" {
  description = "Tags for ECR"
  type        = map(string)
}

variable "ecr_name" {
  description = "Name of the ECR repository."
  type        = string
  #default     = "fmeval-process-job-container"
}

variable "ecr_image_tag_mutability" {
  description = "The tag mutability setting for the repository. Must be one of: `MUTABLE` or `IMMUTABLE`."
  type        = string
  default     = "MUTABLE"
  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.ecr_image_tag_mutability)
    error_message = "The ecr_image_tag_mutability must be either MUTABLE or IMMUTABLE."
  }
}

variable "ecr_force_delete" {
  description = "If `true`, will delete the repository even if it contains images. Defaults to `false`"
  type        = bool
  default     = false
}

variable "ecr_scan_on_push" {
  description = "Indicates whether images are scanned after being pushed to the repository (true) or not scanned (false)."
  type        = bool
  default     = true
}

variable "ecr_encryption_type" {
  description = "The encryption type to use for the repository. Valid values are `AES256` or `KMS`"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "KMS"], var.ecr_encryption_type)
    error_message = "The encryption_type must be either AES256 or KMS."
  }
}

variable "ecr_kms_master_key_arn" {
  type        = string
  description = "The ARN of an AWS-managed customer master key (CMK) for Amazon ECR or a custom CMK."
  default     = ""
}

variable "ecr_tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}
