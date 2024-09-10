resource "aws_ecr_repository" "server" {
  name = "x-remove-server"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = var.project_tag
  }
}

output "repository_url" {
  value = aws_ecr_repository.server.repository_url
  description = "The URL of the ECR repository"
}
