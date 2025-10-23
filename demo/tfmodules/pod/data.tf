# Latest Ubuntu 22.04 LTS ARM64 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  # Canonical's official public AWS account for Ubuntu AMIs
  # This is a well-known public ID, documented at:
  # https://ubuntu.com/server/docs/cloud-images/amazon-ec2
  owners = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Default VPC for demo (Phase D1 only)
data "aws_vpc" "default" {
  default = true
}

# Default subnets in default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
