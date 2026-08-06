# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ECS Fargate Terraform Module - Output Values
# Following repo patterns with conditional expressions

# ============================================================================
# CORE OUTPUTS (Always Available)
# Task 10.1 - Core resource outputs following repo patterns
# ============================================================================

output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = local.cluster_id
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = local.cluster_arn
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.main.arn
}

output "task_definition_family" {
  description = "Family of the task definition"
  value       = aws_ecs_task_definition.main.family
}

output "task_definition_revision" {
  description = "Revision of the task definition"
  value       = aws_ecs_task_definition.main.revision
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.main.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.main.arn
}

output "log_stream_prefix" {
  description = "Log stream prefix used for CloudWatch logs"
  value       = var.log_stream_prefix
}

output "log_retention_days" {
  description = "Log retention period in days"
  value       = var.log_retention_days
}

# ============================================================================
# MONITORING OUTPUTS (Task 9.2 - CloudWatch Alarms and Monitoring)
# ============================================================================

output "cloudwatch_alarms_enabled" {
  description = "Whether CloudWatch alarms are enabled"
  value       = var.enable_cloudwatch_alarms
}

output "ecs_cpu_alarm_arn" {
  description = "ARN of the ECS CPU utilization alarm"
  value       = var.enable_service && var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.ecs_cpu_utilization[0].arn : null
}

output "ecs_memory_alarm_arn" {
  description = "ARN of the ECS memory utilization alarm"
  value       = var.enable_service && var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.ecs_memory_utilization[0].arn : null
}

output "ecs_task_count_alarm_arn" {
  description = "ARN of the ECS running task count alarm"
  value       = var.enable_service && var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.ecs_running_task_count[0].arn : null
}

output "alb_healthy_hosts_alarm_arn" {
  description = "ARN of the ALB healthy hosts alarm"
  value       = var.enable_alb && var.enable_load_balancer_alarms ? aws_cloudwatch_metric_alarm.alb_healthy_host_count[0].arn : null
}

output "alb_response_time_alarm_arn" {
  description = "ARN of the ALB response time alarm"
  value       = var.enable_alb && var.enable_load_balancer_alarms ? aws_cloudwatch_metric_alarm.alb_response_time[0].arn : null
}

output "nlb_healthy_hosts_alarm_arn" {
  description = "ARN of the NLB healthy hosts alarm"
  value       = var.enable_nlb && var.enable_load_balancer_alarms ? aws_cloudwatch_metric_alarm.nlb_healthy_host_count[0].arn : null
}

output "glb_healthy_hosts_alarm_arn" {
  description = "ARN of the GLB healthy hosts alarm"
  value       = var.enable_glb && var.enable_load_balancer_alarms ? aws_cloudwatch_metric_alarm.glb_healthy_host_count[0].arn : null
}

output "container_insights_enabled" {
  description = "Whether Container Insights is enabled on the ECS cluster"
  value       = var.enable_container_insights
}

output "monitoring_configuration" {
  description = "Summary of monitoring configuration"
  value = {
    container_insights_enabled   = var.enable_container_insights
    cloudwatch_alarms_enabled    = var.enable_cloudwatch_alarms
    load_balancer_alarms_enabled = var.enable_load_balancer_alarms
    cpu_threshold                = var.cpu_utilization_threshold
    memory_threshold             = var.memory_utilization_threshold
    sns_topic_arn                = var.alarm_sns_topic_arn != "" ? var.alarm_sns_topic_arn : null
  }
}

# ============================================================================
# SERVICE OUTPUTS (Conditional)
# Task 10.1 - Conditional service outputs with null for disabled features
# ============================================================================

output "service_id" {
  description = "ID of the ECS service"
  value       = var.enable_service ? aws_ecs_service.main[0].id : null
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = var.enable_service ? aws_ecs_service.main[0].arn : null
}

output "service_name" {
  description = "Name of the ECS service"
  value       = var.enable_service ? aws_ecs_service.main[0].name : null
}

# ============================================================================
# APPLICATION LOAD BALANCER OUTPUTS (Conditional)
# Task 10.2 - ALB outputs with conditional expressions and null for disabled features
# ============================================================================

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = var.enable_alb ? aws_lb.alb[0].arn : null
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = var.enable_alb ? aws_lb.alb[0].dns_name : null
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = var.enable_alb ? aws_lb.alb[0].zone_id : null
}

output "alb_target_group_arn" {
  description = "ARN of the ALB target group for integration"
  value       = var.enable_alb ? aws_lb_target_group.alb[0].arn : null
}

output "alb_listener_arn" {
  description = "ARN of the ALB HTTP listener"
  value       = var.enable_alb ? aws_lb_listener.alb_http[0].arn : null
}

output "alb_https_listener_arn" {
  description = "ARN of the ALB HTTPS listener"
  value       = var.enable_alb && var.enable_https ? aws_lb_listener.alb_https[0].arn : null
}

# ============================================================================
# NETWORK LOAD BALANCER OUTPUTS (Conditional)
# Task 10.2 - NLB outputs with conditional expressions and null for disabled features
# ============================================================================

output "nlb_arn" {
  description = "ARN of the Network Load Balancer"
  value       = var.enable_nlb ? aws_lb.nlb[0].arn : null
}

output "nlb_dns_name" {
  description = "DNS name of the Network Load Balancer"
  value       = var.enable_nlb ? aws_lb.nlb[0].dns_name : null
}

output "nlb_zone_id" {
  description = "Zone ID of the Network Load Balancer"
  value       = var.enable_nlb ? aws_lb.nlb[0].zone_id : null
}

output "nlb_target_group_arn" {
  description = "ARN of the NLB target group for integration"
  value       = var.enable_nlb ? aws_lb_target_group.nlb[0].arn : null
}

output "nlb_listener_arn" {
  description = "ARN of the NLB listener"
  value       = var.enable_nlb ? aws_lb_listener.nlb[0].arn : null
}

# ============================================================================
# GATEWAY LOAD BALANCER OUTPUTS (Conditional)
# Task 10.2 - GLB outputs with conditional expressions and null for disabled features
# ============================================================================

output "glb_arn" {
  description = "ARN of the Gateway Load Balancer"
  value       = var.enable_glb ? aws_lb.glb[0].arn : null
}

output "glb_dns_name" {
  description = "DNS name of the Gateway Load Balancer"
  value       = var.enable_glb ? aws_lb.glb[0].dns_name : null
}

output "glb_zone_id" {
  description = "Zone ID of the Gateway Load Balancer"
  value       = var.enable_glb ? aws_lb.glb[0].zone_id : null
}

output "glb_target_group_arn" {
  description = "ARN of the GLB target group for integration"
  value       = var.enable_glb ? aws_lb_target_group.glb[0].arn : null
}

output "glb_listener_arn" {
  description = "ARN of the GLB listener"
  value       = var.enable_glb ? aws_lb_listener.glb[0].arn : null
}

# ============================================================================
# SCHEDULED TASKS OUTPUTS (Conditional)
# Task 10.3 - Advanced feature outputs following repo naming conventions
# ============================================================================

output "scheduled_task_rule_arns" {
  description = "ARNs of the EventBridge rules for scheduled tasks"
  value = var.enable_scheduled_tasks ? {
    for name, rule in aws_cloudwatch_event_rule.scheduled_tasks : name => rule.arn
  } : null
}

output "scheduled_task_rule_names" {
  description = "Names of the EventBridge rules for scheduled tasks"
  value = var.enable_scheduled_tasks ? {
    for name, rule in aws_cloudwatch_event_rule.scheduled_tasks : name => rule.name
  } : null
}

output "scheduled_task_target_arns" {
  description = "ARNs of the EventBridge targets for scheduled tasks"
  value = var.enable_scheduled_tasks ? {
    for name, target in aws_cloudwatch_event_target.ecs_tasks : name => target.arn
  } : null
}

output "schedule_expressions" {
  description = "Schedule expressions configured for the scheduled tasks"
  value = var.enable_scheduled_tasks ? {
    for schedule in var.schedule_expressions : schedule.name => {
      expression  = schedule.schedule_expression
      description = schedule.description
      enabled     = schedule.enabled
    }
  } : null
}

# ============================================================================
# EVENT-DRIVEN OUTPUTS (Conditional)
# Task 10.3 - Event-driven outputs following repo naming conventions
# ============================================================================

output "lambda_function_arns" {
  description = "ARNs of Lambda functions for event-driven tasks"
  value = var.enable_event_driven ? {
    for source in var.event_sources : source.name => null # Will be populated when Lambda resources are implemented
  } : null
}

output "s3_bucket_notifications" {
  description = "S3 bucket notification configurations"
  value = var.enable_event_driven ? {
    for source in local.s3_event_sources : source.name => null # Will be populated when S3 notifications are implemented
  } : null
}

output "sqs_event_source_mappings" {
  description = "SQS event source mapping ARNs"
  value = var.enable_event_driven ? {
    for source in local.sqs_event_sources : source.name => null # Will be populated when SQS mappings are implemented
  } : null
}

output "sns_subscriptions" {
  description = "SNS subscription ARNs"
  value = var.enable_event_driven ? {
    for source in local.sns_event_sources : source.name => null # Will be populated when SNS subscriptions are implemented
  } : null
}

# ============================================================================
# BATCH PROCESSING OUTPUTS (Conditional)
# Task 10.3 - Batch integration outputs following repo naming conventions
# ============================================================================

output "batch_job_definition_arn" {
  description = "ARN of the Batch job definition"
  value       = var.enable_batch_processing ? aws_batch_job_definition.main[0].arn : null
}

output "batch_job_definition_name" {
  description = "Name of the Batch job definition"
  value       = var.enable_batch_processing ? aws_batch_job_definition.main[0].name : null
}

output "batch_job_definition_revision" {
  description = "Revision of the Batch job definition"
  value       = var.enable_batch_processing ? aws_batch_job_definition.main[0].revision : null
}

output "batch_job_queue_name" {
  description = "Name of the Batch job queue (from input variable)"
  value       = var.enable_batch_processing ? var.batch_job_queue_name : null
}

output "batch_compute_environment_name" {
  description = "Name of the Batch compute environment (from input variable)"
  value       = var.enable_batch_processing ? var.batch_compute_environment_name : null
}

# ============================================================================
# NETWORKING OUTPUTS (Conditional)
# ============================================================================

output "vpc_id" {
  description = "VPC ID used by the module"
  value       = var.vpc_id != "" ? var.vpc_id : null
}

output "subnet_ids" {
  description = "Subnet IDs used by the module"
  value       = length(var.subnet_ids) > 0 ? var.subnet_ids : null
}

output "security_group_ids" {
  description = "Security group IDs used by the module"
  value       = length(var.security_group_ids) > 0 ? var.security_group_ids : null
}

# ============================================================================
# METADATA OUTPUTS
# ============================================================================

output "deployment_pattern" {
  description = "Deployment pattern used (standalone, service, scheduled, event-driven)"
  value       = local.common_tags.Pattern
}

output "module_version" {
  description = "Version of the ECS Fargate module"
  value       = "1.0.0"
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = data.aws_region.current.id
}

output "aws_account_id" {
  description = "AWS account ID where resources are deployed"
  value       = data.aws_caller_identity.current.account_id
}
