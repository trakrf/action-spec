resource "aws_secretsmanager_secret" "github_token" {
  name                    = "action-spec/github-token"
  description             = "GitHub Personal Access Token for action-spec App Runner"
  recovery_window_in_days = 7

  tags = {
    Application = "action-spec"
  }
}

resource "aws_secretsmanager_secret_version" "github_token" {
  secret_id     = aws_secretsmanager_secret.github_token.id
  secret_string = var.github_token
}
