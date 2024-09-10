resource "aws_iam_role" "ec2_ecr_read_role" {
  name = "x-remove-ec2-ecr-read-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = {
    Project = var.project_tag
  }
}

resource "aws_iam_role_policy" "ec2_ecr_read_policy" {
  name = "x-remove-ec2-ecr-read-policy"
  role = aws_iam_role.ec2_ecr_read_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.server.arn
      },
      {
        Effect = "Allow"
        Action = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
            "Sid": "IamPassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "ec2.amazonaws.com"
                }
            }
        },
        {
            "Sid": "ListEc2AndListInstanceProfiles",
            "Effect": "Allow",
            "Action": [
                "iam:ListInstanceProfiles",
                "ec2:Describe*",
                "ec2:Search*",
                "ec2:Get*"
            ],
            "Resource": "*"
        }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_ecr_read_instance_profile" {
  name = "x-remove-ec2-ecr-read-instance-profile"
  role = aws_iam_role.ec2_ecr_read_role.name
  tags = {
    Project = var.project_tag
  }
}

output "ec2_ecr_read_instance_profile_name" {
  value = aws_iam_instance_profile.ec2_ecr_read_instance_profile.name
  description = "The name of the instance profile that allows EC2 instances to read from the ECR repository"
}
output "ec2_ecr_read_role_name" {
  value = aws_iam_role.ec2_ecr_read_role.name
  description = "The name of the IAM role that allows EC2 instances to read from the ECR repository"
}