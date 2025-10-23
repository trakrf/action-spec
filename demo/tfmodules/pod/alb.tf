# Security group for ALB
resource "aws_security_group" "alb" {
  name_prefix = "${var.customer}-${var.environment}-alb-"
  description = "Security group for ${var.customer} ${var.environment} ALB"
  vpc_id      = local.vpc_id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound (for health checks)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-alb-sg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.customer}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.all.ids

  enable_deletion_protection = false  # Demo setting

  tags = {
    Name        = "${var.customer}-${var.environment}-alb"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Target group for EC2 instances
resource "aws_lb_target_group" "main" {
  name     = "${var.customer}-${var.environment}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = local.vpc_id

  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-tg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach EC2 instance to target group
resource "aws_lb_target_group_attachment" "main" {
  target_group_arn = aws_lb_target_group.main.arn
  target_id        = aws_instance.pod.id
  port             = 80
}

# HTTP listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
