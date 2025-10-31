# Auto-scaling configuration
resource "aws_apprunner_auto_scaling_configuration_version" "action_spec" {
  auto_scaling_configuration_name = "action-spec-autoscaling"
  max_concurrency                 = 100
  max_size                        = var.max_instances
  min_size                        = 1

  tags = {
    Name = "action-spec-autoscaling"
  }
}

# App Runner service
resource "aws_apprunner_service" "action_spec" {
  service_name = "action-spec"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.action_spec.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8080"

        runtime_environment_variables = {
          AWS_REGION      = var.aws_region
          GH_REPO         = var.github_repo
          SPECS_PATH      = "infra"
          WORKFLOW_BRANCH = var.github_branch
        }

        runtime_environment_secrets = {
          GH_TOKEN = aws_secretsmanager_secret.github_token.arn
        }
      }
    }
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.action_spec.arn

  tags = {
    Name = "action-spec"
  }
}
