variable "deepseek_container_image" {
  description = "Container image for DeepSeek model"
  type        = string
  default     = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04"
}

variable "deepseek_model_data_url" {
  description = "S3 URL for the DeepSeek model data"
  type        = string
  default     = "s3://sagemaker-models/deepseek-r1/model.tar.gz"
}

variable "deepseek_instance_type" {
  description = "Instance type for DeepSeek SageMaker endpoint"
  type        = string
  default     = "ml.g5.2xlarge"
}
