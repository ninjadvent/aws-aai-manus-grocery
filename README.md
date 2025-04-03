# Grocery Management Agents System

This repository contains the implementation of a Grocery Management Agents System using AWS services and CrewAI with DeepSeek integration.

## System Architecture

The system uses the following AWS services:
- API Gateway for API endpoints
- Lambda for serverless functions
- DynamoDB for data storage
- S3 for receipt image storage
- SageMaker for DeepSeek AI model hosting

The infrastructure is defined using Terraform for automated deployment.

## Agent Components

The system consists of four specialized AI agents:

1. **Receipt Interpreter Agent** - Extracts grocery items from receipt images
2. **Expiration Date Estimator Agent** - Predicts when items will expire
3. **Grocery Tracker Agent** - Maintains inventory of groceries
4. **Recipe Recommendation Agent** - Suggests recipes based on available items

These agents are orchestrated using CrewAI to work together in a coordinated workflow.

## Directory Structure

```
grocery_management_system/
├── terraform/           # Terraform configuration files
├── lambda/              # Lambda function code
│   ├── receipt_interpreter/
│   ├── expiration_date_estimator/
│   ├── grocery_tracker/
│   ├── recipe_recommender/
│   ├── orchestrator/
│   └── common/          # Shared code
└── docs/                # Documentation
```

## Deployment

See [deployment instructions](docs/deployment.md) for details on how to deploy this system to AWS.

## API Endpoints

Once deployed, the system provides the following API endpoints:

- `POST /receipts` - Upload a receipt image for processing
- `GET /grocery` - Get the current grocery inventory
- `GET /recipes` - Get recipe recommendations based on available ingredients

## Development

This project was developed based on the architecture described in the AWS blog post: [Build Agentic AI Solutions with DeepSeek R1, CrewAI, and Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/build-agentic-ai-solutions-with-deepseek-r1-crewai-and-amazon-sagemaker-ai/)
