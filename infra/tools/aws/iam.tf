# IAM role for App Runner instance (runtime execution)
resource "aws_iam_role" "app_runner_instance" {
  name = "action-spec-app-runner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "action-spec-app-runner-instance-role"
  }
}

# Policy for Secrets Manager access
resource "aws_iam_role_policy" "app_runner_secrets" {
  name = "secrets-manager-access"
  role = aws_iam_role.app_runner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.github_token.arn
      }
    ]
  })
}

# Policy for CloudWatch Logs (needed for Phase 2, but harmless to add now)
resource "aws_iam_role_policy" "app_runner_logs" {
  name = "cloudwatch-logs-access"
  role = aws_iam_role.app_runner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/apprunner/*"
      }
    ]
  })
}

# IAM role for App Runner service (ECR image pull access)
resource "aws_iam_role" "app_runner_access" {
  name = "action-spec-app-runner-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "action-spec-app-runner-access-role"
  }
}

# Policy for ECR image pull
resource "aws_iam_role_policy" "app_runner_ecr" {
  name = "ecr-pull-access"
  role = aws_iam_role.app_runner_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      }
    ]
  })
}
