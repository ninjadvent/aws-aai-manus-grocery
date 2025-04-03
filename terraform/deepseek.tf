# DeepSeek AI Integration for SageMaker

This Terraform module creates a SageMaker endpoint for DeepSeek R1 model integration.

# Note: This is a simplified version. In a real-world scenario, you would need to:
# 1. Create a SageMaker model from a pre-trained DeepSeek model
# 2. Create an endpoint configuration
# 3. Create an endpoint

resource "aws_sagemaker_model" "deepseek_model" {
  name               = "deepseek-r1-model"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    image = var.deepseek_container_image
    model_data_url = var.deepseek_model_data_url
  }
}

resource "aws_sagemaker_endpoint_configuration" "deepseek_endpoint_config" {
  name = "deepseek-r1-endpoint-config"

  production_variants {
    variant_name           = "default"
    model_name             = aws_sagemaker_model.deepseek_model.name
    instance_type          = var.deepseek_instance_type
    initial_instance_count = 1
  }
}

resource "aws_sagemaker_endpoint" "deepseek_endpoint" {
  name                 = var.deepseek_endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.deepseek_endpoint_config.name
}

# IAM role for SageMaker
resource "aws_iam_role" "sagemaker_role" {
  name = "grocery_management_sagemaker_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })
}

# Attach necessary policies to SageMaker role
resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}
