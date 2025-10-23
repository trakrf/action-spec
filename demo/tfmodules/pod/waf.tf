# Regex pattern set for allowed paths
resource "aws_wafv2_regex_pattern_set" "allowed_paths" {
  count = var.waf_enabled ? 1 : 0

  name  = "${var.customer}-${var.environment}-allowed-paths"
  scope = "REGIONAL"

  regular_expression {
    regex_string = "^/health$"
  }

  regular_expression {
    regex_string = "^/api/v1/.*"
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-allowed-paths"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# WAF Web ACL with custom rules and managed rule groups
resource "aws_wafv2_web_acl" "main" {
  count = var.waf_enabled ? 1 : 0

  name  = "${var.customer}-${var.environment}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: Rate limiting (priority 1)
  # AWS WAF minimum: 10 requests per 1 minute (60 seconds)
  # For demo: 11th request triggers block, recovers after 1 minute
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 10
        aggregate_key_type = "IP"
        evaluation_window_sec = 60
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: Path filtering (priority 2)
  rule {
    name     = "BlockUnauthorizedPaths"
    priority = 2

    action {
      block {}
    }

    statement {
      not_statement {
        statement {
          regex_pattern_set_reference_statement {
            arn = aws_wafv2_regex_pattern_set.allowed_paths[0].arn

            field_to_match {
              uri_path {}
            }

            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-path-block"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed Rules - Common Rule Set (OWASP Top 10)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.customer}-${var.environment}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.customer}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Name        = "${var.customer}-${var.environment}-waf"
    Customer    = var.customer
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "alb" {
  count = var.waf_enabled ? 1 : 0

  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main[0].arn
}
