# ECR repository for action-spec Docker images
resource "aws_ecr_repository" "action_spec" {
  name                 = "action-spec"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "action-spec"
  }
}

# Lifecycle policy to keep last 10 images and remove untagged images after 1 day
resource "aws_ecr_lifecycle_policy" "action_spec" {
  repository = aws_ecr_repository.action_spec.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "main-", "prod-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
