# Concierge Gateway Container - Deployment Guide

This directory contains Terraform configuration and deployment scripts for the Concierge Gateway Container.

## Overview

The NGINX gateway enables browser-based WebSocket connections to AWS Bedrock AgentCore Runtime by extracting JWT tokens from query parameters, injecting them as Authorization headers, and routing to the correct backend based on the `profile` query parameter.

**Architecture:**

```text
Internet → ALB (HTTPS:443) → ECS Tasks (HTTP:80) → AgentCore Runtime (concierge / interview)
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0
3. **Docker** for building container images
4. **AgentCore Runtime** deployed for both concierge and interview agents with JWT authorization enabled
5. **ACM Certificate** for HTTPS on ALB
6. **VPC** with public subnets for ALB and private subnets for ECS tasks

## Terraform Module Sources

The `main.tf` uses a **repo-local relative path** pointing at `deployment/terraform/modules/` at the workspace root:

```hcl
module "execution_role" {
  source = "../../deployment/terraform/modules/iam"
  # ...
}
module "gateway" {
  source = "../../deployment/terraform/modules/ecs-fargate"
  # ...
}
```

This is the default, publishable configuration. `terraform init` works without any external package registry, SSH credentials, or authentication — the module source is a plain relative path into the same repo. If you want to fork a module, edit it under `deployment/terraform/modules/`; both this per-project deploy and the single-apply stack at `deployment/terraform/stacks/all/` pick up the change automatically.

## Deployment Steps

### Step 1: Create ECR Repository (One-Time Setup)

The ECR repository is managed separately from Terraform to persist across deployments.

```bash
cd gateway-container/deploy
./create-ecr-repository.sh
```

### Step 2: Create Security Groups (One-Time Setup)

Create dedicated security groups for the ALB and ECS tasks:

```bash
cd gateway-container/deploy
export VPC_ID=<your-vpc-id>
./create-security-groups.sh
```

This creates:

- **ALB Security Group**: Allows HTTPS (443) from internet (0.0.0.0/0)
- **ECS Security Group**: Allows HTTP (80) from ALB security group only

**Important:** Update `user-terraform.tfvars` with the security group IDs output by this script.

### Step 3: Build and Push Container Image

Build the NGINX container and push to ECR:

```bash
cd gateway-container

export AWS_REGION=<your-aws-region>
export AWS_ACCOUNT_ID=<your-aws-account-id>
export ECR_REPOSITORY=gateway-container
export DOCKER_PLATFORM=linux/amd64
export AWS_PROFILE=<your-aws-profile>

./scripts/docker_build_ecr.sh
./scripts/docker_push_ecr.sh
```

### Step 4: Configure Terraform Variables

Create `user-terraform.tfvars` from the sample:

```bash
cd gateway-container/deploy
cp terraform.tfvars.sample user-terraform.tfvars
```

Edit `user-terraform.tfvars` with your values:

```hcl
# AWS Configuration
aws_region     = "<your-aws-region>"
aws_account_id = "<your-aws-account-id>"
environment    = "<your-environment>"

# VPC and Networking
vpc_id             = "<your-vpc-id>"
subnet_ids         = ["<your-private-subnet-1>", "<your-private-subnet-2>"]
alb_subnets        = ["<your-public-subnet-1>", "<your-public-subnet-2>"]
security_group_ids = ["<your-ecs-security-group-id>"]
alb_security_group_ids = ["<your-alb-security-group-id>"]

# SSL/TLS Configuration
certificate_arn = "arn:aws:acm:<your-aws-region>:<your-aws-account-id>:certificate/<your-certificate-id>"

# Gateway Environment Variables
environment_variables = {
  CONCIERGE_AGENTCORE_ENDPOINT = "bedrock-agentcore.<your-aws-region>.amazonaws.com"
  CONCIERGE_AGENT_ARN          = "<your-url-encoded-concierge-runtime-arn>"
  INTERVIEW_AGENTCORE_ENDPOINT = "bedrock-agentcore.<your-aws-region>.amazonaws.com"
  INTERVIEW_AGENT_ARN          = "<your-url-encoded-interview-runtime-arn>"
}
```

**Note:** AgentCore ARNs must be URL-encoded (`:` → `%3A`, `/` → `%2F`).

### Step 5: Deploy with Terraform

```bash
cd gateway-container/deploy

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file=user-terraform.tfvars

# Apply the configuration
terraform apply -var-file=user-terraform.tfvars -auto-approve
```

### Step 6: Verify Deployment

After deployment completes, verify the service:

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster <your-cluster-name> \
  --services <your-service-name> \
  --profile <your-aws-profile> \
  --region <your-aws-region> \
  --query 'services[0].{status:status,runningCount:runningCount,desiredCount:desiredCount}'

# Test health check endpoint
curl -k https://<ALB_DNS_NAME>/health

# Expected response:
# {"status": "ok"}
```

The ALB DNS name is in the Terraform outputs:

```bash
terraform output alb_dns_name
```

## Updating the Deployment

### Update Container Image

```bash
cd gateway-container

# Build and push new image
./scripts/docker_build_ecr.sh
./scripts/docker_push_ecr.sh

# Force new ECS deployment
aws ecs update-service \
  --cluster <your-cluster-name> \
  --service <your-service-name> \
  --force-new-deployment \
  --profile <your-aws-profile> \
  --region <your-aws-region>
```

### Update Infrastructure

```bash
cd gateway-container/deploy

# Update user-terraform.tfvars with changes
# Then apply
terraform apply -var-file=user-terraform.tfvars -auto-approve
```

## Destroying the Deployment

```bash
cd gateway-container/deploy

# Destroy all resources (except ECR repository)
terraform destroy -var-file=user-terraform.tfvars -auto-approve
```

**Note:** The ECR repository is not managed by Terraform and must be deleted manually if needed:

```bash
aws ecr delete-repository \
  --repository-name gateway-container \
  --force \
  --profile <your-aws-profile> \
  --region <your-aws-region>
```

## Troubleshooting

### Tasks Not Starting

Check CloudWatch logs:

```bash
aws logs tail /ecs/concierge-gateway --follow --profile <your-aws-profile> --region <your-aws-region>
```

### Health Check Failing

1. Verify security groups allow traffic from ALB to ECS tasks on port 80
2. Check container logs for NGINX errors
3. Verify container is listening on port 80 (not 443)
4. Verify all 4 environment variables are set correctly

### Connection Refused

1. Verify AgentCore Runtime is deployed and accessible for both concierge and interview agents
2. Check AgentCore ARNs are URL-encoded correctly
3. Verify JWT authorization is enabled on AgentCore

### Profile Routing Issues

1. Verify `?profile=concierge` or `?profile=interview` is included in the WebSocket URL
2. Default profile (no parameter) routes to the concierge backend
3. Check both upstream endpoints are reachable from the ECS tasks

### Terraform module download 401/403/302

Default configuration uses a repo-local relative path (`../../deployment/terraform/modules/...`) that requires no authentication. If `terraform init` fails with a 401/403/302, check the `source = "..."` paths in `main.tf` haven't been accidentally pointed at an external registry.

## Security Notes

- **Container Port**: NGINX listens on HTTP port 80 internally
- **ALB Termination**: ALB terminates SSL and forwards to container on port 80
- **Network Isolation**: ECS tasks only accept traffic from ALB security group
- **No Public Access**: Container port 80 is not exposed to internet
- **JWT Injection**: Tokens are extracted from `?token=` query parameter and injected as `Authorization: Bearer` headers

## Files

| File | Description |
|------|-------------|
| `main.tf` | Main Terraform configuration (ECS Fargate + ALB via ecs-fargate module, IAM via iam module) |
| `variables.tf` | Variable definitions |
| `terraform.tfvars.sample` | Sample configuration template with placeholder values |
| `user-terraform.tfvars` | Your deployment values (gitignored) |
| `create-ecr-repository.sh` | Script to create ECR repository |
| `create-security-groups.sh` | Script to create ALB and ECS security groups |
| `README.md` | This file |
