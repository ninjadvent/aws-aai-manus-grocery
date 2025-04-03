import json
import boto3
import os
import uuid
from datetime import datetime

# Initialize AWS clients
lambda_client = boto3.client('lambda')

# Get environment variables
RECEIPT_INTERPRETER_FUNCTION = os.environ['RECEIPT_INTERPRETER_FUNCTION']
EXPIRATION_DATE_ESTIMATOR_FUNCTION = os.environ['EXPIRATION_DATE_ESTIMATOR_FUNCTION']
GROCERY_TRACKER_FUNCTION = os.environ['GROCERY_TRACKER_FUNCTION']
RECIPE_RECOMMENDER_FUNCTION = os.environ['RECIPE_RECOMMENDER_FUNCTION']

def lambda_handler(event, context):
    """
    Orchestrator Lambda function to coordinate the grocery management workflow.
    
    This function:
    1. Processes incoming API Gateway requests
    2. Coordinates the workflow between different agent Lambda functions
    3. Returns the appropriate response to the client
    """
    try:
        # Determine the request type
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'GET')
        
        # Process receipt upload
        if path.endswith('/receipts') and http_method == 'POST':
            return process_receipt(event)
        
        # Get grocery inventory
        elif path.endswith('/grocery') and http_method == 'GET':
            return get_grocery_inventory(event)
        
        # Get recipe recommendations
        elif path.endswith('/recipes') and http_method == 'GET':
            return get_recipe_recommendations(event)
        
        # Handle unknown requests
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_receipt(event):
    """
    Process a receipt upload and coordinate the workflow.
    
    1. Call receipt_interpreter to extract items from receipt
    2. Call expiration_date_estimator to estimate expiration dates
    3. Return the processed items
    """
    # Step 1: Call receipt_interpreter
    receipt_response = invoke_lambda(RECEIPT_INTERPRETER_FUNCTION, event)
    
    if receipt_response.get('statusCode') != 200:
        return receipt_response
    
    # Parse the receipt response
    receipt_body = json.loads(receipt_response['body'])
    receipt_id = receipt_body.get('receipt_id')
    
    # Step 2: Call expiration_date_estimator
    expiration_event = {
        'body': json.dumps({
            'receipt_id': receipt_id
        })
    }
    
    expiration_response = invoke_lambda(EXPIRATION_DATE_ESTIMATOR_FUNCTION, expiration_event)
    
    if expiration_response.get('statusCode') != 200:
        return expiration_response
    
    # Return the final response
    return expiration_response

def get_grocery_inventory(event):
    """
    Get the current grocery inventory.
    
    Simply pass the request to the grocery_tracker function.
    """
    return invoke_lambda(GROCERY_TRACKER_FUNCTION, event)

def get_recipe_recommendations(event):
    """
    Get recipe recommendations based on available grocery items.
    
    Simply pass the request to the recipe_recommender function.
    """
    return invoke_lambda(RECIPE_RECOMMENDER_FUNCTION, event)

def invoke_lambda(function_name, event):
    """
    Invoke a Lambda function and return its response.
    """
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    # Parse the response
    payload = json.loads(response['Payload'].read().decode())
    
    return payload
