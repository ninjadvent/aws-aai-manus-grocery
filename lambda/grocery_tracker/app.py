import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Get environment variables
GROCERY_TABLE = os.environ['GROCERY_TABLE']

def lambda_handler(event, context):
    """
    Lambda function to track grocery inventory.
    
    This function:
    1. Handles GET requests to retrieve current grocery inventory
    2. Handles DELETE requests to remove consumed items
    3. Returns inventory status including expiring items
    """
    try:
        # Determine the HTTP method
        http_method = event.get('httpMethod', 'GET')
        
        if http_method == 'GET':
            # Get query parameters
            query_params = event.get('queryStringParameters', {}) or {}
            
            # Check if we need to filter by expiration date
            days_to_expiration = None
            if 'expiring_within_days' in query_params:
                try:
                    days_to_expiration = int(query_params['expiring_within_days'])
                except ValueError:
                    pass
            
            # Get the grocery inventory
            inventory = get_grocery_inventory(days_to_expiration)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'items_count': len(inventory),
                    'items': inventory
                })
            }
        
        elif http_method == 'DELETE':
            # Parse the incoming event body
            body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
            
            # Get the item ID to remove
            item_id = body.get('item_id')
            if not item_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No item_id provided'})
                }
            
            # Remove the item from inventory
            remove_grocery_item(item_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Item {item_id} removed from inventory',
                    'item_id': item_id
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_grocery_inventory(days_to_expiration=None):
    """
    Retrieve the current grocery inventory from DynamoDB.
    
    If days_to_expiration is provided, only return items expiring within that many days.
    """
    table = dynamodb.Table(GROCERY_TABLE)
    
    # Get all items from the table
    response = table.scan()
    items = response.get('Items', [])
    
    # Continue scanning if we have more items (pagination)
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    # If we need to filter by expiration date
    if days_to_expiration is not None:
        today = datetime.now().date()
        filtered_items = []
        
        for item in items:
            # Skip items without expiration date
            if 'ExpirationDate' not in item:
                continue
            
            try:
                expiration_date = datetime.strptime(item['ExpirationDate'], "%Y-%m-%d").date()
                days_until_expiration = (expiration_date - today).days
                
                if 0 <= days_until_expiration <= days_to_expiration:
                    # Add days until expiration to the item
                    item['DaysUntilExpiration'] = days_until_expiration
                    filtered_items.append(item)
            except ValueError:
                # Skip items with invalid expiration date format
                continue
        
        return filtered_items
    
    return items

def remove_grocery_item(item_id):
    """
    Remove a grocery item from DynamoDB (mark as consumed).
    """
    table = dynamodb.Table(GROCERY_TABLE)
    
    # Delete the item from DynamoDB
    table.delete_item(
        Key={
            'ItemId': item_id
        }
    )
