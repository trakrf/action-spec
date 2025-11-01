# Route53 DNS configuration for stable App Runner URL

# Data lookup for existing hosted zone (managed in root DNS terraform state)
data "aws_route53_zone" "trakrf_aws" {
  name         = "aws.trakrf.id"
  private_zone = false
}

# App Runner Custom Domain Association (handles SSL certificate automatically)
resource "aws_apprunner_custom_domain_association" "action_spec" {
  domain_name          = "action-spec.aws.trakrf.id"
  service_arn          = aws_apprunner_service.action_spec.arn
  enable_www_subdomain = false
}

# DNS records for ACM certificate validation (from custom domain association)
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for record in aws_apprunner_custom_domain_association.action_spec.certificate_validation_records : record.name => record
  }

  zone_id = data.aws_route53_zone.trakrf_aws.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 300
}

# CNAME record pointing to App Runner service
resource "aws_route53_record" "action_spec" {
  zone_id = data.aws_route53_zone.trakrf_aws.zone_id
  name    = "action-spec.aws.trakrf.id"
  type    = "CNAME"
  ttl     = 300
  records = [aws_apprunner_custom_domain_association.action_spec.dns_target]
}
