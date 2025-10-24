terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "demo/contoso/dev/terraform.tfstate"
    region         = "us-west-2" # Bucket location (separate from provider region)
    dynamodb_table = "terraform-lock"
    encrypt        = true

    # Credentials loaded from environment or ~/.aws/credentials
  }
}
