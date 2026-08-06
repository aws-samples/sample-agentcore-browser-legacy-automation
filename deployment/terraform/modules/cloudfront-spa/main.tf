# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# CloudFront SPA Module
# =============================================================================
# Deploys a static single-page application from a private S3 bucket behind a
# CloudFront distribution with Origin Access Control.
#
# Key characteristics:
#   - S3 bucket is private; CloudFront reads via OAC (not public-read).
#   - SPA error-response rules rewrite 404/403 -> 200 /index.html for client-side
#     routing on direct URL loads.
#   - HTTPS-only viewer policy.
#   - AES-256 server-side encryption on the bucket.
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.18"
    }
  }
}

# -----------------------------------------------------------------------------
# Private S3 Bucket — CloudFront origin
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -----------------------------------------------------------------------------
# CloudFront Origin Access Control
# -----------------------------------------------------------------------------
resource "aws_cloudfront_origin_access_control" "this" {
  name                              = "${var.distribution_name}-oac"
  description                       = "OAC for ${var.distribution_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# -----------------------------------------------------------------------------
# Security Response Headers Policy
# -----------------------------------------------------------------------------
# Emits HSTS, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy on
# every response, plus an optional Content-Security-Policy when a non-empty
# policy string is supplied. Attached to the default cache behavior below.
resource "aws_cloudfront_response_headers_policy" "security_headers" {
  count = var.enable_security_headers ? 1 : 0

  name = "${var.distribution_name}-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = var.hsts_max_age_sec
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = var.frame_option
      override     = true
    }

    referrer_policy {
      referrer_policy = var.referrer_policy
      override        = true
    }

    dynamic "content_security_policy" {
      for_each = var.content_security_policy != "" ? [1] : []
      content {
        content_security_policy = var.content_security_policy
        override                = true
      }
    }
  }
}

# -----------------------------------------------------------------------------
# CloudFront Distribution
# -----------------------------------------------------------------------------
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.default_root_object
  price_class         = var.price_class
  comment             = var.distribution_name
  web_acl_id          = var.web_acl_id != "" ? var.web_acl_id : null
  aliases             = var.aliases
  tags                = var.tags

  origin {
    domain_name              = aws_s3_bucket.this.bucket_regional_domain_name
    origin_id                = "s3-${aws_s3_bucket.this.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  default_cache_behavior {
    target_origin_id = "s3-${aws_s3_bucket.this.id}"

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]

    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    # AWS-managed CachingOptimized policy — serves static assets efficiently.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    # Security headers (HSTS, X-Frame-Options, CSP, ...) when enabled.
    response_headers_policy_id = var.enable_security_headers ? aws_cloudfront_response_headers_policy.security_headers[0].id : null
  }

  dynamic "custom_error_response" {
    for_each = var.custom_error_responses
    content {
      error_code            = custom_error_response.value.error_code
      response_code         = custom_error_response.value.response_code
      response_page_path    = custom_error_response.value.response_page_path
      error_caching_min_ttl = 10
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    # If an ACM cert ARN is provided, use it with the supplied aliases.
    # Otherwise fall back to the default *.cloudfront.net cert.
    cloudfront_default_certificate = var.acm_certificate_arn == "" ? true : null
    acm_certificate_arn            = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
    ssl_support_method             = var.acm_certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version       = var.acm_certificate_arn != "" ? "TLSv1.2_2021" : "TLSv1"
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket Policy — grant OAC read access
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "s3_oac" {
  statement {
    sid    = "AllowCloudFrontOAC"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.s3_oac.json

  # Ensure public-access block is in place before we attach any policy.
  depends_on = [aws_s3_bucket_public_access_block.this]
}
