# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "loggroup_name" {
  type        = string
  description = "Name of CloudWatch Log Group"
}

variable "retention_in_days" {
  type        = number
  description = "Number of days to retain CloudWatch Log Group. Defaults to 365 (1 year) to satisfy log-retention baselines; override for shorter dev retention if desired."
  default     = 365
}

variable "kms_key_id" {
  type        = string
  description = "KMS Key ARN to use for encryption of data in CloudWatch Log Group"
  default     = null
  nullable    = true
}

# ----------------------------------------------------------
#                         Tags
# ----------------------------------------------------------
variable "tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}

