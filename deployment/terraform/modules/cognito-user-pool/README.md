# Cognito User Pool Terraform Module

Creates a Cognito user pool with a hosted-UI domain, resource server, and optional SPA + M2M app clients. Designed for the Browser Agent blog reference architecture, but reusable for any OIDC-authenticated AWS workload.

## Features

- Single user pool with email-as-username and verified-email recovery
- Configurable password policy and MFA
- Hosted-UI domain using the Cognito-managed `*.auth.<region>.amazoncognito.com` subdomain
- Resource server with custom OAuth scopes (for M2M access control)
- Optional SPA app client with PKCE + authorization-code grant (no client secret)
- Optional M2M app client with `client_credentials` grant and generated secret

## Usage

```hcl
module "cognito" {
  source = "../../modules/cognito-user-pool"

  user_pool_name = "browser-agent-blog-pool"
  domain_prefix  = "browser-agent-blog-123abc"

  callback_urls = ["https://d123abc.cloudfront.net/login"]
  logout_urls   = ["https://d123abc.cloudfront.net/login"]

  tags = {
    Project     = "Browser-Agent"
    Environment = "dev"
  }
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| `user_pool_name` | User pool name | `string` | n/a |
| `domain_prefix` | Globally unique hosted-UI domain prefix | `string` | n/a |
| `callback_urls` | Allowed OAuth callback URLs for the SPA client | `list(string)` | `[]` |
| `logout_urls` | Allowed post-logout redirect URLs | `list(string)` | `[]` |
| `create_ui_app_client` | Create the SPA app client | `bool` | `true` |
| `ui_app_client_name` | SPA app client name | `string` | `"chat-bot-ui"` |
| `create_m2m_app_client` | Create the M2M app client | `bool` | `true` |
| `m2m_app_client_name` | M2M app client name | `string` | `"integration-tests-m2m"` |
| `resource_server_identifier` | Resource-server identifier (namespaces the M2M scopes) | `string` | `"browser-agent"` |
| `m2m_scopes` | Custom OAuth scopes to register on the resource server | `list(object({name, description}))` | `[{name="invoke", description="Invoke the browser agent"}]` |
| `password_policy` | Password-policy object | `object` | 12 chars, lower+upper+number required |
| `mfa_configuration` | `OFF` / `ON` / `OPTIONAL` | `string` | `"OFF"` |
| `tags` | Tags applied to all resources | `map(string)` | `{}` |

## Outputs

| Name | Description |
|------|-------------|
| `user_pool_id` | Cognito user pool ID |
| `user_pool_arn` | Cognito user pool ARN |
| `user_pool_issuer` | OIDC issuer URL (JWT `iss` claim value) |
| `discovery_url` | OIDC discovery URL (feed to AgentCore `jwt_discovery_url` and to the UI `__OIDC_AUTHORITY__`) |
| `ui_app_client_id` | SPA app client ID (empty if not created) |
| `m2m_app_client_id` | M2M app client ID (empty if not created) |
| `m2m_app_client_secret` | M2M app client secret (sensitive) |
| `m2m_token_endpoint` | OAuth2 token endpoint for `client_credentials` |
| `hosted_ui_domain` | Hosted-UI base domain |

## License

SPDX-License-Identifier: MIT-0. Part of the Browser Agent blog reference architecture.
