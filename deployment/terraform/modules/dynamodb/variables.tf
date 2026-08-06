# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ----------------------------------------------------------
#                 DynamoDB Table Variables
# ----------------------------------------------------------

variable "dynamodb_table_name" {
  type        = string
  description = "Amazon DynamoDB table name"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for DynamoDB table encryption"
  default     = null
}

variable "billing_mode" {
  type        = string
  description = "Billing mode for the DynamoDB table.The valid values are PROVISIONED and PAY_PER_REQUEST. Defaults to PROVISIONED"
  default     = "PROVISIONED"
}

variable "enable_server_side_encryption" {
  type    = bool
  default = true
}

variable "enable_point_in_time_recovery" {
  type        = bool
  description = "Enable DynamoDB point-in-time recovery (continuous backups). Defaults to true for a recoverable table; set false to reduce cost for ephemeral/demo tables."
  default     = true
}

variable "read_capacity" {
  type        = number
  description = "Read capacity for the DyanmoDB table"
  default     = null
}

variable "write_capacity" {
  type        = number
  description = "Write capacity for the DyanmoDB table"
  default     = null
}

variable "hash_key" {
  type        = string
  description = "Hash key for the DynamoDB table"
}

variable "range_key" {
  type        = string
  description = "Attribute to use as the range (sort) key. Must also be defined as an attribute"
  default     = null
}

variable "ttl" {
  type = object({
    attribute_name = string
    enabled        = bool
    ttl_value      = number
  })
  description = "Value for item TTL and whether it is enabled for the table"
  default = {
    attribute_name = "ttl"
    enabled        = false
    ttl_value      = 86400
  }
}


variable "attributes" {
  description = "List of resources for the REST API"
  type = list(object({
    name = string
    type = string
  }))
  default = []
}

variable "dynamodb_table_tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}

# ----------------------------------------------------------
#                         Tags
# ----------------------------------------------------------
variable "tags" {
  type        = map(string)
  description = "A map containing tags. Both the key and value must be strings."
  default     = {}
}
