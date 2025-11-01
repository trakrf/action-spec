# OAuth Client Secret (replaces service account PAT)
resource "aws_secretsmanager_secret" "github_oauth_client_secret" {
  name                    = "action-spec/github-oauth-client-secret"
  description             = "GitHub OAuth App client secret for user authentication"
  recovery_window_in_days = 7

  tags = {
    Application = "action-spec"
  }
}

resource "aws_secretsmanager_secret_version" "github_oauth_client_secret" {
  secret_id     = aws_secretsmanager_secret.github_oauth_client_secret.id
  secret_string = var.github_oauth_client_secret
}
