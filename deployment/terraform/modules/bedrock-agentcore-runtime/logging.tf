# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ----------------------------------------------------------
#              Application Log Delivery (Optional)
# ----------------------------------------------------------

# CloudWatch Log Group for Application Logs (only when CWL and no custom ARN)
resource "aws_cloudwatch_log_group" "application" {
  count = var.enable_log_delivery && var.log_destination_type == "CWL" && var.log_destination_arn == null ? 1 : 0

  name              = "/aws/vendedlogs/bedrock-agentcore/runtime/APPLICATION_LOGS/${aws_bedrockagentcore_agent_runtime.this.agent_runtime_id}"
  retention_in_days = var.log_retention_days
  tags              = local.merged_tags
}

locals {
  # Resolve application log destination ARN
  application_log_destination_arn = var.enable_log_delivery ? coalesce(
    var.log_destination_arn,
    var.log_destination_type == "CWL" ? try(aws_cloudwatch_log_group.application[0].arn, null) : null
  ) : null

  # Resolve usage log destination ARN
  usage_log_destination_arn = var.enable_usage_log_delivery ? coalesce(
    var.usage_log_destination_arn,
    var.usage_log_destination_type == "CWL" ? try(aws_cloudwatch_log_group.usage[0].arn, null) : null
  ) : null
}

resource "aws_cloudwatch_log_delivery_source" "application" {
  count = var.enable_log_delivery ? 1 : 0

  name         = "${var.agent_runtime_name}-application"
  log_type     = "APPLICATION_LOGS"
  resource_arn = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

resource "aws_cloudwatch_log_delivery_destination" "application" {
  count = var.enable_log_delivery ? 1 : 0

  name          = "${var.agent_runtime_name}-application"
  output_format = var.log_output_format

  delivery_destination_configuration {
    destination_resource_arn = local.application_log_destination_arn
  }
}

resource "aws_cloudwatch_log_delivery" "application" {
  count = var.enable_log_delivery ? 1 : 0

  delivery_source_name     = aws_cloudwatch_log_delivery_source.application[0].name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.application[0].arn
}

# ----------------------------------------------------------
#              Usage Log Delivery (Optional)
# ----------------------------------------------------------

# CloudWatch Log Group for Usage Logs (only when CWL and no custom ARN)
resource "aws_cloudwatch_log_group" "usage" {
  count = var.enable_usage_log_delivery && var.usage_log_destination_type == "CWL" && var.usage_log_destination_arn == null ? 1 : 0

  name              = "/aws/vendedlogs/bedrock-agentcore/runtime/USAGE_LOGS/${aws_bedrockagentcore_agent_runtime.this.agent_runtime_id}"
  retention_in_days = var.log_retention_days
  tags              = local.merged_tags
}

resource "aws_cloudwatch_log_delivery_source" "usage" {
  count = var.enable_usage_log_delivery ? 1 : 0

  name         = "${var.agent_runtime_name}-usage"
  log_type     = "USAGE_LOGS"
  resource_arn = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

resource "aws_cloudwatch_log_delivery_destination" "usage" {
  count = var.enable_usage_log_delivery ? 1 : 0

  name          = "${var.agent_runtime_name}-usage"
  output_format = var.log_output_format

  delivery_destination_configuration {
    destination_resource_arn = local.usage_log_destination_arn
  }
}

resource "aws_cloudwatch_log_delivery" "usage" {
  count = var.enable_usage_log_delivery ? 1 : 0

  delivery_source_name     = aws_cloudwatch_log_delivery_source.usage[0].name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.usage[0].arn
}

# ----------------------------------------------------------
#              Trace Delivery (Optional)
# ----------------------------------------------------------
resource "aws_cloudwatch_log_delivery_source" "traces" {
  count = var.enable_trace_delivery ? 1 : 0

  name         = "${var.agent_runtime_name}-traces"
  log_type     = "TRACES"
  resource_arn = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

resource "aws_cloudwatch_log_delivery_destination" "traces" {
  count = var.enable_trace_delivery ? 1 : 0

  name                      = "${var.agent_runtime_name}-traces"
  delivery_destination_type = "XRAY"
}

resource "aws_cloudwatch_log_delivery" "traces" {
  count = var.enable_trace_delivery ? 1 : 0

  delivery_source_name     = aws_cloudwatch_log_delivery_source.traces[0].name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.traces[0].arn
}

# ----------------------------------------------------------
#              Endpoint Logs (AWS auto-created)
# ----------------------------------------------------------
data "aws_cloudwatch_log_group" "endpoint" {
  name = "/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.this.agent_runtime_id}-DEFAULT"

  depends_on = [aws_bedrockagentcore_agent_runtime.this]
}
