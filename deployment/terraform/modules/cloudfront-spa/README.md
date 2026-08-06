# CloudFront SPA Terraform Module

Deploys a single-page application to CloudFront with a private S3 origin. Suitable for any static SPA (React, Vue, Angular) whose routing is client-side.

## What it creates

- A private S3 bucket with public access fully blocked, AES-256 server-side encryption, and ownership controls set to `BucketOwnerEnforced`.
- A CloudFront Origin Access Control (OAC) that signs requests from the distribution to S3.
- A CloudFront distribution that:
  - Serves `index.html` as the default root object.
  - Rewrites 404 and 403 responses to 200 `/index.html` so client-side routing works on direct-URL loads.
  - Redirects viewer HTTP to HTTPS.
  - Uses `PriceClass_100` by default (US / Canada / Europe edge locations).
- An S3 bucket policy granting the OAC read access to the bucket.
- A CloudFront Response Headers Policy (enabled by default) that adds HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options`, `Referrer-Policy`, and an optional `Content-Security-Policy` to every response.

## Content-Security-Policy

The module does not build a CSP for you — pass a complete policy string via `content_security_policy` from the calling stack, where the real gateway / IdP / asset origins are known. A CSP that is too strict silently breaks the app, so build it from actual origins rather than copying a generic example. For this reference architecture the calling stack allows: same-origin defaults; the gateway `wss://` origin and the Cognito discovery + hosted-UI hosts in `connect-src`; `'unsafe-inline'` in `style-src` (MUI/Emotion inject inline styles); and the S3 pre-signed-URL host in `img-src` (screenshots). Leave `content_security_policy` empty to emit the other headers without a CSP.

## Usage

```hcl
module "ui" {
  source = "../../modules/cloudfront-spa"

  distribution_name = "browser-agent-blog-ui"
  bucket_name       = "browser-agent-blog-ui-123456789012-us-west-2"

  tags = {
    Project     = "Browser-Agent"
    Environment = "dev"
  }
}

output "ui_url" {
  value = "https://${module.ui.distribution_domain_name}"
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| `distribution_name` | Logical name (used in tags / comment) | `string` | n/a |
| `bucket_name` | Globally unique S3 bucket name | `string` | n/a |
| `default_root_object` | Default root object served at `/` | `string` | `"index.html"` |
| `custom_error_responses` | SPA-style error rules | `list(object)` | 404 → 200 `/index.html`, 403 → 200 `/index.html` |
| `price_class` | CloudFront price class | `string` | `"PriceClass_100"` |
| `acm_certificate_arn` | ACM cert ARN in us-east-1 for custom domain | `string` | `""` |
| `aliases` | Custom-domain aliases | `list(string)` | `[]` |
| `web_acl_id` | WAFv2 Web ACL ID | `string` | `""` |
| `enable_security_headers` | Attach the response-headers policy (HSTS, CTO, XFO, Referrer-Policy, optional CSP) | `bool` | `true` |
| `content_security_policy` | Full CSP header value; empty omits CSP but keeps the other headers | `string` | `""` |
| `hsts_max_age_sec` | `max-age` for Strict-Transport-Security | `number` | `31536000` |
| `frame_option` | X-Frame-Options: `DENY` or `SAMEORIGIN` | `string` | `"DENY"` |
| `referrer_policy` | Referrer-Policy value | `string` | `"strict-origin-when-cross-origin"` |
| `tags` | Tags applied to all resources | `map(string)` | `{}` |

## Outputs

| Name | Description |
|------|-------------|
| `distribution_id` | CloudFront distribution ID |
| `distribution_arn` | CloudFront distribution ARN |
| `distribution_domain_name` | CloudFront `*.cloudfront.net` domain |
| `bucket_name` | Name of the private S3 origin bucket |
| `bucket_regional_domain_name` | Regional S3 endpoint (origin target) |
| `oac_id` | Origin Access Control ID |

## License

SPDX-License-Identifier: MIT-0. Part of the Browser Agent blog reference architecture.
