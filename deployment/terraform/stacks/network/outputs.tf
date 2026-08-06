# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Outputs — paste into ../all/terraform.tfvars
# =============================================================================

output "vpc_id" {
  description = "VPC ID. Use as `vpc_id` in ../all/terraform.tfvars."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR block."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs (one per AZ). Use as `alb_subnet_ids` in ../all/terraform.tfvars."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (one per AZ). Use as `gateway_subnet_ids` in ../all/terraform.tfvars."
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "Security group for the ALB. Wrap in a list for `alb_security_group_ids` in ../all/terraform.tfvars."
  value       = aws_security_group.alb.id
}

output "tasks_security_group_id" {
  description = "Security group for the Fargate tasks. Wrap in a list for `gateway_security_group_ids` in ../all/terraform.tfvars."
  value       = aws_security_group.tasks.id
}

output "nat_gateway_public_ip" {
  description = "NAT gateway Elastic IP (egress address seen by Bedrock APIs)."
  value       = aws_eip.nat.public_ip
}

# Convenience block: ready-to-paste excerpt for ../all/terraform.tfvars.
output "tfvars_snippet" {
  description = "Ready-to-paste excerpt for ../all/terraform.tfvars."
  value       = <<-EOT
    vpc_id                     = "${aws_vpc.this.id}"
    gateway_subnet_ids         = ${jsonencode(aws_subnet.private[*].id)}
    gateway_security_group_ids = ["${aws_security_group.tasks.id}"]
    alb_subnet_ids             = ${jsonencode(aws_subnet.public[*].id)}
    alb_security_group_ids     = ["${aws_security_group.alb.id}"]
  EOT
}
