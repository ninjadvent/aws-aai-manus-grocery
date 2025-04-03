#!/bin/bash
# deploy.sh - Automated deployment script for Grocery Management Agents System
# This script automates the deployment process by:
# 1. Installing dependencies
# 2. Packaging Lambda functions
# 3. Running Terraform commands

set -e  # Exit on any error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored status messages
function echo_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
function check_prerequisites() {
    echo_status "Checking prerequisites..."
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo_error "Python 3 is required but not installed. Please install Python 3."
        exit 1
    fi
    
    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        echo_error "pip3 is required but not installed. Please install pip3."
        exit 1
    fi
    
    # Check for Terraform
    if ! command -v terraform &> /dev/null; then
        echo_error "Terraform is required but not installed. Please install Terraform."
        exit 1
    fi
    
    # Check for AWS CLI
    if ! command -v aws &> /dev/null; then
        echo_warning "AWS CLI is not installed. It's recommended for deployment."
        read -p "Continue without AWS CLI? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        # Check AWS credentials
        if ! aws sts get-caller-identity &> /dev/null; then
            echo_warning "AWS credentials not configured or invalid."
            read -p "Continue without valid AWS credentials? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
    
    echo_status "All prerequisites checked."
}

# Install dependencies
function install_dependencies() {
    echo_status "Installing dependencies..."
    
    # Create and activate virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install required packages
    pip3 install -r requirements.txt
    
    echo_status "Dependencies installed successfully."
}

# Package Lambda functions
function package_lambda_functions() {
    echo_status "Packaging Lambda functions..."
    
    # Create directories for zip files
    mkdir -p lambda/dist
    
    # Install dependencies to each Lambda directory
    echo_status "Installing dependencies for Lambda functions..."
    pip3 install boto3 crewai python-dotenv -t lambda/common/
    
    # Package each Lambda function
    echo_status "Creating Lambda packages..."
    
    # Receipt Interpreter Lambda
    echo_status "Packaging receipt_interpreter Lambda..."
    cd lambda/receipt_interpreter
    zip -r ../dist/receipt_interpreter.zip .
    cd ../..
    
    # Expiration Date Estimator Lambda
    echo_status "Packaging expiration_date_estimator Lambda..."
    cd lambda/expiration_date_estimator
    zip -r ../dist/expiration_date_estimator.zip .
    cd ../..
    
    # Grocery Tracker Lambda
    echo_status "Packaging grocery_tracker Lambda..."
    cd lambda/grocery_tracker
    zip -r ../dist/grocery_tracker.zip .
    cd ../..
    
    # Recipe Recommender Lambda
    echo_status "Packaging recipe_recommender Lambda..."
    cd lambda/recipe_recommender
    zip -r ../dist/recipe_recommender.zip .
    cd ../..
    
    # Orchestrator Lambda
    echo_status "Packaging orchestrator Lambda..."
    cd lambda/orchestrator
    zip -r ../dist/orchestrator.zip .
    cd ../..
    
    # Add common code to each Lambda package
    echo_status "Adding common code to Lambda packages..."
    cd lambda/common
    zip -r ../dist/receipt_interpreter.zip .
    zip -r ../dist/expiration_date_estimator.zip .
    zip -r ../dist/grocery_tracker.zip .
    zip -r ../dist/recipe_recommender.zip .
    zip -r ../dist/orchestrator.zip .
    cd ../..
    
    echo_status "Lambda functions packaged successfully."
}

# Deploy with Terraform
function deploy_with_terraform() {
    echo_status "Deploying with Terraform..."
    
    # Navigate to Terraform directory
    cd terraform
    
    # Initialize Terraform
    echo_status "Initializing Terraform..."
    terraform init
    
    # Create terraform.tfvars if it doesn't exist
    if [ ! -f "terraform.tfvars" ]; then
        echo_status "Creating terraform.tfvars file..."
        cat > terraform.tfvars << EOF
aws_region = "us-east-1"
environment = "dev"
receipt_bucket_name = "grocery-management-receipts-$(date +%s)"
deepseek_endpoint_name = "deepseek-r1-endpoint"
EOF
        echo_status "Created terraform.tfvars with default values."
        echo_warning "You may want to edit terraform.tfvars to customize your deployment."
        read -p "Continue with default values? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo_status "Please edit terraform.tfvars and run the script again."
            exit 0
        fi
    fi
    
    # Plan Terraform deployment
    echo_status "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Confirm deployment
    read -p "Proceed with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_status "Deployment cancelled."
        exit 0
    fi
    
    # Apply Terraform deployment
    echo_status "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Return to root directory
    cd ..
    
    echo_status "Terraform deployment completed successfully."
}

# Main function
function main() {
    echo_status "Starting automated deployment of Grocery Management Agents System..."
    
    # Check prerequisites
    check_prerequisites
    
    # Install dependencies
    install_dependencies
    
    # Package Lambda functions
    package_lambda_functions
    
    # Deploy with Terraform
    deploy_with_terraform
    
    echo_status "Deployment completed successfully!"
    echo_status "Your Grocery Management Agents System is now deployed and ready to use."
    echo_status "API Gateway URL can be found in the Terraform outputs above."
}

# Run the main function
main
