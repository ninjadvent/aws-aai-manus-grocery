#!/bin/bash

# This script prepares the Lambda function packages for deployment

# Create directories for zip files
mkdir -p lambda/dist

# Install required dependencies
pip install crewai boto3 -t lambda/common/
pip install crewai boto3 -t lambda/receipt_interpreter/
pip install crewai boto3 -t lambda/expiration_date_estimator/
pip install crewai boto3 -t lambda/grocery_tracker/
pip install crewai boto3 -t lambda/recipe_recommender/
pip install crewai boto3 -t lambda/orchestrator/

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

echo "Lambda packages created successfully in lambda/dist/"
