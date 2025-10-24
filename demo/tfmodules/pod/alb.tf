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

# Target group for demo-app (port 80)
resource "aws_lb_target_group" "demo_app" {
  name     = "${var.customer}-${var.environment}-demo-tg"
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
    Name        = "${var.customer}-${var.environment}-demo-tg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach EC2 instance to demo-app target group
resource "aws_lb_target_group_attachment" "demo_app" {
  target_group_arn = aws_lb_target_group.demo_app.arn
  target_id        = aws_instance.pod.id
  port             = 80
}

# Target group for spec-editor (port 5000)
resource "aws_lb_target_group" "spec_editor" {
  name     = "${var.customer}-${var.environment}-spec-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = local.vpc_id

  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-spec-tg"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach EC2 instance to spec-editor target group
resource "aws_lb_target_group_attachment" "spec_editor" {
  target_group_arn = aws_lb_target_group.spec_editor.arn
  target_id        = aws_instance.pod.id
  port             = 5000
}

# HTTP listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.demo_app.arn
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Route /spec* to spec-editor
resource "aws_lb_listener_rule" "spec_editor" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.spec_editor.arn
  }

  condition {
    path_pattern {
      values = ["/spec", "/spec/*"]
    }
  }

  tags = {
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
