# Deployment Instructions

This document provides instructions for deploying the Grocery Management Agents System to AWS using Terraform.

## Prerequisites

1. AWS CLI installed and configured with appropriate credentials
2. Terraform CLI installed (version 1.0.0 or later)
3. Git installed
4. Python 3.9 or later

## Automated Deployment

We've created an automated deployment script that handles all the steps for you, including installing dependencies, packaging Lambda functions, and deploying with Terraform.

### 1. Clone the Repository

```bash
git clone https://github.com/ninjadvent/aws-aai-manus-grocery.git
cd aws-aai-manus-grocery
```

### 2. Run the Automated Deployment Script

Simply execute the deployment script:

```bash
./deploy.sh
```

The script will:
- Check for required prerequisites
- Install all dependencies in a virtual environment
- Package all Lambda functions automatically
- Create and configure Terraform variables if needed
- Initialize Terraform and plan the deployment
- Deploy the infrastructure after your confirmation

The entire process is interactive and will prompt you at key decision points.

## Manual Deployment (Alternative)

If you prefer to deploy manually or need more control over individual steps, follow these instructions:

### 1. Prepare Lambda Function Packages

Before deploying with Terraform, you need to create ZIP packages for each Lambda function:

```bash
# Install dependencies
pip install -r requirements.txt

# Create directories for zip files
mkdir -p lambda/dist

# Package receipt_interpreter Lambda
cd lambda/receipt_interpreter
zip -r ../dist/receipt_interpreter.zip .
cd ../..

# Package expiration_date_estimator Lambda
cd lambda/expiration_date_estimator
zip -r ../dist/expiration_date_estimator.zip .
cd ../..

# Package grocery_tracker Lambda
cd lambda/grocery_tracker
zip -r ../dist/grocery_tracker.zip .
cd ../..

# Package recipe_recommender Lambda
cd lambda/recipe_recommender
zip -r ../dist/recipe_recommender.zip .
cd ../..

# Package orchestrator Lambda
cd lambda/orchestrator
zip -r ../dist/orchestrator.zip .
cd ../..

# Package common code into each Lambda
cd lambda/common
zip -r ../dist/receipt_interpreter.zip .
zip -r ../dist/expiration_date_estimator.zip .
zip -r ../dist/grocery_tracker.zip .
zip -r ../dist/recipe_recommender.zip .
zip -r ../dist/orchestrator.zip .
cd ../..
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Configure Terraform Variables

Create a `terraform.tfvars` file to customize your deployment:

```
aws_region = "us-east-1"
environment = "dev"
receipt_bucket_name = "your-grocery-receipts-bucket"
deepseek_endpoint_name = "your-deepseek-endpoint"
```

### 4. Deploy with Terraform

```bash
terraform plan
terraform apply
```

Review the plan and confirm the deployment by typing `yes` when prompted.

## Testing the Deployment

After deployment completes, Terraform will output the API Gateway URL. You can test the API using curl or Postman:

```bash
# Upload a receipt image
curl -X POST \
  https://your-api-url/dev/receipts \
  -H 'Content-Type: application/json' \
  -d '{
    "image": "base64_encoded_image_data"
  }'

# Get grocery inventory
curl -X GET https://your-api-url/dev/grocery

# Get recipe recommendations
curl -X GET https://your-api-url/dev/recipes
```

## Clean Up

To remove all resources created by Terraform:

```bash
# Using the automated script
./deploy.sh cleanup

# Or manually
cd terraform
terraform destroy
```

## Notes on DeepSeek Integration

The DeepSeek model is deployed as a SageMaker endpoint. This requires:

1. A pre-trained DeepSeek model in an S3 bucket
2. Appropriate IAM permissions for SageMaker
3. GPU instances for model hosting (which can be expensive)

For development and testing, you may want to use a smaller model or mock the DeepSeek integration.

## Troubleshooting

If you encounter issues during deployment:

1. Check CloudWatch Logs for Lambda function errors
2. Verify IAM permissions are correctly configured
3. Ensure SageMaker endpoint is properly deployed and running
4. Check that all required environment variables are set correctly

If the automated deployment script fails:
1. Check the error message for specific issues
2. Try running individual sections of the manual deployment to isolate the problem
3. Ensure you have the necessary permissions for all AWS services used
