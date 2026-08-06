# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ECS Fargate Terraform Module - Main Resources
# Supports all 8 AWS ECS invocation methods with standalone tasks as default

# Standard data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

# Existing cluster data source (when using existing cluster)
data "aws_ecs_cluster" "existing" {
  count        = var.create_cluster ? 0 : 1
  cluster_name = var.existing_cluster_name
}

# VPC validation data source (when VPC is provided)
data "aws_vpc" "selected" {
  count = var.vpc_id != "" ? 1 : 0
  id    = var.vpc_id
}

# Subnet validation data sources (when subnets are provided)
data "aws_subnet" "selected" {
  count = length(var.subnet_ids)
  id    = var.subnet_ids[count.index]
}

# ALB subnet validation data sources (when ALB is enabled)
data "aws_subnet" "alb_subnets" {
  count = var.enable_alb ? length(var.alb_subnets) : 0
  id    = var.alb_subnets[count.index]
}

# NLB subnet validation data sources (when NLB is enabled)
data "aws_subnet" "nlb_subnets" {
  count = var.enable_nlb ? length(var.nlb_subnets) : 0
  id    = var.nlb_subnets[count.index]
}

# GLB subnet validation data sources (when GLB is enabled)
data "aws_subnet" "glb_subnets" {
  count = var.enable_glb ? length(var.glb_subnets) : 0
  id    = var.glb_subnets[count.index]
}

# Local values with explicit configuration (repo pattern)
locals {
  # Standard account reference
  account_id = data.aws_caller_identity.current.account_id

  # Auto-generate names if not provided (following repo naming patterns)
  cluster_name = var.cluster_name != "" ? var.cluster_name : "${var.task_family}-cluster"
  service_name = var.service_name != "" ? var.service_name : "${var.task_family}-service"

  # Cluster reference (new or existing) - following conditional pattern
  cluster_id  = var.create_cluster ? aws_ecs_cluster.main[0].id : data.aws_ecs_cluster.existing[0].id
  cluster_arn = var.create_cluster ? aws_ecs_cluster.main[0].arn : data.aws_ecs_cluster.existing[0].arn

  # Determine execution pattern
  is_standalone     = !var.enable_service && !var.enable_scheduled_tasks && !var.enable_event_driven
  is_service        = var.enable_service
  has_load_balancer = var.enable_alb || var.enable_nlb || var.enable_glb

  # Networking requirements
  requires_vpc_config = local.is_service || local.has_load_balancer || var.enable_scheduled_tasks || var.enable_event_driven

  # Validation flags
  container_port_required = local.has_load_balancer || var.enable_service
  vpc_config_required     = local.requires_vpc_config

  # Event source categorization (following for_each patterns)
  s3_event_sources  = [for source in var.event_sources : source if source.type == "s3"]
  sqs_event_sources = [for source in var.event_sources : source if source.type == "sqs"]
  sns_event_sources = [for source in var.event_sources : source if source.type == "sns"]

  # Tags following repo merge pattern
  common_tags = merge(var.tags, {
    ManagedBy = "terraform"
    Module    = "ecs-fargate"
    Pattern   = local.is_standalone ? "standalone" : (local.is_service ? "service" : "scheduled")
  })

  # VPC and subnet validation (Task 3.2)
  # Validate that all subnets exist in the specified VPC
  validate_subnets_in_vpc = var.vpc_id != "" && length(var.subnet_ids) > 0 ? alltrue([
    for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id
  ]) : true

  # Validate that ALB subnets are in the same VPC as the tasks. The earlier
  # version of this check required alb_subnets to be a subset of subnet_ids,
  # which forced ALB and tasks to share subnets. That conflicts with the
  # standard "public ALB + private tasks" pattern, so the check is now a
  # VPC-membership assertion instead.
  validate_alb_subnet_consistency = var.enable_alb && var.vpc_id != "" ? alltrue([
    for subnet in data.aws_subnet.alb_subnets : subnet.vpc_id == var.vpc_id
  ]) : true

  # Validate that ALB has at least 2 subnets when enabled
  validate_alb_subnet_count = var.enable_alb ? length(var.alb_subnets) >= 2 : true

  # Validate that NLB subnets are subset of main subnet_ids
  validate_nlb_subnet_consistency = var.enable_nlb ? alltrue([
    for subnet in var.nlb_subnets : contains(var.subnet_ids, subnet)
  ]) : true

  # Validate that GLB subnets are subset of main subnet_ids
  validate_glb_subnet_consistency = var.enable_glb ? alltrue([
    for subnet in var.glb_subnets : contains(var.subnet_ids, subnet)
  ]) : true

  # Cross-variable validation (implemented as locals for runtime validation)
  validate_container_port = local.container_port_required && var.container_port == 0 ? tobool("container_port is required when enable_service, enable_alb, enable_nlb, or enable_glb is true") : true

  validate_vpc_config = local.vpc_config_required && (var.vpc_id == "" || length(var.subnet_ids) == 0 || length(var.security_group_ids) == 0) ? tobool("vpc_id, subnet_ids, and security_group_ids are required when enabling services, load balancers, scheduled tasks, or event-driven tasks") : true

  validate_alb_subnets = var.enable_alb && length(var.alb_subnets) < 2 ? tobool("alb_subnets must contain at least 2 subnets when enable_alb is true") : true

  validate_alb_vpc_config = var.enable_alb && (var.vpc_id == "" || length(var.security_group_ids) == 0) ? tobool("vpc_id and security_group_ids are required when enable_alb is true") : true

  validate_nlb_subnets = var.enable_nlb && length(var.nlb_subnets) < 2 ? tobool("nlb_subnets must contain at least 2 subnets when enable_nlb is true") : true

  validate_glb_subnets = var.enable_glb && length(var.glb_subnets) < 2 ? tobool("glb_subnets must contain at least 2 subnets when enable_glb is true") : true

  validate_eventbridge_role = var.enable_scheduled_tasks && var.eventbridge_role_arn == "" ? tobool("eventbridge_role_arn is required when enable_scheduled_tasks is true") : true

  validate_lambda_role = var.enable_event_driven && var.lambda_execution_role_arn == "" ? tobool("lambda_execution_role_arn is required when enable_event_driven is true") : true

  validate_https_cert = var.enable_https && var.certificate_arn == "" ? tobool("certificate_arn is required when enable_https is true") : true

  validate_existing_cluster = !var.create_cluster && var.existing_cluster_name == "" ? tobool("existing_cluster_name is required when create_cluster is false") : true

  validate_batch_config = var.enable_batch_processing && (var.batch_job_queue_name == "" || var.batch_job_definition_name == "" || var.batch_compute_environment_name == "") ? tobool("batch_job_queue_name, batch_job_definition_name, and batch_compute_environment_name are required when enable_batch_processing is true") : true

  # Availability zone validation for load balancers (Task 3.2)
  alb_availability_zones = var.enable_alb ? [
    for subnet in data.aws_subnet.alb_subnets : subnet.availability_zone
  ] : []

  nlb_availability_zones = var.enable_nlb ? [
    for subnet in data.aws_subnet.nlb_subnets : subnet.availability_zone
  ] : []

  glb_availability_zones = var.enable_glb ? [
    for subnet in data.aws_subnet.glb_subnets : subnet.availability_zone
  ] : []

  # Validate that load balancer subnets are in different availability zones
  validate_alb_multi_az = var.enable_alb ? length(distinct(local.alb_availability_zones)) >= 2 : true
  validate_nlb_multi_az = var.enable_nlb ? length(distinct(local.nlb_availability_zones)) >= 2 : true
  validate_glb_multi_az = var.enable_glb ? length(distinct(local.glb_availability_zones)) >= 2 : true

  # Validation assertions (Task 3.2)
  validate_subnets_vpc_assertion = local.validate_subnets_in_vpc ? true : tobool("All subnet_ids must exist in the specified vpc_id")

  validate_alb_consistency_assertion = local.validate_alb_subnet_consistency ? true : tobool("All alb_subnets must belong to the specified vpc_id")

  validate_alb_subnet_count_assertion = local.validate_alb_subnet_count ? true : tobool("ALB requires at least 2 subnets when enable_alb is true")

  validate_nlb_consistency_assertion = local.validate_nlb_subnet_consistency ? true : tobool("All nlb_subnets must be included in subnet_ids")

  validate_glb_consistency_assertion = local.validate_glb_subnet_consistency ? true : tobool("All glb_subnets must be included in subnet_ids")

  validate_alb_multi_az_assertion = local.validate_alb_multi_az ? true : tobool("ALB subnets must be in at least 2 different availability zones")

  validate_nlb_multi_az_assertion = local.validate_nlb_multi_az ? true : tobool("NLB subnets must be in at least 2 different availability zones")

  validate_glb_multi_az_assertion = local.validate_glb_multi_az ? true : tobool("GLB subnets must be in at least 2 different availability zones")
}

# ============================================================================
# CLOUDWATCH LOGGING (Task 9.1 - CloudWatch Logging Implementation)
# ============================================================================

# CloudWatch Log Group (always created)
# Provides centralized logging for all ECS tasks with configurable retention
resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/${var.task_family}"
  retention_in_days = var.log_retention_days

  # Enhanced tagging following repo patterns
  tags = merge(local.common_tags, {
    Name       = "/ecs/${var.task_family}"
    Type       = "cloudwatch-log-group"
    Purpose    = "ecs-container-logging"
    TaskFamily = var.task_family
    LogType    = "application"
    Retention  = "${var.log_retention_days}days"
  })
}

# ECS Cluster (conditional creation)
resource "aws_ecs_cluster" "main" {
  count = var.create_cluster ? 1 : 0
  name  = local.cluster_name

  configuration {
    execute_command_configuration {
      logging = "DEFAULT"
    }
  }

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = local.common_tags
}

# ============================================================================
# CLOUDWATCH MONITORING AND ALARMS (Task 9.2 - Container Insights and Monitoring)
# ============================================================================

# CloudWatch Alarm for ECS Service CPU Utilization (conditional)
# Monitors CPU utilization for ECS services to detect performance issues
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_utilization" {
  count = var.enable_service && var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.cpu_utilization_threshold
  alarm_description   = "This metric monitors ECS service CPU utilization"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    ServiceName = local.service_name
    ClusterName = local.cluster_name
  }

  tags = merge(local.common_tags, {
    Name       = "${var.task_family}-cpu-utilization"
    Type       = "cloudwatch-alarm"
    Purpose    = "ecs-service-monitoring"
    MetricType = "cpu-utilization"
    Threshold  = tostring(var.cpu_utilization_threshold)
  })

  depends_on = [aws_ecs_service.main]
}

# CloudWatch Alarm for ECS Service Memory Utilization (conditional)
# Monitors memory utilization for ECS services to detect memory pressure
resource "aws_cloudwatch_metric_alarm" "ecs_memory_utilization" {
  count = var.enable_service && var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.memory_utilization_threshold
  alarm_description   = "This metric monitors ECS service memory utilization"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    ServiceName = local.service_name
    ClusterName = local.cluster_name
  }

  tags = merge(local.common_tags, {
    Name       = "${var.task_family}-memory-utilization"
    Type       = "cloudwatch-alarm"
    Purpose    = "ecs-service-monitoring"
    MetricType = "memory-utilization"
    Threshold  = tostring(var.memory_utilization_threshold)
  })

  depends_on = [aws_ecs_service.main]
}

# CloudWatch Alarm for ECS Service Running Task Count (conditional)
# Monitors the number of running tasks to detect service availability issues
resource "aws_cloudwatch_metric_alarm" "ecs_running_task_count" {
  count = var.enable_service && var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-running-task-count"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RunningTaskCount"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = var.desired_count
  alarm_description   = "This metric monitors ECS service running task count"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    ServiceName = local.service_name
    ClusterName = local.cluster_name
  }

  tags = merge(local.common_tags, {
    Name       = "${var.task_family}-running-task-count"
    Type       = "cloudwatch-alarm"
    Purpose    = "ecs-service-monitoring"
    MetricType = "running-task-count"
    Threshold  = tostring(var.desired_count)
  })

  depends_on = [aws_ecs_service.main]
}

# CloudWatch Alarm for ALB Target Health (conditional)
# Monitors ALB target group healthy host count to detect load balancer issues
resource "aws_cloudwatch_metric_alarm" "alb_healthy_host_count" {
  count = var.enable_alb && var.enable_load_balancer_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-alb-healthy-hosts"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "This metric monitors ALB healthy host count"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    TargetGroup  = aws_lb_target_group.alb[0].arn_suffix
    LoadBalancer = aws_lb.alb[0].arn_suffix
  }

  tags = merge(local.common_tags, {
    Name         = "${var.task_family}-alb-healthy-hosts"
    Type         = "cloudwatch-alarm"
    Purpose      = "load-balancer-monitoring"
    MetricType   = "healthy-host-count"
    LoadBalancer = "alb"
  })

  depends_on = [aws_lb_target_group.alb, aws_lb.alb]
}

# CloudWatch Alarm for ALB Response Time (conditional)
# Monitors ALB target response time to detect performance issues
resource "aws_cloudwatch_metric_alarm" "alb_response_time" {
  count = var.enable_alb && var.enable_load_balancer_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-alb-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = 1.0 # 1 second
  alarm_description   = "This metric monitors ALB target response time"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    LoadBalancer = aws_lb.alb[0].arn_suffix
  }

  tags = merge(local.common_tags, {
    Name         = "${var.task_family}-alb-response-time"
    Type         = "cloudwatch-alarm"
    Purpose      = "load-balancer-monitoring"
    MetricType   = "response-time"
    LoadBalancer = "alb"
    Threshold    = "1.0s"
  })

  depends_on = [aws_lb.alb]
}

# CloudWatch Alarm for NLB Healthy Host Count (conditional)
# Monitors NLB target group healthy host count to detect load balancer issues
resource "aws_cloudwatch_metric_alarm" "nlb_healthy_host_count" {
  count = var.enable_nlb && var.enable_load_balancer_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-nlb-healthy-hosts"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/NetworkELB"
  period              = "60"
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "This metric monitors NLB healthy host count"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    TargetGroup  = aws_lb_target_group.nlb[0].arn_suffix
    LoadBalancer = aws_lb.nlb[0].arn_suffix
  }

  tags = merge(local.common_tags, {
    Name         = "${var.task_family}-nlb-healthy-hosts"
    Type         = "cloudwatch-alarm"
    Purpose      = "load-balancer-monitoring"
    MetricType   = "healthy-host-count"
    LoadBalancer = "nlb"
  })

  depends_on = [aws_lb_target_group.nlb, aws_lb.nlb]
}

# CloudWatch Alarm for GLB Healthy Host Count (conditional)
# Monitors GLB target group healthy host count to detect load balancer issues
resource "aws_cloudwatch_metric_alarm" "glb_healthy_host_count" {
  count = var.enable_glb && var.enable_load_balancer_alarms ? 1 : 0

  alarm_name          = "${var.task_family}-glb-healthy-hosts"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/GatewayELB"
  period              = "60"
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "This metric monitors GLB healthy host count"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
  ok_actions          = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    TargetGroup  = aws_lb_target_group.glb[0].arn_suffix
    LoadBalancer = aws_lb.glb[0].arn_suffix
  }

  tags = merge(local.common_tags, {
    Name         = "${var.task_family}-glb-healthy-hosts"
    Type         = "cloudwatch-alarm"
    Purpose      = "load-balancer-monitoring"
    MetricType   = "healthy-host-count"
    LoadBalancer = "glb"
  })

  depends_on = [aws_lb_target_group.glb, aws_lb.glb]
}

# ECS Task Definition (always created)
resource "aws_ecs_task_definition" "main" {
  family                   = var.task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = var.container_name
      image = var.container_image

      # Only include port mappings if container_port is specified
      portMappings = var.container_port > 0 ? [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ] : []

      environment = [
        for key, value in var.environment_variables : {
          name  = key
          value = value
        }
      ]

      secrets = var.secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = var.log_stream_prefix
        }
      }

      essential = true
    }
  ])

  tags = local.common_tags
}

# ============================================================================
# ECS SERVICE (Task 3.1 - Conditional Creation)
# ============================================================================

# ECS Service (conditional creation based on enable_service)
resource "aws_ecs_service" "main" {
  count           = var.enable_service ? 1 : 0
  name            = local.service_name
  cluster         = local.cluster_id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Explicit VPC configuration required for services
  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = var.assign_public_ip
  }

  # Dynamic load balancer blocks for ALB, NLB, GLB integration
  dynamic "load_balancer" {
    for_each = var.enable_alb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.alb[0].arn
      container_name   = var.container_name
      container_port   = var.container_port
    }
  }

  dynamic "load_balancer" {
    for_each = var.enable_nlb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.nlb[0].arn
      container_name   = var.container_name
      container_port   = var.container_port
    }
  }

  dynamic "load_balancer" {
    for_each = var.enable_glb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.glb[0].arn
      container_name   = var.container_name
      container_port   = var.container_port
    }
  }

  # Dependency management for load balancer resources
  depends_on = [
    aws_lb_listener.alb_http,
    aws_lb_listener.alb_https,
    aws_lb_listener.nlb,
    aws_lb_listener.glb
  ]

  tags = local.common_tags

  # Ensure service waits for target group health checks when load balancers are enabled
  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ============================================================================
# APPLICATION LOAD BALANCER (Task 4.1 - ALB Resources with Target Groups)
# ============================================================================

# Application Load Balancer (conditional creation based on enable_alb)
# Uses separate security groups from ECS service for proper network isolation
resource "aws_lb" "alb" {
  count              = var.enable_alb ? 1 : 0
  name               = "${var.task_family}-alb"
  internal           = var.alb_internal
  load_balancer_type = "application"
  security_groups    = length(var.alb_security_group_ids) > 0 ? var.alb_security_group_ids : var.security_group_ids
  subnets            = var.alb_subnets

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-alb"
    Type = "application"
  })
}

# ALB Target Group for ECS Service (conditional creation based on enable_alb)
resource "aws_lb_target_group" "alb" {
  count       = var.enable_alb ? 1 : 0
  name        = "${var.task_family}-alb-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval            = 300
    path                = var.health_check_path
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  # Enable session stickiness for stateful applications like MCP servers
  stickiness {
    enabled         = var.alb_enable_stickiness
    type            = "lb_cookie"
    cookie_duration = var.alb_stickiness_duration
  }

  # Ensure target group is created before service
  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-alb-tg"
    Type = "application"
  })
}

# ALB HTTP Listener (conditional creation based on enable_alb)
resource "aws_lb_listener" "alb_http" {
  count             = var.enable_alb ? 1 : 0
  load_balancer_arn = aws_lb.alb[0].arn
  port              = "80"
  protocol          = "HTTP"

  # If HTTPS is enabled, redirect HTTP to HTTPS, otherwise forward to target group
  dynamic "default_action" {
    for_each = var.enable_https ? [1] : []
    content {
      type = "redirect"

      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.enable_https ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.alb[0].arn
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-alb-http-listener"
    Type = "application"
  })
}

# ALB HTTPS Listener (conditional creation based on enable_alb AND enable_https)
resource "aws_lb_listener" "alb_https" {
  count             = var.enable_alb && var.enable_https ? 1 : 0
  load_balancer_arn = aws_lb.alb[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alb[0].arn
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-alb-https-listener"
    Type = "application"
  })
}

# ============================================================================
# NETWORK LOAD BALANCER (Task 5.1 - NLB Resources with TCP/UDP Support)
# ============================================================================

# Network Load Balancer (conditional creation based on enable_nlb)
resource "aws_lb" "nlb" {
  count              = var.enable_nlb ? 1 : 0
  name               = "${var.task_family}-nlb"
  internal           = var.nlb_internal
  load_balancer_type = "network"
  subnets            = var.nlb_subnets

  enable_cross_zone_load_balancing = var.nlb_enable_cross_zone_load_balancing
  enable_deletion_protection       = false

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-nlb"
    Type = "network"
  })
}

# NLB Target Group for ECS Service (conditional creation based on enable_nlb)
resource "aws_lb_target_group" "nlb" {
  count       = var.enable_nlb ? 1 : 0
  name        = "${var.task_family}-nlb-tg"
  port        = var.nlb_target_port
  protocol    = var.nlb_protocol
  vpc_id      = var.vpc_id
  target_type = "ip"

  # Health check configuration for TCP/HTTP protocols
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = var.nlb_protocol == "TCP" ? 6 : 5
    interval            = 30
    port                = "traffic-port"
    protocol            = var.nlb_protocol == "TCP" ? "TCP" : "HTTP"

    # Only set path for HTTP health checks
    path = var.nlb_protocol == "HTTP" ? "/" : null
  }

  # Ensure target group is created before service
  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-nlb-tg"
    Type = "network"
  })
}

# NLB Listener (conditional creation based on enable_nlb)
resource "aws_lb_listener" "nlb" {
  count             = var.enable_nlb ? 1 : 0
  load_balancer_arn = aws_lb.nlb[0].arn
  port              = var.nlb_target_port
  protocol          = var.nlb_protocol

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb[0].arn
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-nlb-listener"
    Type = "network"
  })
}

# ============================================================================
# GATEWAY LOAD BALANCER (Task 6.1 - GLB Resources for Virtual Appliances)
# ============================================================================

# Gateway Load Balancer (conditional creation based on enable_glb)
resource "aws_lb" "glb" {
  count              = var.enable_glb ? 1 : 0
  name               = "${var.task_family}-glb"
  load_balancer_type = "gateway"
  subnets            = var.glb_subnets

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-glb"
    Type = "gateway"
  })
}

# GLB Target Group for ECS Service (conditional creation based on enable_glb)
# Uses GENEVE protocol for virtual appliance traffic inspection
resource "aws_lb_target_group" "glb" {
  count       = var.enable_glb ? 1 : 0
  name        = "${var.task_family}-glb-tg"
  port        = var.glb_target_port
  protocol    = "GENEVE"
  vpc_id      = var.vpc_id
  target_type = "ip"

  # GLB-specific health check configuration
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    port                = var.glb_target_port
    protocol            = "HTTP"
    path                = var.health_check_path
  }

  # Ensure target group is created before service
  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-glb-tg"
    Type = "gateway"
  })
}

# GLB Listener (conditional creation based on enable_glb)
resource "aws_lb_listener" "glb" {
  count             = var.enable_glb ? 1 : 0
  load_balancer_arn = aws_lb.glb[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.glb[0].arn
  }

  tags = merge(local.common_tags, {
    Name = "${var.task_family}-glb-listener"
    Type = "gateway"
  })
}

# ============================================================================
# SCHEDULED TASKS WITH EVENTBRIDGE (Task 7.1 - EventBridge Rules)
# ============================================================================

# EventBridge Rules for task scheduling (conditional creation based on enable_scheduled_tasks)
# Uses for_each pattern to create multiple rules from schedule_expressions variable
resource "aws_cloudwatch_event_rule" "scheduled_tasks" {
  for_each = var.enable_scheduled_tasks ? {
    for schedule in var.schedule_expressions : schedule.name => schedule
  } : {}

  name                = "${var.task_family}-${each.key}"
  description         = each.value.description
  schedule_expression = each.value.schedule_expression
  state               = each.value.enabled ? "ENABLED" : "DISABLED"

  tags = merge(local.common_tags, {
    Name        = "${var.task_family}-${each.key}"
    Type        = "scheduled-task"
    Schedule    = each.value.schedule_expression
    Description = each.value.description
  })
}

# ============================================================================
# EVENTBRIDGE TARGETS FOR ECS TASK EXECUTION (Task 7.2)
# ============================================================================

# EventBridge Targets for ECS task execution (conditional creation based on enable_scheduled_tasks)
# Uses for_each pattern to create targets for each EventBridge rule
resource "aws_cloudwatch_event_target" "ecs_tasks" {
  for_each = var.enable_scheduled_tasks ? {
    for schedule in var.schedule_expressions : schedule.name => schedule
  } : {}

  rule      = aws_cloudwatch_event_rule.scheduled_tasks[each.key].name
  target_id = "${var.task_family}-${each.key}-target"
  arn       = local.cluster_arn
  role_arn  = var.eventbridge_role_arn

  # ECS target configuration with task definition and network configuration
  ecs_target {
    task_definition_arn = aws_ecs_task_definition.main.arn
    launch_type         = "FARGATE"
    task_count          = 1
    platform_version    = "LATEST"

    # Network configuration using explicit VPC parameters
    # Only include network configuration if VPC parameters are provided
    dynamic "network_configuration" {
      for_each = var.vpc_id != "" && length(var.subnet_ids) > 0 ? [1] : []
      content {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = var.assign_public_ip
      }
    }
  }
}

# ============================================================================
# AWS BATCH INTEGRATION (Task 8.1 - Batch Processing Support)
# ============================================================================

# Data sources for existing Batch resources validation
data "aws_batch_job_queue" "existing" {
  count = var.enable_batch_processing ? 1 : 0
  name  = var.batch_job_queue_name
}

data "aws_batch_compute_environment" "existing" {
  count = var.enable_batch_processing ? 1 : 0
  name  = var.batch_compute_environment_name
}

# AWS Batch Job Definition using ECS task definition
# This creates a Batch job definition that references the ECS task definition
# allowing the same container configuration to be used for both ECS and Batch workloads
resource "aws_batch_job_definition" "main" {
  count                 = var.enable_batch_processing ? 1 : 0
  name                  = var.batch_job_definition_name
  type                  = "container"
  platform_capabilities = ["FARGATE"]

  # Container properties derived from ECS task definition
  container_properties = jsonencode({
    # Use the same container image as ECS task definition
    image = var.container_image

    # Resource requirements matching ECS task definition
    resourceRequirements = [
      {
        type  = "VCPU"
        value = tostring(var.cpu / 1024) # Convert CPU units to vCPU (1024 units = 1 vCPU)
      },
      {
        type  = "MEMORY"
        value = tostring(var.memory)
      }
    ]

    # Execution role for Batch job (same as ECS task execution role)
    executionRoleArn = var.execution_role_arn

    # Job role for Batch job (same as ECS task role)
    jobRoleArn = var.task_role_arn

    # Environment variables from ECS task definition
    environment = [
      for key, value in var.environment_variables : {
        name  = key
        value = value
      }
    ]

    # Secrets from ECS task definition
    secrets = var.secrets

    # Logging configuration matching ECS task definition
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = data.aws_region.current.id
        "awslogs-stream-prefix" = "${var.log_stream_prefix}-batch"
      }
    }

    # Network configuration for Fargate
    networkConfiguration = var.vpc_id != "" && length(var.subnet_ids) > 0 ? {
      assignPublicIp = var.assign_public_ip ? "ENABLED" : "DISABLED"
    } : null

    # Fargate platform configuration
    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
  })

  # Timeout configuration (optional, can be overridden at job submission)
  timeout {
    attempt_duration_seconds = 3600 # 1 hour default timeout
  }

  # Retry strategy (optional, can be overridden at job submission)
  retry_strategy {
    attempts = 1
  }

  tags = merge(local.common_tags, {
    Name   = var.batch_job_definition_name
    Type   = "batch-job-definition"
    Source = "ecs-task-definition"
  })

  # Ensure job definition is created after task definition and log group
  depends_on = [
    aws_ecs_task_definition.main,
    aws_cloudwatch_log_group.main
  ]
}

# ============================================================================
# PLACEHOLDER COMMENTS FOR FUTURE IMPLEMENTATION
# ============================================================================
# Additional resources will be implemented in subsequent tasks:
# - Task 8: Event-driven tasks with Lambda triggers (removed from scope)
