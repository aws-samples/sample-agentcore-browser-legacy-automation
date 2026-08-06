# Bedrock AgentCore Runtime Terraform Module

This Terraform module creates and manages an AWS Bedrock AgentCore Agent Runtime with comprehensive VPC support, CloudWatch logging, and configuration options.

## Features

- **Complete AgentCore Runtime Configuration**: Supports all AWS Bedrock AgentCore runtime features
- **CloudWatch Logging**: Automatic creation of log groups for application, usage, and endpoint logs (addresses [GitHub issue #44898](https://github.com/hashicorp/terraform-provider-aws/issues/44898))
- **VPC Support**: Full VPC integration with subnet and security group configuration
- **JWT Authorization**: Optional custom JWT authorizer configuration
- **Lifecycle Management**: Configurable session timeouts and instance lifetime
- **Protocol Support**: HTTP, MCP, and A2A protocol configurations
- **Request Header Control**: Configurable HTTP header allowlist
- **Reference Implementation**: Comprehensive validation and error handling; a blueprint to adapt and harden

## Quick Start

### 1. Using the Deployment Script (Recommended)

The easiest way to deploy is using the provided deployment script with environment variables:

```bash
# Navigate to your project directory
cd /path/to/your-agentcore-container

# Configure environment variables in .env file
cp .env.sample .env
# Edit .env with your values

# Deploy using the script
./deploy-terraform.sh
```

### 2. Manual Terraform Deployment

```bash
cd deploy
terraform init
terraform plan -var-file="user_deployment.tfvars"
terraform apply -var-file="user_deployment.tfvars"
```

## Configuration

### Environment Variables (.env)

The deployment script reads configuration from a `.env` file:

```bash
# AWS Configuration
AWS_PROFILE=default
AWS_REGION=us-east-1
TERRAFORM_COMMAND=apply

# Runtime Configuration
AGENT_RUNTIME_NAME=my_agent_runtime_stage
CONTAINER_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-server:latest
ROLE_ARN=  # Leave empty to create new role

# JWT Authorization (optional)
JWT_DISCOVERY_URL=https://example.auth0.com/.well-known/openid-configuration
JWT_ALLOWED_AUDIENCE=gateway-api
JWT_ALLOWED_CLIENTS=client-id-1,client-id-2

# VPC Configuration
VPC_SUBNET_IDS=subnet-12345678,subnet-87654321
VPC_SECURITY_GROUP_IDS=sg-12345678

# Application Configuration (passed to container)
LOG_LEVEL=INFO
# ... other application environment variables
```

### Terraform Variables (.tfvars)

Alternatively, use Terraform variables directly:

```hcl
agent_runtime_name = "my_agent_runtime_stage"
container_uri      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-server:latest"
role_arn          = ""  # Empty to create new role

enable_custom_jwt_authorizer = true
jwt_discovery_url           = "https://example.auth0.com/.well-known/openid-configuration"
jwt_allowed_audience        = ["gateway-api"]
jwt_allowed_clients         = ["client-id-1", "client-id-2"]

network_mode             = "VPC"
vpc_subnet_ids          = ["subnet-12345678", "subnet-87654321"]
vpc_security_group_ids  = ["sg-12345678"]

# Log Delivery (optional, defaults to CWL with auto-created log groups)
enable_log_delivery       = true
enable_usage_log_delivery = true
enable_trace_delivery     = false
log_retention_days        = 30

# To send logs to S3 instead of CloudWatch:
# log_destination_type = "S3"
# log_destination_arn  = "arn:aws:s3:::my-runtime-logs-bucket"

environment_variables = {
  "LOG_LEVEL" = "INFO"
  # ... other environment variables
}
```

## Usage

### Basic Usage (Public Network)

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  agent_runtime_name = "my-mcp-server-dev"
  description        = "MCP server runtime for development"
  role_arn           = "arn:aws:iam::123456789012:role/bedrock-agentcore-role"
  container_uri      = "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-server:v1.0"

  network_mode = "PUBLIC"

  environment_variables = {
    LOG_LEVEL = "INFO"
    ENV       = "development"
  }

  tags = {
    Environment = "dev"
    Project     = "my-project"
  }
}
```

### VPC Configuration

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  agent_runtime_name = "my-mcp-server-prod"
  description        = "Production MCP server runtime"
  role_arn           = "arn:aws:iam::123456789012:role/bedrock-agentcore-role"
  container_uri      = "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-server:v2.0"

  # VPC Configuration
  network_mode             = "VPC"
  vpc_subnet_ids          = ["subnet-12345678", "subnet-87654321"]
  vpc_security_group_ids  = ["sg-12345678"]

  # Lifecycle Configuration
  idle_runtime_session_timeout = 3600   # 1 hour
  max_lifetime                 = 86400  # 24 hours

  environment_variables = {
    LOG_LEVEL = "INFO"
    ENV       = "production"
  }
}
```

### JWT Authorization

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  agent_runtime_name = "secure-mcp-server"
  role_arn           = "arn:aws:iam::123456789012:role/bedrock-agentcore-role"
  container_uri      = "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-server:latest"

  # JWT Authorization
  enable_custom_jwt_authorizer = true
  jwt_discovery_url           = "https://accounts.google.com/.well-known/openid-configuration"
  jwt_allowed_audience        = ["my-app", "mobile-app"]
  jwt_allowed_clients         = ["client-123", "client-456"]

  # Request Header Configuration
  request_header_allowlist = ["Authorization", "Content-Type", "X-Custom-Header"]
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 6.18.0 |

**Note**: AWS provider version 6.18.0+ is required for Bedrock AgentCore support. Earlier versions do not include the necessary resources.

## Providers

| Name | Version |
|------|---------|
| aws | >= 6.18.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| agent_runtime_name | Name of the Bedrock AgentCore runtime | `string` | n/a | yes |
| role_arn | ARN of the IAM role for the AgentCore runtime | `string` | n/a | yes |
| container_uri | ECR container URI for the agent runtime | `string` | n/a | yes |
| description | Description of the agent runtime | `string` | `""` | no |
| region | AWS region for the agent runtime | `string` | `""` | no |
| enable_custom_jwt_authorizer | Enable custom JWT authorizer | `bool` | `false` | no |
| jwt_discovery_url | JWT discovery URL (must end with .well-known/openid-configuration) | `string` | `""` | no |
| jwt_allowed_audience | List of allowed audiences for JWT authorizer | `list(string)` | `[]` | no |
| jwt_allowed_clients | List of allowed client IDs for JWT authorizer | `list(string)` | `[]` | no |
| network_mode | Network mode (PUBLIC or VPC) | `string` | `"PUBLIC"` | no |
| vpc_subnet_ids | List of VPC subnet IDs (required when network_mode is VPC) | `list(string)` | `[]` | no |
| vpc_security_group_ids | List of VPC security group IDs (required when network_mode is VPC) | `list(string)` | `[]` | no |
| server_protocol | Server protocol (HTTP, MCP, or A2A) | `string` | `"MCP"` | no |
| idle_runtime_session_timeout | Timeout in seconds for idle runtime sessions | `number` | `null` | no |
| max_lifetime | Maximum lifetime for the instance in seconds | `number` | `null` | no |
| request_header_allowlist | List of HTTP request headers allowed to be passed through | `list(string)` | `[]` | no |
| environment_variables | Environment variables for the agent runtime | `map(string)` | `{"LOG_LEVEL": "INFO", "ENV": "production"}` | no |
| log_retention_days | CloudWatch log retention in days (auto-created CWL groups only) | `number` | `7` | no |
| enable_log_delivery | Enable application log delivery | `bool` | `true` | no |
| log_destination_type | Application log destination: CWL, S3, FH | `string` | `"CWL"` | no |
| log_destination_arn | Custom application log destination ARN | `string` | `null` | no |
| log_output_format | Log format: json, plain, w3c, raw, parquet | `string` | `"json"` | no |
| enable_usage_log_delivery | Enable usage log delivery | `bool` | `true` | no |
| usage_log_destination_type | Usage log destination: CWL, S3, FH | `string` | `"CWL"` | no |
| usage_log_destination_arn | Custom usage log destination ARN | `string` | `null` | no |
| enable_trace_delivery | Enable X-Ray trace delivery | `bool` | `false` | no |
| tags | A map containing tags for the agent runtime resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| agent_runtime_arn | ARN of the Bedrock AgentCore runtime |
| agent_runtime_name | Name of the Bedrock AgentCore runtime |
| agent_runtime_id | Unique identifier of the Bedrock AgentCore runtime |
| agent_runtime_version | Version of the Bedrock AgentCore runtime |
| network_mode | Network mode of the agent runtime |
| workload_identity_details | Workload identity details for the agent runtime |
| workload_identity_arn | ARN of the workload identity |
| application_log_group_name | Name of the application log group |
| application_log_group_arn | ARN of the application log group |
| usage_log_group_name | Name of the usage log group |
| usage_log_group_arn | ARN of the usage log group |
| endpoint_log_group_name | Name of the endpoint log group |
| endpoint_log_group_arn | ARN of the endpoint log group |
| tags_all | A map of tags assigned to the resource |

## Validation Rules

- **agent_runtime_name**: Must start with a letter and contain only letters, numbers, and underscores (max 48 characters)
- **role_arn**: Must be a valid IAM role ARN format
- **container_uri**: Must be a valid ECR repository URI
- **jwt_discovery_url**: Must be a valid HTTPS URL ending with `.well-known/openid-configuration`
- **network_mode**: Must be either `PUBLIC` or `VPC`
- **server_protocol**: Must be `HTTP`, `MCP`, or `A2A`
- **environment_variables**: Variable names must be uppercase with underscores
- **VPC Configuration**: When `network_mode` is `VPC`, both `vpc_subnet_ids` and `vpc_security_group_ids` must be specified

## Log Delivery

The module supports configurable log delivery for application logs and usage logs, with optional X-Ray trace delivery. Logs can be sent to CloudWatch Logs, Amazon S3, or Amazon Data Firehose.

By default, both application and usage log delivery are enabled with auto-created CloudWatch log groups. Set `enable_log_delivery` or `enable_usage_log_delivery` to `false` to disable.

- **Application Logs**: Extraction/consolidation logs from the runtime
- **Usage Logs**: Data plane usage statistics
- **Endpoint Logs**: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT` (auto-created by AWS, always referenced)

### Default (CloudWatch Logs)

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  # ... other configuration ...

  enable_log_delivery       = true   # default
  enable_usage_log_delivery = true   # default
  log_retention_days        = 30
}
```

### Application Logs to S3, Usage Logs to CloudWatch

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  # ... other configuration ...

  enable_log_delivery  = true
  log_destination_type = "S3"
  log_destination_arn  = aws_s3_bucket.runtime_logs.arn
  log_output_format    = "json"

  enable_usage_log_delivery = true
  # usage defaults to CWL with auto-created log group
  log_retention_days = 14
}
```

### Logs to Amazon Data Firehose

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  # ... other configuration ...

  enable_log_delivery  = true
  log_destination_type = "FH"
  log_destination_arn  = aws_kinesis_firehose_delivery_stream.runtime_logs.arn

  enable_usage_log_delivery  = true
  usage_log_destination_type = "FH"
  usage_log_destination_arn  = aws_kinesis_firehose_delivery_stream.runtime_usage.arn
}
```

### With X-Ray Trace Delivery

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  # ... other configuration ...

  enable_log_delivery   = true
  enable_trace_delivery = true
  log_retention_days    = 30
}
```

### Disable All Log Delivery

```hcl
module "bedrock_agentcore_runtime" {
  source = "./bedrock-agentcore-runtime"

  # ... other configuration ...

  enable_log_delivery       = false
  enable_usage_log_delivery = false
}
```

## IAM Requirements

The IAM role specified in `role_arn` must have the following permissions:

### Required Permissions

**ECR Access:**

- `ecr:GetAuthorizationToken` (for authentication)
- `ecr:BatchGetImage` (to pull container images)
- `ecr:GetDownloadUrlForLayer` (to download image layers)

**CloudWatch Logs:**

- `logs:DescribeLogGroups` (to list log groups)
- `logs:DescribeLogStreams` (to list log streams)
- `logs:CreateLogGroup` (to create log groups)
- `logs:CreateLogStream` (to create log streams)
- `logs:PutLogEvents` (to write logs)

**X-Ray Tracing:**

- `xray:PutTraceSegments`
- `xray:PutTelemetryRecords`
- `xray:GetSamplingRules`
- `xray:GetSamplingTargets`

**CloudWatch Metrics:**

- `cloudwatch:PutMetricData` (scoped to `bedrock-agentcore` namespace)

**Bedrock AgentCore:**

- `bedrock-agentcore:GetWorkloadAccessToken`
- `bedrock-agentcore:GetWorkloadAccessTokenForJWT`
- `bedrock-agentcore:GetWorkloadAccessTokenForUserId`

**Bedrock Model Invocation:**

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

### Trust Policy

The IAM role must trust the `bedrock-agentcore.amazonaws.com` service:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Agent runtime name validation error**: Ensure the name starts with a letter and contains only letters, numbers, and underscores
2. **CREATE_FAILED status**: Check that the ECR repository exists and the container image is available
3. **VPC configuration errors**: Verify that subnets and security groups exist and are accessible
4. **IAM permission errors**: Ensure the role has all required permissions listed above
5. **Logs not appearing in CloudWatch**:
   - Verify the IAM role has CloudWatch Logs permissions
   - Check that log groups were created successfully
   - Ensure the runtime is actively processing requests
6. **Endpoint log group already exists error**: This is expected - AWS auto-creates the endpoint log group. The module uses a data source to reference it.

### Viewing Logs

After deployment, you can view logs in CloudWatch:

```bash
# Application logs
aws logs tail "/aws/vendedlogs/bedrock-agentcore/runtime/APPLICATION_LOGS/<runtime-id>" --follow

# Usage logs
aws logs tail "/aws/vendedlogs/bedrock-agentcore/runtime/USAGE_LOGS/<runtime-id>" --follow

# Endpoint logs
aws logs tail "/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT" --follow
```

Or use the outputs to get log group names:

```bash
terraform output application_log_group_name
terraform output usage_log_group_name
terraform output endpoint_log_group_name
```

### Deployment Script Issues

- Ensure `.env` file exists and contains required variables
- Check that `TERRAFORM_COMMAND` is set to `apply` or `destroy`
- Verify AWS credentials are configured correctly

## License

SPDX-License-Identifier: MIT-0. Part of the Browser Agent blog reference architecture.
