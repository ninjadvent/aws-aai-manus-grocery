terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  
  # Uncomment this block to use Terraform Cloud for team collaboration
  # backend "s3" {
  #   bucket = "terraform-state-grocery-management"
  #   key    = "terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}
