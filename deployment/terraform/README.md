# Deployment Terraform

Infrastructure-as-code for the Browser Agent blog reference architecture. One `terraform apply` provisions every cloud resource needed to run the full demo: Cognito user pool, AgentCore runtime, ECS Fargate gateway, CloudFront UI, ECR repositories, IAM roles, and S3 session store.

## Layout

```
deployment/terraform/
├── README.md                     ← this file
├── modules/                      ← reusable Terraform modules
│   ├── bedrock-agentcore-runtime/  (copied — see note below)
│   ├── cloudfront-spa/             (new — see note below)
│   ├── cloudwatch-log-group/       (copied)
│   ├── cognito-user-pool/          (new)
│   ├── dynamodb/                   (copied)
│   ├── ecr-repository/             (copied)
│   ├── ecs-fargate/                (copied)
│   ├── iam/                        (copied)
│   └── s3/                         (copied)
└── stacks/
    └── all/                      ← single-apply end-to-end stack
        ├── main.tf                 (wires every module)
        ├── variables.tf
        ├── outputs.tf
        ├── versions.tf
        ├── providers.tf
        ├── terraform.tfvars.sample
        ├── policies/               (8 IAM policy JSONs for the AgentCore role)
        ├── deploy-ui.sh            (post-apply UI build + S3 sync + CloudFront invalidate)
        └── teardown.sh             (safe terraform destroy wrapper)
```

### "Copied" vs "new" modules

The 7 copied modules are snapshots of generic Terraform modules the team maintains elsewhere. Only their top-level `.tf` files and README are copied (no `tests/`, `examples/`, CI metadata, or CHANGELOG) — the module source is not modified so upstream compatibility is preserved. If you need to update one, re-copy it from the source of truth.

The 2 new modules (`cognito-user-pool/`, `cloudfront-spa/`) are purpose-built for this reference architecture.

## Prerequisites

- Terraform `>= 1.5`
- AWS CLI configured with credentials for the target account
- An existing VPC with at least 2 private subnets (for the gateway tasks) and 2 public subnets (for the ALB), plus security groups for both
- An IAM principal with permission to create Cognito user pools, Bedrock AgentCore runtimes, ECS/ALB resources, CloudFront distributions, S3 buckets, ECR repos, and IAM roles

The stack does NOT provision a VPC. Use your default VPC or an existing one.

## Deployment flow

There is a chicken-and-egg problem: the AgentCore Runtime and ECS Fargate service need a container image in ECR before they can start, but ECR repos are created by the same apply. The pragmatic workaround is a two-pass apply:

```bash
cd deployment/terraform/stacks/all
cp terraform.tfvars.sample terraform.tfvars
# Edit terraform.tfvars with your VPC / subnet / security-group IDs and
# Cognito domain prefix.

terraform init

# Pass 1 — provision ECR repos only.
terraform apply \
  -target=module.browser_agent_ecr \
  -target=module.gateway_ecr

# Push images to ECR using the per-project build + push scripts.
# `docker_build_ecr.sh` builds locally; `docker_push_ecr.sh` tags + pushes.
cd ../../../../browser-agent-container
./scripts/docker_build_ecr.sh && ./scripts/docker_push_ecr.sh

cd ../gateway-container
./scripts/docker_build_ecr.sh && ./scripts/docker_push_ecr.sh

# Pass 2 — provision everything else.
cd ../deployment/terraform/stacks/all
terraform apply
```

Cognito callback URLs, the AgentCore runtime ARN, the AgentCore endpoint, and the session-store bucket name are all wired automatically from Terraform outputs, so there is no manual placeholder edit between pass 2 and sign-in. The first full apply takes 20–30 minutes — CloudFront propagation (5–10 minutes) and ACM DNS validation (1–5 minutes when `gateway_public_hostname` + `route53_zone_id` are set) dominate.

## Deploying the UI

The UI is a separate build step because webpack needs the CloudFront domain + Cognito IDs + gateway URL as build-time constants (webpack `DefinePlugin`).

```bash
./deploy-ui.sh
```

The script reads `terraform output -json`, runs `yarn build` in `chat-bot-ui/` with the correct env vars, `aws s3 sync`s the `dist/` output to the UI bucket, and issues a CloudFront invalidation.

## Per-project deploy folders

Each container has its own `deploy/` folder (`browser-agent-container/deploy/agentcore/`, `gateway-container/deploy/`) for isolated iteration on just that service. Those folders reference the same modules under `deployment/terraform/modules/`, so editing a module once updates both paths.

Deploy paths in practice:

- **Full-stack, end-to-end (primary)** — `deployment/terraform/stacks/all/`. The workflow documented above.
- **Per-project iteration** — `<container>/deploy/*/`. Useful when developing a single service without rebuilding the whole stack. You must manually supply the Cognito/VPC/network inputs that the consolidated stack wires automatically.

## Tear-down

Use the helper script to destroy the stack safely:

```bash
./teardown.sh
```

The script:

1. Prompts for explicit confirmation (type `destroy`).
2. Empties the CloudFront S3 bucket (CloudFront origins can't be destroyed while they hold objects).
3. Empties the S3 session-store bucket for the same reason.
4. Runs `terraform destroy -var-file=terraform.tfvars`.

Cognito hosted-UI domains take a few minutes to release; if you destroy and immediately re-apply with the same `cognito_domain_prefix` you may hit a "domain already exists" error — wait or use a different prefix.

## Outputs reference

| Output | Used by |
|--------|---------|
| `cloudfront_domain` | UI URL. Consumed by `deploy-ui.sh`. |
| `cloudfront_distribution_id` | `deploy-ui.sh` for `aws cloudfront create-invalidation`. |
| `ui_bucket_name` | `deploy-ui.sh` and `teardown.sh`. |
| `cognito_user_pool_id` | Admin console operations (e.g. `admin-create-user`). |
| `cognito_user_pool_issuer` | UI build-time `__OIDC_AUTHORITY__`. |
| `cognito_discovery_url` | AgentCore `jwt_discovery_url` (wired automatically) + diagnostic checks. |
| `ui_app_client_id` | UI build-time `__OIDC_CLIENT_ID__`. |
| `m2m_app_client_id` / `m2m_app_client_secret` / `m2m_token_endpoint` | Integration tests. |
| `browser_agent_ecr_url` / `gateway_ecr_url` | Container build + push scripts. |
| `agentcore_runtime_arn` / `agentcore_invocation_url` | Wired automatically into the gateway's `BROWSER_AGENT_ARN` env var; surfaced for diagnostic checks. |
| `gateway_public_url` | UI build-time WebSocket origin. `deploy-ui.sh` reads this and turns `https://<host>` into `wss://<host>` — the UI's `buildWebSocketUrl` helper appends `/ws?token=...&profile=browser`, so the build-time value must be the bare scheme+host (no path). |
| `gateway_alb_dns_name` | Direct ALB DNS, retained for diagnostics. Use `gateway_public_url` for UI wiring. |
| `s3_sessions_bucket` | Wired automatically into the browser-agent `BA_SESSION_STORE_BUCKET` env var; surfaced for diagnostic checks. |

See `outputs.tf` for the full list.
