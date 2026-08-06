# S3 Bucket Terraform Module

This Terraform module creates and manages an AWS S3 bucket with public access blocking, optional versioning, and force destroy support.

## Features

- S3 bucket creation with configurable name
- Public access block (all four settings enabled by default)
- Optional bucket versioning
- Force destroy support for clean teardown
- Tag management

## Usage

```hcl
module "athena_results_bucket" {
  source = "./s3"

  bucket_name        = "amzn-s3-demo-app-results-123456789012-us-west-2"
  versioning_enabled = true
  force_destroy      = true

  bucket_tags = {
    Environment = "prod"
    Project     = "my-app"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 5.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 5.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket_name | S3 bucket name | `string` | n/a | yes |
| versioning_enabled | Enable bucket versioning | `bool` | `false` | no |
| force_destroy | Allow Terraform to destroy the bucket even if it contains objects | `bool` | `false` | no |
| bucket_tags | A map containing tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_arn | S3 bucket ARN |
| bucket_name | S3 bucket name |

## Security

The module automatically configures a public access block on every bucket:

- `block_public_acls = true`
- `block_public_policy = true`
- `ignore_public_acls = true`
- `restrict_public_buckets = true`

## License

SPDX-License-Identifier: MIT-0. Part of the Browser Agent blog reference architecture.
