# AgentCore Runtime Deployment — Browser Agent

Terraform configuration to deploy the Browser Agent to AWS Bedrock AgentCore Runtime.

## Prerequisites

1. **Build and push Docker image**:
   ```bash
   ./scripts/docker_build_ecr.sh
   ./scripts/docker_push_ecr.sh
   ```

2. **Terraform** >= 1.0

3. **AWS CLI** v2 with configured profile

4. **jq** (for custom claims script):
   ```bash
   brew install jq  # macOS
   ```

## Terraform Module Sources

The `main.tf` uses a **repo-local relative path** pointing at `deployment/terraform/modules/` at the workspace root:

```hcl
module "browser_agent" {
  source = "../../../deployment/terraform/modules/bedrock-agentcore-runtime"
  # ...
}
```

This is the default, publishable configuration. `terraform init` works without any external package registry, SSH credentials, or authentication — the module source is a plain relative path into the same repo. If you want to fork the module, edit it under `deployment/terraform/modules/`; both this per-project deploy and the single-apply stack at `deployment/terraform/stacks/all/` pick up the change automatically.

## Deployment Steps

### 1. Setup IAM Role

```bash
cd deploy/agentcore
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
./setup-iam-role.sh
```

This creates the role with all required policies:
- Core: ECR, Bedrock, CloudWatch, AgentCore
- Browser-specific: AgentCore Browser (11 browser actions)
- Session persistence: S3 (screenshots + session data), DynamoDB (session metadata)

### 2. Create user-terraform.tfvars

```bash
cp terraform.tfvars.example user-terraform.tfvars
# Edit with your values (role ARN from step 1, account ID, image tag, etc.)
```

### 3. Deploy

```bash
terraform init
terraform apply -var-file=user-terraform.tfvars
```

### 4. Configure Custom JWT Claims (optional)

For IdPs using non-standard claims (e.g., Auth0 `azp`):

```bash
AWS_REGION=us-west-2 \
AWS_PROFILE=your-profile \
OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration \
JWT_AUDIENCE=https://your-api-audience \
JWT_CLIENT_ID=your-m2m-client-id \
JWT_CLAIM_NAME=azp \
RUNTIME_ID=browser_agent-xxxxxxxxxx \
./update-custom-claims.sh
```

Get `RUNTIME_ID` from `terraform output agent_runtime_id`.

### 5. Get Outputs

```bash
terraform output
```

Key outputs: `agent_runtime_id`, `invocation_url`, `endpoint_name`.

## Environment Variables

All container env vars are in the `environment_variables` map in `user-terraform.tfvars` (passthrough pattern).

| Variable | Description | Default |
|----------|-------------|---------|
| `BA_BROWSER_MODEL_ID` | Bedrock model ID (cross-region inference profile) | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `BA_SESSION_TIMEOUT` | Browser session TTL in seconds | `3600` |
| `BA_SESSIONS_DIR` | Local session/screenshot directory | `sessions` |
| `BA_MAX_STEPS_PER_SESSION` | Max agent steps per session | `100` |
| `BA_DISCONNECT_GRACE_SECONDS` | Grace period before terminating on disconnect | `30` |
| `BA_HITL_TIMEOUT_SECONDS` | HITL prompt auto-cancel timeout | `300` |
| `BA_SESSION_STORE_TYPE` | Session backend: `memory`, `dynamodb`, `s3` | `memory` |
| `BA_SESSION_STORE_TABLE` | DynamoDB table (required when type=dynamodb) | — |
| `BA_SESSION_STORE_BUCKET` | S3 bucket (required when type=dynamodb or s3) | — |
| `BA_SESSION_STORE_PREFIX` | S3/DDB key prefix | `browser-sessions` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED` | OTEL log handler | `false` |

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `setup-iam-role.sh` | Create/update IAM role with all required policies |
| `update-custom-claims.sh` | Configure JWT custom claims post-deployment |

## Deploying New Versions

1. Build and push new image with new tag
2. Update `image_tag` in `user-terraform.tfvars`
3. `terraform apply -var-file=user-terraform.tfvars`

## Differences from Concierge Agent

| Aspect | Concierge | Browser Agent |
|--------|-----------|---------------|
| IAM policies | + invoke-specialists, identity-token-vault | + browser, s3-session, dynamodb-session |
| AgentCore modules | Runtime + Memory + Identity | Runtime only |
| Env prefix | `SA_` | `BA_` |
| Server protocol | WebSocket | WebSocket |

## Cleanup

```bash
terraform destroy -var-file=user-terraform.tfvars
```
