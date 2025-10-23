resource "aws_instance" "pod" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  # Use specified or default subnet
  subnet_id = local.subnet_id

  # SSH key for debugging access
  key_name = var.ssh_key_name

  # Assign public IP for demo access
  associate_public_ip_address = true

  # Security group (default or override)
  vpc_security_group_ids = [local.security_group_id]

  # User data: Install Docker and run http-echo
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Add additional SSH key to ubuntu user
    echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIsrQEHKvwPZI8lOBF1j7t9pMUW28pRAZ914BjTnAwW7 mike@kwyk.net" >> /home/ubuntu/.ssh/authorized_keys

    # Install Docker via official script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh

    # Run http-echo on port 80
    docker run -d \
      --name demo-app \
      --restart unless-stopped \
      -p 80:5678 \
      hashicorp/http-echo:latest \
      -text="${var.demo_message}"

    # Log completion
    echo "User data completed at $(date)" >> /var/log/user-data.log
  EOF

  # Customer-specific naming convention
  tags = {
    Name         = "${var.customer}-${var.environment}-${var.instance_name}"
    Customer     = var.customer
    Environment  = var.environment
    ManagedBy    = "Terraform"
    InstanceName = var.instance_name
  }

  # Enable detailed monitoring (helpful for debugging)
  monitoring = true

  # Instance metadata service v2 (security best practice)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
}
