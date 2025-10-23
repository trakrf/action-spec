terraform {
  backend "s3" {
    bucket         = "jxp-demo-terraform-backend-store"
    key            = "demo/advworks/dev/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true

    # Credentials loaded from environment or ~/.aws/credentials
  }
}
