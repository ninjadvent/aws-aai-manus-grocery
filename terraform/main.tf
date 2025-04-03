provider "aws" {
  region = var.aws_region
}

# S3 bucket for storing receipt images
resource "aws_s3_bucket" "receipt_bucket" {
  bucket = var.receipt_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "receipt_bucket_ownership" {
  bucket = aws_s3_bucket.receipt_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "receipt_bucket_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.receipt_bucket_ownership]
  bucket = aws_s3_bucket.receipt_bucket.id
  acl    = "private"
}

# DynamoDB tables for storing grocery data
resource "aws_dynamodb_table" "grocery_items" {
  name           = "GroceryItems"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "ItemId"
  
  attribute {
    name = "ItemId"
    type = "S"
  }

  tags = {
    Name        = "GroceryItems"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "recipes" {
  name           = "Recipes"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "RecipeId"
  
  attribute {
    name = "RecipeId"
    type = "S"
  }

  tags = {
    Name        = "Recipes"
    Environment = var.environment
  }
}

# IAM role for Lambda functions
resource "aws_iam_role" "lambda_role" {
  name = "grocery_management_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda functions
resource "aws_iam_policy" "lambda_policy" {
  name        = "grocery_management_lambda_policy"
  description = "Policy for grocery management lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "${aws_s3_bucket.receipt_bucket.arn}",
          "${aws_s3_bucket.receipt_bucket.arn}/*"
        ]
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = [
          "${aws_dynamodb_table.grocery_items.arn}",
          "${aws_dynamodb_table.recipes.arn}"
        ]
      },
      {
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Lambda functions for each agent
resource "aws_lambda_function" "receipt_interpreter" {
  function_name    = "receipt_interpreter"
  filename         = var.receipt_interpreter_zip
  source_code_hash = filebase64sha256(var.receipt_interpreter_zip)
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      RECEIPT_BUCKET = aws_s3_bucket.receipt_bucket.bucket
      GROCERY_TABLE  = aws_dynamodb_table.grocery_items.name
      DEEPSEEK_ENDPOINT = var.deepseek_endpoint_name
    }
  }
}

resource "aws_lambda_function" "expiration_date_estimator" {
  function_name    = "expiration_date_estimator"
  filename         = var.expiration_date_estimator_zip
  source_code_hash = filebase64sha256(var.expiration_date_estimator_zip)
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      GROCERY_TABLE  = aws_dynamodb_table.grocery_items.name
      DEEPSEEK_ENDPOINT = var.deepseek_endpoint_name
    }
  }
}

resource "aws_lambda_function" "grocery_tracker" {
  function_name    = "grocery_tracker"
  filename         = var.grocery_tracker_zip
  source_code_hash = filebase64sha256(var.grocery_tracker_zip)
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      GROCERY_TABLE  = aws_dynamodb_table.grocery_items.name
    }
  }
}

resource "aws_lambda_function" "recipe_recommender" {
  function_name    = "recipe_recommender"
  filename         = var.recipe_recommender_zip
  source_code_hash = filebase64sha256(var.recipe_recommender_zip)
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      GROCERY_TABLE  = aws_dynamodb_table.grocery_items.name
      RECIPE_TABLE   = aws_dynamodb_table.recipes.name
      DEEPSEEK_ENDPOINT = var.deepseek_endpoint_name
    }
  }
}

resource "aws_lambda_function" "orchestrator" {
  function_name    = "grocery_management_orchestrator"
  filename         = var.orchestrator_zip
  source_code_hash = filebase64sha256(var.orchestrator_zip)
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      RECEIPT_INTERPRETER_FUNCTION = aws_lambda_function.receipt_interpreter.function_name
      EXPIRATION_DATE_ESTIMATOR_FUNCTION = aws_lambda_function.expiration_date_estimator.function_name
      GROCERY_TRACKER_FUNCTION = aws_lambda_function.grocery_tracker.function_name
      RECIPE_RECOMMENDER_FUNCTION = aws_lambda_function.recipe_recommender.function_name
      DEEPSEEK_ENDPOINT = var.deepseek_endpoint_name
    }
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "grocery_api" {
  name        = "GroceryManagementAPI"
  description = "API for Grocery Management System"
}

# API Gateway resources
resource "aws_api_gateway_resource" "receipts" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  parent_id   = aws_api_gateway_rest_api.grocery_api.root_resource_id
  path_part   = "receipts"
}

resource "aws_api_gateway_resource" "grocery" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  parent_id   = aws_api_gateway_rest_api.grocery_api.root_resource_id
  path_part   = "grocery"
}

resource "aws_api_gateway_resource" "recipes" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  parent_id   = aws_api_gateway_rest_api.grocery_api.root_resource_id
  path_part   = "recipes"
}

# API Gateway methods for receipts
resource "aws_api_gateway_method" "post_receipt" {
  rest_api_id   = aws_api_gateway_rest_api.grocery_api.id
  resource_id   = aws_api_gateway_resource.receipts.id
  http_method   = "POST"
  authorization_type = "NONE"
}

resource "aws_api_gateway_integration" "post_receipt_integration" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  resource_id = aws_api_gateway_resource.receipts.id
  http_method = aws_api_gateway_method.post_receipt.http_method
  
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.orchestrator.invoke_arn
}

# API Gateway methods for grocery
resource "aws_api_gateway_method" "get_grocery" {
  rest_api_id   = aws_api_gateway_rest_api.grocery_api.id
  resource_id   = aws_api_gateway_resource.grocery.id
  http_method   = "GET"
  authorization_type = "NONE"
}

resource "aws_api_gateway_integration" "get_grocery_integration" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  resource_id = aws_api_gateway_resource.grocery.id
  http_method = aws_api_gateway_method.get_grocery.http_method
  
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.grocery_tracker.invoke_arn
}

# API Gateway methods for recipes
resource "aws_api_gateway_method" "get_recipes" {
  rest_api_id   = aws_api_gateway_rest_api.grocery_api.id
  resource_id   = aws_api_gateway_resource.recipes.id
  http_method   = "GET"
  authorization_type = "NONE"
}

resource "aws_api_gateway_integration" "get_recipes_integration" {
  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  resource_id = aws_api_gateway_resource.recipes.id
  http_method = aws_api_gateway_method.get_recipes.http_method
  
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.recipe_recommender.invoke_arn
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "grocery_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.post_receipt_integration,
    aws_api_gateway_integration.get_grocery_integration,
    aws_api_gateway_integration.get_recipes_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.grocery_api.id
  stage_name  = var.environment
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "orchestrator_api_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestrator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.grocery_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "grocery_tracker_api_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.grocery_tracker.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.grocery_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "recipe_recommender_api_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recipe_recommender.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.grocery_api.execution_arn}/*/*"
}

# Output the API Gateway URL
output "api_url" {
  value = "${aws_api_gateway_deployment.grocery_api_deployment.invoke_url}"
}
