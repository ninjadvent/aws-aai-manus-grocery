import json
import os
from common.grocery_crew import GroceryManagementCrew

def lambda_handler(event, context):
    """
    Lambda function to orchestrate the grocery management workflow using CrewAI.
    
    This function:
    1. Processes incoming API Gateway requests
    2. Initializes the GroceryManagementCrew
    3. Executes the appropriate workflow
    4. Returns the results to the client
    """
    try:
        # Parse the incoming event
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'GET')
        
        # Process receipt upload
        if path.endswith('/receipts') and http_method == 'POST':
            # Parse the body
            body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
            
            # Get the receipt image data
            if 'image' not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No image provided'})
                }
            
            receipt_image_base64 = body['image']
            
            # Initialize the crew
            crew = GroceryManagementCrew()
            
            # Process the receipt
            result = crew.process_receipt(receipt_image_base64)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        
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
