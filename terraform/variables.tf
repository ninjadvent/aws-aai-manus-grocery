variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "receipt_bucket_name" {
  description = "Name of the S3 bucket for storing receipt images"
  type        = string
  default     = "grocery-management-receipts"
}

variable "receipt_interpreter_zip" {
  description = "Path to the receipt interpreter Lambda function zip file"
  type        = string
  default     = "../lambda/receipt_interpreter.zip"
}

variable "expiration_date_estimator_zip" {
  description = "Path to the expiration date estimator Lambda function zip file"
  type        = string
  default     = "../lambda/expiration_date_estimator.zip"
}

variable "grocery_tracker_zip" {
  description = "Path to the grocery tracker Lambda function zip file"
  type        = string
  default     = "../lambda/grocery_tracker.zip"
}

variable "recipe_recommender_zip" {
  description = "Path to the recipe recommender Lambda function zip file"
  type        = string
  default     = "../lambda/recipe_recommender.zip"
}

variable "orchestrator_zip" {
  description = "Path to the orchestrator Lambda function zip file"
  type        = string
  default     = "../lambda/orchestrator.zip"
}

variable "deepseek_endpoint_name" {
  description = "Name of the SageMaker DeepSeek endpoint"
  type        = string
  default     = "deepseek-r1-endpoint"
}
