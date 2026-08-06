# Network bootstrap stack

Optional one-shot stack that provisions the VPC, subnets, NAT gateway, and
security groups consumed by `../all/`. Use this when your sandbox AWS
account does not already have a VPC with the right shape (2 public + 2
private subnets, NAT egress).

## What it creates

| Resource | Purpose |
| --- | --- |
| `aws_vpc` | `10.0.0.0/16`, DNS support + hostnames enabled |
| `aws_internet_gateway` | Internet egress for public subnets |
| `aws_subnet` × 2 (public) | `10.0.0.0/24`, `10.0.1.0/24` — for the gateway ALB |
| `aws_subnet` × 2 (private) | `10.0.10.0/24`, `10.0.11.0/24` — for the gateway Fargate tasks |
| `aws_eip` + `aws_nat_gateway` | NAT egress so private subnets can reach `bedrock-agentcore.<region>.amazonaws.com` |
| `aws_route_table` × 2 | Public RT (default route → IGW), private RT (default route → NAT) |
| `aws_security_group` (alb) | Inbound 80/443 from the internet |
| `aws_security_group` (tasks) | Inbound 80 from the ALB SG only |

Two AZs by default. Override `availability_zones` if `us-west-2a/b` are
not the right pair for your account.

## Cost

A NAT gateway is ~$32/month plus per-GB data charges. Fine for a
sandbox; `terraform destroy` cleans it up. If you want to skip the NAT
bill, use VPC endpoints instead — out of scope for this bootstrap stack.

## Usage

```bash
cd deployment/terraform/stacks/network

# Optional: set the same region/profile you'll use for stacks/all/
cat > terraform.tfvars <<EOF
aws_region   = "us-west-2"
aws_profile  = ""
project_name = "browser-agent-blog"
environment  = "dev"
EOF

terraform init
terraform plan
terraform apply

# Copy the outputs into ../all/terraform.tfvars
terraform output
```

The outputs map 1:1 to the variables in `../all/`:

| `network` output | `all` variable |
| --- | --- |
| `vpc_id` | `vpc_id` |
| `private_subnet_ids` | `gateway_subnet_ids` |
| `public_subnet_ids` | `alb_subnet_ids` |
| `tasks_security_group_id` | `gateway_security_group_ids` (wrap in a list) |
| `alb_security_group_id` | `alb_security_group_ids` (wrap in a list) |

## Teardown

After `../all/` is destroyed (Step 7 in `PICKUP_PLAN.md`), run:

```bash
cd deployment/terraform/stacks/network
terraform destroy
```

Order matters — destroy `../all/` first so the ALB and Fargate tasks
release their ENIs in these subnets before the subnets/SGs go away.
