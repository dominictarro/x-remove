data "aws_region" "current" {}

provider "aws" {
    region = "us-east-1"
}

variable "project_tag" {
  type = string
  description = "A tag to identify resources used for x-remove.cc"
  default = "x-remove"
}