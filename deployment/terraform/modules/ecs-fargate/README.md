# ECS Fargate Terraform Module

A comprehensive reference Terraform module for deploying containers to Amazon ECS on AWS Fargate. This module supports 7 core AWS ECS invocation methods with standalone tasks as the default deployment pattern. It is part of a blueprint reference architecture — review and harden its defaults (encryption, logging retention, network exposure) before any production use.

## Features

- **Minimal Configuration**: Only 5 required variables for basic standalone task deployment
- **Additive Architecture**: Boolean flags enable additional components without breaking existing configurations
- **7 ECS Invocation Methods**: Supports all core ECS deployment patterns with pure Terraform resources
- **Load Balancer Support**: Application Load Balancer (ALB), Network Load Balancer (NLB), and Gateway Load Balancer (GLB)
- **Comprehensive Validation**: Input validation with clear error messages for all configuration parameters
- **Operational Building Blocks**: Built-in monitoring, logging, and security hooks intended as a blueprint to extend and harden
- **3-File Module Structure**: Separates resources, variables, and outputs per Terraform best practices
- **Explicit Configuration**: Required VPC configuration for services and load balancers (no default assumptions)

## Supported ECS Invocation Methods

1. **Standalone Tasks** (Default) - One-time or batch processing tasks with minimal configuration
2. **ECS Services** - Long-running containerized applications with auto-scaling and health checks
3. **Application Load Balanced Services** - HTTP/HTTPS web applications with ALB integration
4. **Network Load Balanced Services** - High-performance TCP/UDP applications with NLB integration
5. **Gateway Load Balanced Services** - Virtual network appliances with GLB integration
6. **Scheduled Tasks** - EventBridge-triggered tasks with cron/rate expressions
7. **Batch Processing** - AWS Batch integration for large-scale processing workloads

## Quick Start

### Minimal Standalone Task (5 Required Variables)

```hcl
module "ecs_task" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables only
  task_family        = "my-batch-job"
  container_name     = "processor"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:latest"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # Optional: Override defaults
  cpu    = 512
  memory = 1024

  tags = {
    Environment = "production"
    Application = "data-processing"
  }
}
```

### ECS Service with Application Load Balancer

```hcl
module "ecs_web_service" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables
  task_family        = "web-application"
  container_name     = "web-server"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app:v1.2.3"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # Service configuration
  enable_service  = true
  desired_count   = 3
  container_port  = 8080

  # Explicit VPC configuration (required for services)
  vpc_id             = "vpc-12345678"
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  security_group_ids = ["sg-12345678"]

  # Application Load Balancer
  enable_alb    = true
  alb_subnets   = ["subnet-12345678", "subnet-87654321"]
  enable_https  = true
  certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/12345678-1234-1234-1234-123456789012"

  # Resource configuration
  cpu    = 1024
  memory = 2048

  # Environment variables
  environment_variables = {
    NODE_ENV = "production"
    PORT     = "8080"
  }

  tags = {
    Environment = "production"
    Application = "web-service"
  }
}
```

### Scheduled Tasks with Multiple Schedules

```hcl
module "ecs_scheduled_tasks" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables
  task_family        = "scheduled-processor"
  container_name     = "batch-processor"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/batch-app:latest"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # Scheduled tasks configuration
  enable_scheduled_tasks = true
  eventbridge_role_arn   = "arn:aws:iam::123456789012:role/eventbridge-ecs-role"

  # Explicit VPC configuration (required for scheduled tasks)
  vpc_id             = "vpc-12345678"
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  security_group_ids = ["sg-12345678"]

  # Multiple schedules
  schedule_expressions = [
    {
      name                = "hourly-processing"
      schedule_expression = "rate(1 hour)"
      description         = "Process data every hour"
      enabled             = true
    },
    {
      name                = "daily-cleanup"
      schedule_expression = "cron(0 2 * * ? *)"
      description         = "Daily cleanup at 2 AM UTC"
      enabled             = true
    },
    {
      name                = "weekly-report"
      schedule_expression = "cron(0 8 ? * MON *)"
      description         = "Weekly report on Mondays at 8 AM UTC"
      enabled             = false
    }
  ]

  tags = {
    Environment = "production"
    Application = "scheduled-processing"
  }
}
```

### High-Performance Network Load Balancer

```hcl
module "ecs_nlb_service" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables
  task_family        = "tcp-service"
  container_name     = "tcp-server"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/tcp-app:latest"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # Service configuration
  enable_service  = true
  desired_count   = 5
  container_port  = 9090

  # Explicit VPC configuration
  vpc_id             = "vpc-12345678"
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  security_group_ids = ["sg-12345678"]

  # Network Load Balancer for high performance
  enable_nlb                           = true
  nlb_subnets                         = ["subnet-12345678", "subnet-87654321"]
  nlb_protocol                        = "TCP"
  nlb_target_port                     = 9090
  nlb_enable_cross_zone_load_balancing = true

  # High-performance configuration
  cpu    = 2048
  memory = 4096

  tags = {
    Environment = "production"
    Application = "high-performance-tcp"
  }
}
```

### Gateway Load Balancer for Security Appliances

```hcl
module "ecs_security_appliance" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables
  task_family        = "security-appliance"
  container_name     = "firewall"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/security-app:latest"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # Service configuration
  enable_service  = true
  desired_count   = 2
  container_port  = 6081

  # Explicit VPC configuration
  vpc_id             = "vpc-12345678"
  subnet_ids         = ["subnet-12345678", "subnet-87654321"]
  security_group_ids = ["sg-12345678"]

  # Gateway Load Balancer for virtual appliances
  enable_glb      = true
  glb_subnets     = ["subnet-12345678", "subnet-87654321"]
  glb_target_port = 6081

  # Security appliance configuration
  cpu    = 1024
  memory = 2048

  tags = {
    Environment = "production"
    Application = "security-appliance"
  }
}
```

### AWS Batch Integration

```hcl
module "ecs_batch_processing" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Required variables
  task_family        = "batch-job"
  container_name     = "batch-processor"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/batch-app:latest"
  task_role_arn      = "arn:aws:iam::123456789012:role/ecs-task-role"
  execution_role_arn = "arn:aws:iam::123456789012:role/ecs-execution-role"

  # AWS Batch integration
  enable_batch_processing         = true
  batch_job_queue_name           = "my-batch-queue"
  batch_job_definition_name      = "my-batch-job-definition"
  batch_compute_environment_name = "my-batch-compute-env"

  # Large-scale processing configuration
  cpu    = 4096
  memory = 8192

  tags = {
    Environment = "production"
    Application = "batch-processing"
  }
}
```

## Variable Reference

### Required Variables (Minimal Configuration - Only 5 Required)

| Variable | Type | Description | Validation Rules |
|----------|------|-------------|------------------|
| `task_family` | `string` | Task definition family name | 1-255 chars, start with alphanumeric, contain only alphanumeric, hyphens, underscores |
| `container_name` | `string` | Name of the container in task definition | 1-255 chars, start with alphanumeric, contain only alphanumeric, hyphens, underscores |
| `container_image` | `string` | Container image URI (ECR repository URL with tag) | Must be valid ECR URI format: `123456789012.dkr.ecr.region.amazonaws.com/repository:tag` |
| `task_role_arn` | `string` | ARN of the IAM role for ECS tasks | Must be valid IAM role ARN format: `arn:aws:iam::123456789012:role/role-name` |
| `execution_role_arn` | `string` | ARN of the IAM role for ECS task execution | Must be valid IAM role ARN format: `arn:aws:iam::123456789012:role/role-name` |

### Optional Configuration Variables

#### Cluster Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `cluster_name` | `string` | `""` | Name of the ECS cluster (auto-generated if not specified) | 1-255 chars, start with alphanumeric |
| `create_cluster` | `bool` | `true` | Create new ECS cluster or use existing | - |
| `existing_cluster_name` | `string` | `""` | Name of existing ECS cluster to use (required when create_cluster = false) | 1-255 chars, start with alphanumeric |

#### VPC Configuration (Required for Services/Load Balancers)

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `vpc_id` | `string` | `""` | VPC ID (required for services and load balancers) | Valid VPC ID format: `vpc-xxxxxxxxx` |
| `subnet_ids` | `list(string)` | `[]` | Subnet IDs (required for services and load balancers) | Valid subnet ID format: `subnet-xxxxxxxxx` |
| `security_group_ids` | `list(string)` | `[]` | Security group IDs (required for services and load balancers) | Valid security group ID format: `sg-xxxxxxxxx` |
| `assign_public_ip` | `bool` | `false` | Assign public IP to tasks | - |

#### Resource Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `cpu` | `number` | `256` | CPU units for the task | Must be one of: 256, 512, 1024, 2048, 4096 |
| `memory` | `number` | `512` | Memory in MiB for the task | Must be compatible with CPU (see Fargate requirements) |
| `container_port` | `number` | `0` | Port exposed by container (required for services and load balancers) | 0-65535 |

#### Container Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `environment_variables` | `map(string)` | `{}` | Environment variables for the container | - |
| `secrets` | `list(object)` | `[]` | Secrets from Parameter Store or Secrets Manager | Objects with `name` and `valueFrom` fields |

#### Logging Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `log_retention_days` | `number` | `7` | CloudWatch log retention in days | Valid CloudWatch retention values |
| `enable_container_insights` | `bool` | `true` | Enable CloudWatch Container Insights | - |
| `log_stream_prefix` | `string` | `"ecs"` | Prefix for CloudWatch log streams | 1-63 chars, start with alphanumeric |

#### Monitoring Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_cloudwatch_alarms` | `bool` | `true` | Enable CloudWatch alarms for service monitoring | - |
| `alarm_sns_topic_arn` | `string` | `""` | SNS topic ARN for CloudWatch alarm notifications | Valid SNS topic ARN format |
| `cpu_utilization_threshold` | `number` | `80` | CPU utilization threshold for alarms (percentage) | 0-100 |
| `memory_utilization_threshold` | `number` | `80` | Memory utilization threshold for alarms (percentage) | 0-100 |
| `enable_load_balancer_alarms` | `bool` | `true` | Enable CloudWatch alarms for load balancer monitoring | - |

#### Service Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_service` | `bool` | `false` | Enable ECS Service for long-running containers | - |
| `service_name` | `string` | `""` | Name of the ECS service (auto-generated if not specified) | 1-255 chars, start with alphanumeric |
| `desired_count` | `number` | `1` | Desired number of service tasks | 0-10000 |

#### Application Load Balancer Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_alb` | `bool` | `false` | Enable Application Load Balancer | - |
| `alb_internal` | `bool` | `false` | Create internal ALB | - |
| `alb_subnets` | `list(string)` | `[]` | Subnets for ALB (min 2 required) | Valid subnet IDs, minimum 2 subnets |
| `enable_https` | `bool` | `false` | Enable HTTPS listener (requires certificate_arn) | - |
| `certificate_arn` | `string` | `""` | SSL certificate ARN (required when enable_https = true) | Valid ACM certificate ARN format |
| `health_check_path` | `string` | `"/"` | Health check path for ALB target group | Must start with '/' |

#### Network Load Balancer Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_nlb` | `bool` | `false` | Enable Network Load Balancer for TCP/UDP traffic | - |
| `nlb_internal` | `bool` | `false` | Create internal NLB | - |
| `nlb_subnets` | `list(string)` | `[]` | Subnets for NLB (min 2 required) | Valid subnet IDs, minimum 2 subnets |
| `nlb_enable_cross_zone_load_balancing` | `bool` | `true` | Enable cross-zone load balancing for NLB | - |
| `nlb_target_port` | `number` | `80` | Target port for NLB | 1-65535 |
| `nlb_protocol` | `string` | `"TCP"` | Protocol for NLB | Must be TCP, UDP, TCP_UDP, or TLS |

#### Gateway Load Balancer Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_glb` | `bool` | `false` | Enable Gateway Load Balancer for virtual appliances | - |
| `glb_subnets` | `list(string)` | `[]` | Subnets for GLB (min 2 required) | Valid subnet IDs, minimum 2 subnets |
| `glb_target_port` | `number` | `6081` | Target port for GLB | 1-65535 |

#### Scheduling Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_scheduled_tasks` | `bool` | `false` | Enable EventBridge scheduled task execution | - |
| `eventbridge_role_arn` | `string` | `""` | IAM role ARN for EventBridge (required when enable_scheduled_tasks = true) | Valid IAM role ARN format |
| `schedule_expressions` | `list(object)` | `[]` | List of schedule expressions for task execution | Objects with `name`, `schedule_expression`, `description`, `enabled` fields |

#### Batch Processing Configuration

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `enable_batch_processing` | `bool` | `false` | Enable AWS Batch integration | - |
| `batch_job_queue_name` | `string` | `""` | AWS Batch job queue name (required when enable_batch_processing = true) | 1-128 chars, start with alphanumeric |
| `batch_job_definition_name` | `string` | `""` | AWS Batch job definition name (required when enable_batch_processing = true) | 1-128 chars, start with alphanumeric |
| `batch_compute_environment_name` | `string` | `""` | AWS Batch compute environment name (required when enable_batch_processing = true) | 1-128 chars, start with alphanumeric |

#### Tags

| Variable | Type | Default | Description | Validation Rules |
|----------|------|---------|-------------|------------------|
| `tags` | `map(string)` | `{}` | Tags to apply to all resources | - |

## Output Reference

All outputs use conditional expressions with `null` for disabled features.

### Core Outputs (Always Available)

| Output | Description | Type |
|--------|-------------|------|
| `cluster_id` | ID of the ECS cluster | `string` |
| `cluster_arn` | ARN of the ECS cluster | `string` |
| `task_definition_arn` | ARN of the task definition | `string` |
| `task_definition_family` | Family of the task definition | `string` |
| `task_definition_revision` | Revision of the task definition | `number` |
| `log_group_name` | Name of the CloudWatch log group | `string` |
| `log_group_arn` | ARN of the CloudWatch log group | `string` |
| `log_stream_prefix` | Log stream prefix used for CloudWatch logs | `string` |
| `log_retention_days` | Log retention period in days | `number` |

### Monitoring Outputs

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `cloudwatch_alarms_enabled` | Whether CloudWatch alarms are enabled | `bool` | Always |
| `ecs_cpu_alarm_arn` | ARN of the ECS CPU utilization alarm | `string` | `enable_service && enable_cloudwatch_alarms` |
| `ecs_memory_alarm_arn` | ARN of the ECS memory utilization alarm | `string` | `enable_service && enable_cloudwatch_alarms` |
| `ecs_task_count_alarm_arn` | ARN of the ECS running task count alarm | `string` | `enable_service && enable_cloudwatch_alarms` |
| `alb_healthy_hosts_alarm_arn` | ARN of the ALB healthy hosts alarm | `string` | `enable_alb && enable_load_balancer_alarms` |
| `alb_response_time_alarm_arn` | ARN of the ALB response time alarm | `string` | `enable_alb && enable_load_balancer_alarms` |
| `nlb_healthy_hosts_alarm_arn` | ARN of the NLB healthy hosts alarm | `string` | `enable_nlb && enable_load_balancer_alarms` |
| `glb_healthy_hosts_alarm_arn` | ARN of the GLB healthy hosts alarm | `string` | `enable_glb && enable_load_balancer_alarms` |
| `container_insights_enabled` | Whether Container Insights is enabled | `bool` | Always |
| `monitoring_configuration` | Summary of monitoring configuration | `object` | Always |

### Service Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `service_id` | ID of the ECS service | `string` | `enable_service` |
| `service_arn` | ARN of the ECS service | `string` | `enable_service` |
| `service_name` | Name of the ECS service | `string` | `enable_service` |

### Application Load Balancer Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `alb_arn` | ARN of the Application Load Balancer | `string` | `enable_alb` |
| `alb_dns_name` | DNS name of the Application Load Balancer | `string` | `enable_alb` |
| `alb_zone_id` | Zone ID of the Application Load Balancer | `string` | `enable_alb` |
| `alb_target_group_arn` | ARN of the ALB target group for integration | `string` | `enable_alb` |
| `alb_listener_arn` | ARN of the ALB HTTP listener | `string` | `enable_alb` |
| `alb_https_listener_arn` | ARN of the ALB HTTPS listener | `string` | `enable_alb && enable_https` |

### Network Load Balancer Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `nlb_arn` | ARN of the Network Load Balancer | `string` | `enable_nlb` |
| `nlb_dns_name` | DNS name of the Network Load Balancer | `string` | `enable_nlb` |
| `nlb_zone_id` | Zone ID of the Network Load Balancer | `string` | `enable_nlb` |
| `nlb_target_group_arn` | ARN of the NLB target group for integration | `string` | `enable_nlb` |
| `nlb_listener_arn` | ARN of the NLB listener | `string` | `enable_nlb` |

### Gateway Load Balancer Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `glb_arn` | ARN of the Gateway Load Balancer | `string` | `enable_glb` |
| `glb_dns_name` | DNS name of the Gateway Load Balancer | `string` | `enable_glb` |
| `glb_zone_id` | Zone ID of the Gateway Load Balancer | `string` | `enable_glb` |
| `glb_target_group_arn` | ARN of the GLB target group for integration | `string` | `enable_glb` |
| `glb_listener_arn` | ARN of the GLB listener | `string` | `enable_glb` |

### Scheduled Tasks Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `scheduled_task_rule_arns` | ARNs of the EventBridge rules for scheduled tasks | `map(string)` | `enable_scheduled_tasks` |
| `scheduled_task_rule_names` | Names of the EventBridge rules for scheduled tasks | `map(string)` | `enable_scheduled_tasks` |
| `scheduled_task_target_arns` | ARNs of the EventBridge targets for scheduled tasks | `map(string)` | `enable_scheduled_tasks` |
| `schedule_expressions` | Schedule expressions configured for the scheduled tasks | `map(object)` | `enable_scheduled_tasks` |

### Batch Processing Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `batch_job_definition_arn` | ARN of the Batch job definition | `string` | `enable_batch_processing` |
| `batch_job_definition_name` | Name of the Batch job definition | `string` | `enable_batch_processing` |
| `batch_job_definition_revision` | Revision of the Batch job definition | `number` | `enable_batch_processing` |
| `batch_job_queue_name` | Name of the Batch job queue (from input) | `string` | `enable_batch_processing` |
| `batch_compute_environment_name` | Name of the Batch compute environment (from input) | `string` | `enable_batch_processing` |

### Networking Outputs (Conditional)

| Output | Description | Type | Condition |
|--------|-------------|------|-----------|
| `vpc_id` | VPC ID used by the module | `string` | `vpc_id != ""` |
| `subnet_ids` | Subnet IDs used by the module | `list(string)` | `length(subnet_ids) > 0` |
| `security_group_ids` | Security group IDs used by the module | `list(string)` | `length(security_group_ids) > 0` |

### Metadata Outputs

| Output | Description | Type |
|--------|-------------|------|
| `deployment_pattern` | Deployment pattern used (standalone, service, scheduled) | `string` |
| `module_version` | Version of the ECS Fargate module | `string` |
| `aws_region` | AWS region where resources are deployed | `string` |
| `aws_account_id` | AWS account ID where resources are deployed | `string` |

## Validation Rules

The module includes comprehensive input validation with clear error messages:

### CPU/Memory Compatibility (Fargate Requirements)

| CPU (vCPU) | Memory Range (MiB) | Common Values |
|------------|-------------------|---------------|
| 256 (0.25) | 512 - 2048 | 512, 1024, 2048 |
| 512 (0.5) | 1024 - 4096 | 1024, 2048, 3072, 4096 |
| 1024 (1) | 2048 - 8192 | 2048, 3072, 4096, 5120, 6144, 7168, 8192 |
| 2048 (2) | 4096 - 16384 | 4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384 |
| 4096 (4) | 8192 - 30720 | 8192, 9216, 10240, ..., 30720 (increments of 1024) |

### VPC Configuration Requirements

- **Services and Load Balancers**: Require explicit `vpc_id`, `subnet_ids`, and `security_group_ids`
- **Standalone Tasks**: VPC configuration is optional (uses Fargate default networking if not provided)
- **Load Balancer Subnets**: Must specify at least 2 subnets in different availability zones
- **Subnet Consistency**: All load balancer subnets must be included in the main `subnet_ids` list
- **Public IP Assignment**: Use `assign_public_ip = true` for tasks in public subnets without NAT gateway

### Role and Permission Requirements

- **Task Role**: IAM role for the ECS task itself (application permissions)
- **Execution Role**: IAM role for ECS to pull images and write logs (must include `AmazonECSTaskExecutionRolePolicy`)
- **EventBridge Role**: Required when `enable_scheduled_tasks = true` (must have ECS task execution permissions)
- **Certificate ARN**: Required when `enable_https = true` (must be a valid ACM certificate)

### Naming and Format Validation

- **Resource Names**: 1-255 characters, start with alphanumeric, contain only alphanumeric, hyphens, underscores
- **ECR Image URI**: Must be valid ECR format: `123456789012.dkr.ecr.region.amazonaws.com/repository:tag`
- **ARN Formats**: All ARNs validated for proper AWS ARN format
- **AWS Resource IDs**: VPC, subnet, and security group IDs validated for proper AWS format

### Cross-Variable Validation

- **Container Port**: Required when enabling services or load balancers (`container_port > 0`)
- **Load Balancer Subnets**: Required when enabling respective load balancers
- **Schedule Expressions**: Must be valid `rate()` or `cron()` expressions
- **Batch Resources**: All three Batch variables required when `enable_batch_processing = true`

## Best Practices

### Security Best Practices

#### IAM Roles and Permissions

- **Least Privilege**: Grant only the minimum permissions required for each role
- **Separate Roles**: Use different task roles for different applications
- **Execution Role**: Always include `AmazonECSTaskExecutionRolePolicy` for the execution role
- **Custom Policies**: Create custom policies for specific application needs

```hcl
# Example task role with minimal permissions
data "aws_iam_policy_document" "task_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = ["arn:aws:s3:::my-app-bucket/*"]
  }
}
```

#### Network Security

- **Explicit VPC Configuration**: Always specify VPC, subnets, and security groups for production
- **Security Groups**: Use specific security group rules instead of allowing all traffic
- **Private Subnets**: Deploy tasks in private subnets with NAT gateway for internet access
- **Encryption**: Enable encryption in transit and at rest for sensitive data

```hcl
# Example security group for web application
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.task_family}-ecs-tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # Only from ALB
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # HTTPS outbound only
  }
}
```

#### Secrets Management

- **AWS Secrets Manager**: Use for database passwords and API keys
- **Parameter Store**: Use for configuration values
- **Environment Variables**: Avoid sensitive data in environment variables

```hcl
# Example secrets configuration
secrets = [
  {
    name      = "DATABASE_PASSWORD"
    valueFrom = "arn:aws:secretsmanager:us-west-2:123456789012:secret:db-password-AbCdEf"
  },
  {
    name      = "API_KEY"
    valueFrom = "arn:aws:ssm:us-west-2:123456789012:parameter/app/api-key"
  }
]
```

### Performance Best Practices

#### Resource Sizing

- **Right-sizing**: Start with smaller resources and scale up based on monitoring
- **CPU-bound vs Memory-bound**: Choose CPU/memory ratios based on application characteristics
- **Monitoring**: Use CloudWatch Container Insights to understand resource usage patterns

```hcl
# Example resource configuration for different workload types

# CPU-intensive workload
cpu    = 2048
memory = 4096

# Memory-intensive workload
cpu    = 1024
memory = 8192

# Balanced workload
cpu    = 1024
memory = 2048
```

#### Load Balancer Selection

- **ALB**: Use for HTTP/HTTPS applications with advanced routing needs
- **NLB**: Use for high-performance TCP/UDP applications or when static IPs are needed
- **GLB**: Use for virtual network appliances and security devices

```hcl
# High-performance configuration
enable_nlb                           = true
nlb_enable_cross_zone_load_balancing = true
nlb_protocol                        = "TCP"
```

#### Health Checks

- **Appropriate Timeouts**: Set realistic health check timeouts
- **Health Check Endpoints**: Implement lightweight health check endpoints
- **Graceful Shutdown**: Handle SIGTERM signals properly for graceful shutdowns

```hcl
# Optimized health check configuration
health_check_path                = "/health"
# Health check configuration is handled automatically by the module
```

### Cost Optimization Best Practices

#### Deployment Pattern Selection

- **Standalone Tasks**: Use for batch jobs and one-time processing to avoid idle costs
- **Services**: Use only for applications that need to run continuously
- **Scheduled Tasks**: Use for periodic processing instead of always-running services

```hcl
# Cost-effective batch processing
module "batch_processor" {
  source = "./deployment/terraform/modules/ecs-fargate"

  # Minimal configuration for batch job
  task_family        = "batch-processor"
  container_name     = "processor"
  container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/batch-app:latest"
  task_role_arn      = aws_iam_role.task_role.arn
  execution_role_arn = aws_iam_role.execution_role.arn

  # No service - run on-demand only
  enable_service = false

  # Optimize for cost
  cpu    = 256
  memory = 512
}
```

#### Resource Optimization

- **Log Retention**: Set appropriate log retention periods
- **Container Images**: Use smaller, optimized container images
- **Spot Instances**: Use Spot instances for Batch workloads when possible

```hcl
# Cost-optimized logging
log_retention_days = 7  # Reduce from default for non-critical applications

# For Batch workloads, configure compute environment with Spot instances
# (This is done outside the module in your Batch configuration)
```

### Operational Excellence Best Practices

#### Monitoring and Observability

- **Container Insights**: Enable for detailed container metrics
- **CloudWatch Alarms**: Set up proactive alerting
- **Structured Logging**: Use structured logging in your applications
- **Distributed Tracing**: Implement tracing for complex applications

```hcl
# Comprehensive monitoring setup
enable_container_insights     = true
enable_cloudwatch_alarms     = true
enable_load_balancer_alarms  = true
alarm_sns_topic_arn         = aws_sns_topic.alerts.arn

# Appropriate thresholds
cpu_utilization_threshold    = 70
memory_utilization_threshold = 80
```

#### Tagging Strategy

- **Consistent Tagging**: Use consistent tags across all resources
- **Cost Allocation**: Include cost center and project tags
- **Environment**: Always tag with environment (dev, staging, prod)
- **Automation**: Use tags for automation and resource management

```hcl
# Comprehensive tagging strategy
tags = {
  Environment   = "production"
  Application   = "web-service"
  Team          = "platform"
  CostCenter    = "engineering"
  Project       = "customer-portal"
  ManagedBy     = "terraform"
  BackupPolicy  = "daily"
  Compliance    = "pci-dss"
}
```

#### Deployment Practices

- **Infrastructure as Code**: Always use Terraform for deployments
- **Version Control**: Store all Terraform configurations in version control
- **Environment Separation**: Use separate AWS accounts or regions for different environments
- **Automated Testing**: Test infrastructure changes in non-production environments first

```hcl
# Environment-specific configuration
locals {
  environment_config = {
    dev = {
      cpu           = 256
      memory        = 512
      desired_count = 1
      log_retention = 3
    }
    staging = {
      cpu           = 512
      memory        = 1024
      desired_count = 2
      log_retention = 7
    }
    production = {
      cpu           = 1024
      memory        = 2048
      desired_count = 3
      log_retention = 30
    }
  }
}

# Use environment-specific values
cpu               = local.environment_config[var.environment].cpu
memory            = local.environment_config[var.environment].memory
desired_count     = local.environment_config[var.environment].desired_count
log_retention_days = local.environment_config[var.environment].log_retention
```

#### Disaster Recovery

- **Multi-AZ Deployment**: Always deploy across multiple availability zones
- **Backup Strategy**: Implement appropriate backup strategies for stateful components
- **Recovery Testing**: Regularly test disaster recovery procedures
- **Documentation**: Maintain up-to-date runbooks and procedures

```hcl
# Multi-AZ deployment
subnet_ids = [
  "subnet-12345678",  # us-west-2a
  "subnet-87654321",  # us-west-2b
  "subnet-11223344"   # us-west-2c
]

alb_subnets = [
  "subnet-12345678",  # us-west-2a
  "subnet-87654321"   # us-west-2b
]
```

### Development and Testing Best Practices

#### Local Development

- **Container Testing**: Test containers locally before deploying
- **Environment Parity**: Keep development and production environments similar
- **Configuration Management**: Use environment-specific configuration files

#### CI/CD Integration

- **Automated Testing**: Include infrastructure testing in CI/CD pipelines
- **Gradual Rollouts**: Use blue-green or canary deployments for production changes
- **Rollback Strategy**: Always have a rollback plan for deployments

#### Documentation

- **README Files**: Maintain comprehensive README files for each module
- **Architecture Diagrams**: Create and maintain architecture diagrams
- **Runbooks**: Document operational procedures and troubleshooting steps
- **Change Logs**: Maintain change logs for infrastructure modifications

## Troubleshooting Guide

### Common Validation Errors

#### VPC Configuration Errors

**Error**: `vpc_id, subnet_ids, and security_group_ids are required when enabling services, load balancers, or scheduled tasks`

**Cause**: Services, load balancers, and scheduled tasks require explicit VPC configuration

**Solution**:

```hcl
# Add explicit VPC configuration
vpc_id             = "vpc-12345678"
subnet_ids         = ["subnet-12345678", "subnet-87654321"]
security_group_ids = ["sg-12345678"]
```

**Error**: `ALB/NLB/GLB requires at least 2 subnets in different availability zones`

**Cause**: Load balancers need redundancy across multiple AZs

**Solution**:

```hcl
# Ensure subnets are in different AZs
alb_subnets = ["subnet-12345678", "subnet-87654321"]  # Different AZs
```

#### Container Configuration Errors

**Error**: `container_port is required when enable_service, enable_alb, enable_nlb, or enable_glb is true`

**Cause**: Services and load balancers need to know which port to route traffic to

**Solution**:

```hcl
# Specify the port your container exposes
container_port = 8080
```

**Error**: `Container image must be a valid ECR repository URI`

**Cause**: Invalid ECR image URI format

**Solution**:

```hcl
# Use proper ECR URI format
container_image = "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0"
```

#### Resource Configuration Errors

**Error**: `CPU and memory combination is not valid for Fargate`

**Cause**: Invalid CPU/memory combination for AWS Fargate

**Solution**: Use valid combinations from the table above:

```hcl
# Valid combinations
cpu    = 512
memory = 1024

# Or
cpu    = 1024
memory = 2048
```

**Error**: `Task family must be 1-255 characters, start with alphanumeric`

**Cause**: Invalid task family name format

**Solution**:

```hcl
# Use valid naming convention
task_family = "my-application-task"  # Good
task_family = "-invalid-name"       # Bad - starts with hyphen
```

#### Role and Permission Errors

**Error**: `EventBridge role ARN is required when enable_scheduled_tasks = true`

**Cause**: Scheduled tasks need an IAM role for EventBridge to execute ECS tasks

**Solution**:

```hcl
enable_scheduled_tasks = true
eventbridge_role_arn   = "arn:aws:iam::123456789012:role/eventbridge-ecs-role"
```

**Error**: `Certificate ARN is required when enable_https = true`

**Cause**: HTTPS listeners need an SSL certificate

**Solution**:

```hcl
enable_https    = true
certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/12345678-1234-1234-1234-123456789012"
```

### Runtime Issues

#### Task Startup Problems

**Issue**: Tasks fail to start or immediately stop

**Debug Steps**:

1. Check CloudWatch logs:

   ```bash
   aws logs describe-log-groups --log-group-name-prefix "/ecs/"
   aws logs get-log-events --log-group-name "/ecs/my-task-family" --log-stream-name "ecs/container-name/task-id"
   ```

2. Verify IAM permissions:

   ```bash
   # Check if execution role can pull images
   aws sts assume-role --role-arn "arn:aws:iam::123456789012:role/ecs-execution-role" --role-session-name "test"

   # Check ECR permissions
   aws ecr describe-repositories --repository-names my-app
   ```

3. Test container locally:

   ```bash
   # Pull and run the same image locally
   docker pull 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:latest
   docker run --rm 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:latest
   ```

#### Network Connectivity Issues

**Issue**: Tasks can't reach external services or load balancer health checks fail

**Debug Steps**:

1. Check security group rules:

   ```bash
   aws ec2 describe-security-groups --group-ids sg-12345678
   ```

2. Verify subnet routing:

   ```bash
   aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=subnet-12345678"
   ```

3. Test connectivity from within the task:

   ```bash
   # Enable ECS Exec for debugging
   aws ecs execute-command --cluster my-cluster --task task-id --container container-name --interactive --command "/bin/bash"
   ```

#### Load Balancer Issues

**Issue**: Load balancer health checks failing

**Debug Steps**:

1. Check target group health:

   ```bash
   aws elbv2 describe-target-health --target-group-arn "arn:aws:elasticloadbalancing:..."
   ```

2. Verify health check configuration:

   ```bash
   aws elbv2 describe-target-groups --target-group-arns "arn:aws:elasticloadbalancing:..."
   ```

3. Test health check endpoint:

   ```bash
   # From within the container or VPC
   curl -v http://container-ip:container-port/health-check-path
   ```

### Performance Issues

#### High CPU/Memory Utilization

**Issue**: Tasks consuming too many resources

**Solutions**:

1. Increase CPU/memory allocation:

   ```hcl
   cpu    = 1024  # Increase from 512
   memory = 2048  # Increase from 1024
   ```

2. Enable CloudWatch alarms for monitoring:

   ```hcl
   enable_cloudwatch_alarms = true
   cpu_utilization_threshold = 70    # Lower threshold
   memory_utilization_threshold = 70 # Lower threshold
   ```

#### Slow Task Startup

**Issue**: Tasks take too long to start

**Solutions**:

1. Optimize container image:
   - Use smaller base images
   - Minimize layers
   - Use multi-stage builds

2. Pre-pull images to reduce cold start:

   ```bash
   # Use ECS-optimized AMIs with image pre-pulling
   ```

### Monitoring and Debugging

#### Enable Detailed Monitoring

```hcl
# Enable comprehensive monitoring
enable_container_insights     = true
enable_cloudwatch_alarms     = true
enable_load_balancer_alarms  = true
alarm_sns_topic_arn         = "arn:aws:sns:us-west-2:123456789012:alerts"
```

#### Useful AWS CLI Commands

```bash
# List ECS clusters
aws ecs list-clusters

# Describe ECS service
aws ecs describe-services --cluster my-cluster --services my-service

# List running tasks
aws ecs list-tasks --cluster my-cluster --service-name my-service

# Describe task definition
aws ecs describe-task-definition --task-definition my-task-family:1

# Check CloudWatch logs
aws logs describe-log-streams --log-group-name "/ecs/my-task-family"

# Monitor CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=my-service Name=ClusterName,Value=my-cluster \
  --start-time 2023-01-01T00:00:00Z \
  --end-time 2023-01-01T01:00:00Z \
  --period 300 \
  --statistics Average
```

### Getting Help

1. **AWS Documentation**: [ECS Developer Guide](https://docs.aws.amazon.com/ecs/)
2. **Terraform AWS Provider**: [ECS Resources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_service)
3. **AWS Support**: Use AWS Support for service-specific issues

## Requirements

- Terraform >= 1.0
- AWS Provider >= 5.0
- Valid AWS credentials with appropriate permissions

## License

SPDX-License-Identifier: MIT-0. Part of the Browser Agent blog reference architecture.

## Contributing

Follow standard Terraform module contribution practices: include appropriate tests and documentation updates for all changes.
