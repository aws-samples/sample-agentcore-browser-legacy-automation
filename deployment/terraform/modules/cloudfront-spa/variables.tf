# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# CloudFront SPA Module — Variables
# =============================================================================

variable "distribution_name" {
  description = "Logical name for the CloudFront distribution (used in tags / comment)."
  type        = string
}

variable "bucket_name" {
  description = "Name of the private S3 bucket that backs this distribution. Must be globally unique."
  type        = string
}

variable "default_root_object" {
  description = "Default root object served when the viewer requests \"/\"."
  type        = string
  default     = "index.html"
}

variable "custom_error_responses" {
  description = "SPA-style error-response rules. Defaults rewrite 404 and 403 to 200 /index.html so client-side routing works."
  type = list(object({
    error_code         = number
    response_code      = number
    response_page_path = string
  }))
  default = [
    {
      error_code         = 404
      response_code      = 200
      response_page_path = "/index.html"
    },
    {
      error_code         = 403
      response_code      = 200
      response_page_path = "/index.html"
    },
  ]
}

variable "price_class" {
  description = "CloudFront price class: PriceClass_100 (US/CA/EU) | PriceClass_200 | PriceClass_All."
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be one of PriceClass_100, PriceClass_200, PriceClass_All."
  }
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom-domain HTTPS. Must be in us-east-1. Empty string = use the default CloudFront certificate + *.cloudfront.net domain."
  type        = string
  default     = ""
}

variable "aliases" {
  description = "Custom-domain aliases (e.g. [\"app.example.com\"]). Requires a matching acm_certificate_arn."
  type        = list(string)
  default     = []
}

variable "web_acl_id" {
  description = "Optional WAFv2 Web ACL ID to attach to the distribution. Empty string = no WAF."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Security response headers
# -----------------------------------------------------------------------------
variable "enable_security_headers" {
  description = "Attach a CloudFront Response Headers Policy (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and optionally CSP) to the default cache behavior."
  type        = bool
  default     = true
}

variable "content_security_policy" {
  description = "Content-Security-Policy header value. Empty string omits the CSP directive but still emits the other security headers. Build this in the calling stack from the real gateway / IdP origins so it is not hardcoded to a single deployment."
  type        = string
  default     = ""
}

variable "hsts_max_age_sec" {
  description = "max-age (seconds) for the Strict-Transport-Security header. Default 1 year."
  type        = number
  default     = 31536000
}

variable "frame_option" {
  description = "X-Frame-Options value: DENY or SAMEORIGIN."
  type        = string
  default     = "DENY"

  validation {
    condition     = contains(["DENY", "SAMEORIGIN"], var.frame_option)
    error_message = "frame_option must be DENY or SAMEORIGIN."
  }
}

variable "referrer_policy" {
  description = "Referrer-Policy header value."
  type        = string
  default     = "strict-origin-when-cross-origin"
}

variable "tags" {
  description = "Tags to apply to all resources created by this module."
  type        = map(string)
  default     = {}
}
