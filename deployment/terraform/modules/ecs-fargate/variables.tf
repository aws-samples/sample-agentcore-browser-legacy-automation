# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ECS Fargate Terraform Module - Variable Definitions
# Comprehensive input validation following repo standards

# ============================================================================
# REQUIRED VARIABLES (Minimal Configuration - Only 5 Required)
# ============================================================================

variable "task_family" {
  type        = string
  description = "Task definition family name"

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,254}$", var.task_family))
    error_message = "Task family must be 1-255 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "container_name" {
  type        = string
  description = "Name of the container in task definition"

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,254}$", var.container_name))
    error_message = "Container name must be 1-255 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "container_image" {
  type        = string
  description = "Container image URI (ECR repository URL with tag)"

  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/.+", var.container_image))
    error_message = "Container image must be a valid ECR repository URI format: 123456789012.dkr.ecr.region.amazonaws.com/repository:tag"
  }
}

variable "task_role_arn" {
  type        = string
  description = "ARN of the IAM role for ECS tasks"

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.task_role_arn))
    error_message = "Task role ARN must be a valid IAM role ARN format: arn:aws:iam::123456789012:role/role-name"
  }
}

variable "execution_role_arn" {
  type        = string
  description = "ARN of the IAM role for ECS task execution"

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.execution_role_arn))
    error_message = "Execution role ARN must be a valid IAM role ARN format: arn:aws:iam::123456789012:role/role-name"
  }
}

# ============================================================================
# CLUSTER CONFIGURATION
# ============================================================================

variable "cluster_name" {
  type        = string
  description = "Name of the ECS cluster (auto-generated if not specified)"
  default     = ""

  validation {
    condition     = var.cluster_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,254}$", var.cluster_name))
    error_message = "Cluster name must be 1-255 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "create_cluster" {
  type        = bool
  description = "Create new ECS cluster or use existing"
  default     = true
}

variable "existing_cluster_name" {
  type        = string
  description = "Name of existing ECS cluster to use (required when create_cluster = false)"
  default     = ""

  validation {
    condition     = var.existing_cluster_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,254}$", var.existing_cluster_name))
    error_message = "Existing cluster name must be 1-255 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

# ============================================================================
# VPC CONFIGURATION (Explicit Configuration Required for Services/Load Balancers)
# ============================================================================

variable "vpc_id" {
  type        = string
  description = "VPC ID (required when enable_service, enable_alb, enable_nlb, or enable_glb is true)"
  default     = ""

  validation {
    condition     = var.vpc_id == "" || can(regex("^vpc-[a-z0-9]{8,17}$", var.vpc_id))
    error_message = "VPC ID must be a valid VPC ID format: vpc-xxxxxxxxx"
  }
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs (required when enable_service, enable_alb, enable_nlb, or enable_glb is true)"
  default     = []

  validation {
    condition = alltrue([
      for subnet_id in var.subnet_ids : can(regex("^subnet-[a-z0-9]{8,17}$", subnet_id))
    ])
    error_message = "All subnet IDs must be valid subnet ID format: subnet-xxxxxxxxx"
  }
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security group IDs (required when enable_service, enable_alb, enable_nlb, or enable_glb is true)"
  default     = []

  validation {
    condition = alltrue([
      for sg_id in var.security_group_ids : can(regex("^sg-[a-z0-9]{8,17}$", sg_id))
    ])
    error_message = "All security group IDs must be valid security group ID format: sg-xxxxxxxxx"
  }
}

variable "assign_public_ip" {
  type        = bool
  description = "Assign public IP to tasks"
  default     = false
}

# ============================================================================
# RESOURCE CONFIGURATION
# ============================================================================

variable "cpu" {
  type        = number
  description = "CPU units for the task (256, 512, 1024, 2048, 4096)"
  default     = 256

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.cpu)
    error_message = "CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "memory" {
  type        = number
  description = "Memory in MiB for the task"
  default     = 512

  # CPU/Memory compatibility validation for Fargate
  validation {
    condition = (
      (var.cpu == 256 && var.memory >= 512 && var.memory <= 2048) ||
      (var.cpu == 512 && var.memory >= 1024 && var.memory <= 4096) ||
      (var.cpu == 1024 && var.memory >= 2048 && var.memory <= 8192) ||
      (var.cpu == 2048 && var.memory >= 4096 && var.memory <= 16384) ||
      (var.cpu == 4096 && var.memory >= 8192 && var.memory <= 30720)
    )
    error_message = "CPU and memory combination is not valid for Fargate. See AWS documentation for valid combinations."
  }
}

variable "container_port" {
  type        = number
  description = "Port exposed by the container (required for services and load balancers)"
  default     = 0

  validation {
    condition     = var.container_port >= 0 && var.container_port <= 65535
    error_message = "Container port must be between 0 and 65535."
  }
}

# ============================================================================
# CONTAINER CONFIGURATION
# ============================================================================

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables for the container"
  default     = {}
}

variable "secrets" {
  type = list(object({
    name      = string
    valueFrom = string
  }))
  description = "Secrets from Parameter Store or Secrets Manager"
  default     = []
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days. Defaults to 365 (1 year) to satisfy log-retention baselines; override for shorter dev retention if desired."
  default     = 365

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch log retention value."
  }
}

variable "enable_container_insights" {
  type        = bool
  description = "Enable CloudWatch Container Insights"
  default     = true
}

variable "log_stream_prefix" {
  type        = string
  description = "Prefix for CloudWatch log streams"
  default     = "ecs"

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,62}$", var.log_stream_prefix))
    error_message = "Log stream prefix must be 1-63 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

# ============================================================================
# MONITORING AND ALARMS CONFIGURATION
# ============================================================================

variable "enable_cloudwatch_alarms" {
  type        = bool
  description = "Enable CloudWatch alarms for service monitoring"
  default     = true
}

variable "alarm_sns_topic_arn" {
  type        = string
  description = "SNS topic ARN for CloudWatch alarm notifications (optional)"
  default     = ""

  validation {
    condition     = var.alarm_sns_topic_arn == "" || can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+", var.alarm_sns_topic_arn))
    error_message = "SNS topic ARN must be a valid SNS topic ARN format."
  }
}

variable "cpu_utilization_threshold" {
  type        = number
  description = "CPU utilization threshold for CloudWatch alarms (percentage)"
  default     = 80

  validation {
    condition     = var.cpu_utilization_threshold >= 0 && var.cpu_utilization_threshold <= 100
    error_message = "CPU utilization threshold must be between 0 and 100."
  }
}

variable "memory_utilization_threshold" {
  type        = number
  description = "Memory utilization threshold for CloudWatch alarms (percentage)"
  default     = 80

  validation {
    condition     = var.memory_utilization_threshold >= 0 && var.memory_utilization_threshold <= 100
    error_message = "Memory utilization threshold must be between 0 and 100."
  }
}

variable "enable_load_balancer_alarms" {
  type        = bool
  description = "Enable CloudWatch alarms for load balancer monitoring"
  default     = true
}

# ============================================================================
# SERVICE PATTERN VARIABLES
# ============================================================================

variable "enable_service" {
  type        = bool
  description = "Enable ECS Service for long-running containers"
  default     = false
}

variable "service_name" {
  type        = string
  description = "Name of the ECS service (auto-generated if not specified)"
  default     = ""

  validation {
    condition     = var.service_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,254}$", var.service_name))
    error_message = "Service name must be 1-255 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "desired_count" {
  type        = number
  description = "Desired number of service tasks"
  default     = 1

  validation {
    condition     = var.desired_count >= 0 && var.desired_count <= 10000
    error_message = "Desired count must be between 0 and 10000."
  }
}

# ============================================================================
# APPLICATION LOAD BALANCER VARIABLES
# ============================================================================

variable "enable_alb" {
  type        = bool
  description = "Enable Application Load Balancer"
  default     = false
}

variable "alb_internal" {
  type        = bool
  description = "Create internal ALB"
  default     = false
}

variable "alb_subnets" {
  type        = list(string)
  description = "Subnets for ALB (required if enable_alb = true, must be at least 2)"
  default     = []

  validation {
    condition = alltrue([
      for subnet_id in var.alb_subnets : can(regex("^subnet-[a-z0-9]{8,17}$", subnet_id))
    ])
    error_message = "All ALB subnet IDs must be valid subnet ID format: subnet-xxxxxxxxx"
  }

  validation {
    condition     = length(var.alb_subnets) == 0 || length(var.alb_subnets) >= 2
    error_message = "ALB requires at least 2 subnets in different availability zones when alb_subnets is specified."
  }
}

variable "alb_security_group_ids" {
  type        = list(string)
  description = "Security group IDs for ALB (required when enable_alb is true, separate from ECS task security groups)"
  default     = []

  validation {
    condition = alltrue([
      for sg_id in var.alb_security_group_ids : can(regex("^sg-[a-z0-9]{8,17}$", sg_id))
    ])
    error_message = "All ALB security group IDs must be valid security group ID format: sg-xxxxxxxxx"
  }
}

variable "enable_https" {
  type        = bool
  description = "Enable HTTPS listener (requires certificate_arn when true)"
  default     = false
}

variable "certificate_arn" {
  type        = string
  description = "SSL certificate ARN (required when enable_https = true)"
  default     = ""

  validation {
    condition     = var.certificate_arn == "" || can(regex("^arn:aws:acm:[a-z0-9-]+:[0-9]{12}:certificate/.+", var.certificate_arn))
    error_message = "Certificate ARN must be a valid ACM certificate ARN format."
  }
}

variable "health_check_path" {
  type        = string
  description = "Health check path for ALB target group"
  default     = "/"

  validation {
    condition     = can(regex("^/.*", var.health_check_path))
    error_message = "Health check path must start with '/'."
  }
}

# ============================================================================
# NETWORK LOAD BALANCER VARIABLES
# ============================================================================

variable "enable_nlb" {
  type        = bool
  description = "Enable Network Load Balancer for TCP/UDP traffic"
  default     = false
}

variable "nlb_internal" {
  type        = bool
  description = "Create internal NLB"
  default     = false
}

variable "nlb_subnets" {
  type        = list(string)
  description = "Subnets for NLB (required if enable_nlb = true, must be at least 2)"
  default     = []

  validation {
    condition = alltrue([
      for subnet_id in var.nlb_subnets : can(regex("^subnet-[a-z0-9]{8,17}$", subnet_id))
    ])
    error_message = "All NLB subnet IDs must be valid subnet ID format: subnet-xxxxxxxxx"
  }

  validation {
    condition     = length(var.nlb_subnets) == 0 || length(var.nlb_subnets) >= 2
    error_message = "NLB requires at least 2 subnets in different availability zones when nlb_subnets is specified."
  }
}

variable "nlb_enable_cross_zone_load_balancing" {
  type        = bool
  description = "Enable cross-zone load balancing for NLB"
  default     = true
}

variable "nlb_target_port" {
  type        = number
  description = "Target port for NLB"
  default     = 80

  validation {
    condition     = var.nlb_target_port >= 1 && var.nlb_target_port <= 65535
    error_message = "NLB target port must be between 1 and 65535."
  }
}

variable "nlb_protocol" {
  type        = string
  description = "Protocol for NLB (TCP, UDP, TCP_UDP, TLS)"
  default     = "TCP"

  validation {
    condition     = contains(["TCP", "UDP", "TCP_UDP", "TLS"], var.nlb_protocol)
    error_message = "NLB protocol must be TCP, UDP, TCP_UDP, or TLS."
  }
}

# ============================================================================
# GATEWAY LOAD BALANCER VARIABLES
# ============================================================================

variable "enable_glb" {
  type        = bool
  description = "Enable Gateway Load Balancer for virtual appliances"
  default     = false
}

variable "glb_subnets" {
  type        = list(string)
  description = "Subnets for GLB (required if enable_glb = true, must be at least 2)"
  default     = []

  validation {
    condition = alltrue([
      for subnet_id in var.glb_subnets : can(regex("^subnet-[a-z0-9]{8,17}$", subnet_id))
    ])
    error_message = "All GLB subnet IDs must be valid subnet ID format: subnet-xxxxxxxxx"
  }

  validation {
    condition     = length(var.glb_subnets) == 0 || length(var.glb_subnets) >= 2
    error_message = "GLB requires at least 2 subnets in different availability zones when glb_subnets is specified."
  }
}

variable "glb_target_port" {
  type        = number
  description = "Target port for GLB"
  default     = 6081

  validation {
    condition     = var.glb_target_port >= 1 && var.glb_target_port <= 65535
    error_message = "GLB target port must be between 1 and 65535."
  }
}

# ============================================================================
# SCHEDULING VARIABLES
# ============================================================================

variable "enable_scheduled_tasks" {
  type        = bool
  description = "Enable EventBridge scheduled task execution"
  default     = false
}

variable "eventbridge_role_arn" {
  type        = string
  description = "IAM role ARN for EventBridge to execute ECS tasks (required when enable_scheduled_tasks = true)"
  default     = ""

  validation {
    condition     = var.eventbridge_role_arn == "" || can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.eventbridge_role_arn))
    error_message = "EventBridge role ARN must be a valid IAM role ARN format."
  }
}

variable "schedule_expressions" {
  type = list(object({
    name                = string
    schedule_expression = string
    description         = string
    enabled             = bool
  }))
  description = "List of schedule expressions for task execution"
  default     = []

  validation {
    condition = alltrue([
      for schedule in var.schedule_expressions :
      can(regex("^(rate\\(.+\\)|cron\\(.+\\))$", schedule.schedule_expression))
    ])
    error_message = "Schedule expressions must be valid rate() or cron() expressions."
  }
}

# ============================================================================
# EVENT-DRIVEN VARIABLES
# ============================================================================

variable "enable_event_driven" {
  type        = bool
  description = "Enable event-driven task execution"
  default     = false
}

variable "lambda_execution_role_arn" {
  type        = string
  description = "IAM role ARN for Lambda functions (required when enable_event_driven = true)"
  default     = ""

  validation {
    condition     = var.lambda_execution_role_arn == "" || can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.lambda_execution_role_arn))
    error_message = "Lambda execution role ARN must be a valid IAM role ARN format."
  }
}

variable "event_sources" {
  type = list(object({
    type   = string      # s3, sqs, sns
    name   = string      # unique name for the event source
    config = map(string) # source-specific configuration
  }))
  description = "Event sources that trigger task execution"
  default     = []

  validation {
    condition = alltrue([
      for source in var.event_sources : contains(["s3", "sqs", "sns"], source.type)
    ])
    error_message = "Event source type must be one of: s3, sqs, sns."
  }
}

# ============================================================================
# BATCH PROCESSING VARIABLES
# ============================================================================

variable "enable_batch_processing" {
  type        = bool
  description = "Enable AWS Batch integration"
  default     = false
}

variable "batch_job_queue_name" {
  type        = string
  description = "AWS Batch job queue name (required when enable_batch_processing = true)"
  default     = ""

  validation {
    condition     = var.batch_job_queue_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,127}$", var.batch_job_queue_name))
    error_message = "Batch job queue name must be 1-128 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "batch_job_definition_name" {
  type        = string
  description = "AWS Batch job definition name (required when enable_batch_processing = true)"
  default     = ""

  validation {
    condition     = var.batch_job_definition_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,127}$", var.batch_job_definition_name))
    error_message = "Batch job definition name must be 1-128 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

variable "batch_compute_environment_name" {
  type        = string
  description = "AWS Batch compute environment name (required when enable_batch_processing = true)"
  default     = ""

  validation {
    condition     = var.batch_compute_environment_name == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,127}$", var.batch_compute_environment_name))
    error_message = "Batch compute environment name must be 1-128 characters, start with alphanumeric, and contain only alphanumeric, hyphens, and underscores."
  }
}

# ============================================================================
# ALB STICKINESS CONFIGURATION
# ============================================================================

variable "alb_enable_stickiness" {
  type        = bool
  description = "Enable session stickiness for ALB target group (required for stateful applications like MCP servers)"
  default     = false
}

variable "alb_stickiness_duration" {
  type        = number
  description = "Duration of ALB session stickiness in seconds (1-604800)"
  default     = 86400

  validation {
    condition     = var.alb_stickiness_duration >= 1 && var.alb_stickiness_duration <= 604800
    error_message = "ALB stickiness duration must be between 1 and 604800 seconds (7 days)."
  }
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}

# ============================================================================
# CROSS-VARIABLE VALIDATION (Note: These validations are implemented in locals)
# ============================================================================
# Cross-variable validations are handled in the main.tf locals block
# due to Terraform limitations with cross-variable validation in variables.tf
