import json
import boto3
import os
from datetime import datetime, timedelta

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
GROCERY_TABLE = os.environ['GROCERY_TABLE']
DEEPSEEK_ENDPOINT = os.environ['DEEPSEEK_ENDPOINT']

def lambda_handler(event, context):
    """
    Lambda function to estimate expiration dates for grocery items.
    
    This function:
    1. Retrieves grocery items from DynamoDB
    2. Uses DeepSeek AI to estimate expiration dates
    3. Updates the items in DynamoDB with the estimated expiration dates
    """
    try:
        # Parse the incoming event
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Get the receipt ID
        receipt_id = body.get('receipt_id')
        if not receipt_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No receipt_id provided'})
            }
        
        # Get the grocery items for this receipt
        grocery_items = get_grocery_items(receipt_id)
        
        if not grocery_items:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'No items found for receipt_id: {receipt_id}'})
            }
        
        # Estimate expiration dates for the items
        updated_items = estimate_expiration_dates(grocery_items)
        
        # Update the items in DynamoDB
        update_grocery_items(updated_items)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'receipt_id': receipt_id,
                'items_count': len(updated_items),
                'items': updated_items
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_grocery_items(receipt_id):
    """
    Retrieve grocery items from DynamoDB for a specific receipt.
    """
    table = dynamodb.Table(GROCERY_TABLE)
    
    # Query items by receipt ID
    response = table.scan(
        FilterExpression="ReceiptId = :receipt_id",
        ExpressionAttributeValues={
            ":receipt_id": receipt_id
        }
    )
    
    return response.get('Items', [])

def estimate_expiration_dates(grocery_items):
    """
    Use DeepSeek AI to estimate expiration dates for grocery items.
    """
    updated_items = []
    
    # Prepare the list of items for DeepSeek
    items_list = "\n".join([f"{item['Name']}" for item in grocery_items])
    
    # Prepare the prompt for DeepSeek
    prompt = f"""
    You are an expert at estimating expiration dates for grocery items.
    Please estimate the typical shelf life (in days) for each of the following grocery items:
    
    {items_list}
    
    For each item, provide only the name and the number of days until expiration.
    Format your response as: "Item name: X days"
    """
    
    # Prepare the payload for DeepSeek
    payload = {
        "prompt": prompt,
        "max_tokens": 1000,
        "temperature": 0.2
    }
    
    # Invoke the DeepSeek endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=DEEPSEEK_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    # Parse the response
    result = json.loads(response['Body'].read().decode())
    
    # Extract the expiration estimates from the response
    if 'generated_text' in result:
        expiration_text = result['generated_text']
        expiration_estimates = parse_expiration_estimates(expiration_text)
        
        # Update the grocery items with expiration dates
        for item in grocery_items:
            item_name = item['Name']
            if item_name in expiration_estimates:
                days = expiration_estimates[item_name]
                purchase_date = datetime.strptime(item['PurchaseDate'], "%Y-%m-%d")
                expiration_date = purchase_date + timedelta(days=days)
                
                # Add expiration date to the item
                item['ExpirationDate'] = expiration_date.strftime("%Y-%m-%d")
                item['ShelfLifeDays'] = days
            else:
                # Default expiration date (7 days) if not found
                purchase_date = datetime.strptime(item['PurchaseDate'], "%Y-%m-%d")
                expiration_date = purchase_date + timedelta(days=7)
                
                item['ExpirationDate'] = expiration_date.strftime("%Y-%m-%d")
                item['ShelfLifeDays'] = 7
            
            updated_items.append(item)
    else:
        raise Exception("Failed to estimate expiration dates")
    
    return updated_items

def parse_expiration_estimates(expiration_text):
    """
    Parse the expiration estimates from the DeepSeek response.
    """
    estimates = {}
    
    # Split the text into lines
    lines = expiration_text.strip().split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Try to extract item name and days
        parts = line.split(':', 1)
        if len(parts) == 2:
            item_name = parts[0].strip()
            days_text = parts[1].strip()
            
            # Extract the number of days
            import re
            days_match = re.search(r'(\d+)', days_text)
            if days_match:
                days = int(days_match.group(1))
                estimates[item_name] = days
    
    return estimates

def update_grocery_items(grocery_items):
    """
    Update the grocery items in DynamoDB with expiration dates.
    """
    table = dynamodb.Table(GROCERY_TABLE)
    
    for item in grocery_items:
        # Update the item in DynamoDB
        table.update_item(
            Key={
                'ItemId': item['ItemId']
            },
            UpdateExpression="set ExpirationDate = :ed, ShelfLifeDays = :sld, UpdatedAt = :ua",
            ExpressionAttributeValues={
                ':ed': item['ExpirationDate'],
                ':sld': item['ShelfLifeDays'],
                ':ua': datetime.now().isoformat()
            }
        )
