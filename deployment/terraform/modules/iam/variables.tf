# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "role_name" {
  type        = string
  description = "IAM role name"
}

variable "custom_role_policy" {
  type = object({
    Version   = string
    Statement = any
  })
  description = "Complete role policy if a more complex role policy is required."
  default     = null
}

variable "principal_name" {
  type        = string
  description = "Service principal name"
  default     = ""
}

variable "inline_policies" {
  type = list(object({
    name   = string
    policy = any
  }))
}

# ----------------------------------------------------------
#                         Tags
# ----------------------------------------------------------
variable "role_tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}
