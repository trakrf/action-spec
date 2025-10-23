# Security group for demo pods
# Phase D1: Allow HTTP (80) and SSH (22) from anywhere
# Phase D2: Will tighten when ALB is added
resource "aws_security_group" "pod" {
  count = var.security_group_id == null ? 1 : 0

  name_prefix = "${var.customer}-${var.environment}-pod-"
  description = "Security group for ${var.customer} ${var.environment} pod"
  vpc_id      = local.vpc_id

  ingress {
    description = "HTTP from anywhere (demo only)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from anywhere (demo only)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-pod-sg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  security_group_id = var.security_group_id != null ? var.security_group_id : aws_security_group.pod[0].id
}
