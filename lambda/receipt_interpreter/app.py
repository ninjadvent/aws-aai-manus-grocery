import json
import boto3
import base64
import os
import uuid
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
RECEIPT_BUCKET = os.environ['RECEIPT_BUCKET']
GROCERY_TABLE = os.environ['GROCERY_TABLE']
DEEPSEEK_ENDPOINT = os.environ['DEEPSEEK_ENDPOINT']

def lambda_handler(event, context):
    """
    Lambda function to interpret receipt images and extract grocery items.
    
    This function:
    1. Receives a base64 encoded image from API Gateway
    2. Saves the image to S3
    3. Uses DeepSeek AI to extract text from the receipt
    4. Parses the text to identify grocery items
    5. Stores the items in DynamoDB
    """
    try:
        # Parse the incoming event
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Get the base64 encoded image
        if 'image' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No image provided'})
            }
        
        image_data = body['image']
        image_content = base64.b64decode(image_data)
        
        # Generate a unique filename
        receipt_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{receipt_id}-{timestamp}.jpg"
        
        # Upload the image to S3
        s3.put_object(
            Bucket=RECEIPT_BUCKET,
            Key=filename,
            Body=image_content,
            ContentType='image/jpeg'
        )
        
        # Get the S3 URL
        s3_url = f"s3://{RECEIPT_BUCKET}/{filename}"
        
        # Extract text from the receipt using DeepSeek AI
        receipt_text = extract_text_from_receipt(image_content)
        
        # Parse the receipt text to identify grocery items
        grocery_items = parse_receipt_text(receipt_text)
        
        # Store the items in DynamoDB
        store_grocery_items(receipt_id, grocery_items)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'receipt_id': receipt_id,
                'items_count': len(grocery_items),
                'items': grocery_items
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def extract_text_from_receipt(image_content):
    """
    Use DeepSeek AI to extract text from the receipt image.
    """
    # Prepare the prompt for DeepSeek
    prompt = """
    You are an expert at extracting information from grocery receipts.
    Please analyze this receipt image and extract all grocery items with their prices.
    Format the output as a list of items, one per line, with the item name followed by the price.
    """
    
    # Prepare the payload for DeepSeek
    payload = {
        "prompt": prompt,
        "image_base64": base64.b64encode(image_content).decode('utf-8'),
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
    
    # Extract the text from the response
    if 'generated_text' in result:
        return result['generated_text']
    else:
        raise Exception("Failed to extract text from receipt")

def parse_receipt_text(receipt_text):
    """
    Parse the receipt text to identify grocery items.
    
    This is a simplified implementation. In a real-world scenario,
    you would use more sophisticated NLP techniques or DeepSeek AI
    to accurately parse the receipt text.
    """
    grocery_items = []
    
    # Split the text into lines
    lines = receipt_text.strip().split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Try to extract item name and price
        parts = line.strip().rsplit(' ', 1)
        if len(parts) == 2:
            item_name = parts[0].strip()
            price_str = parts[1].strip().replace('$', '')
            
            try:
                price = float(price_str)
                
                # Create a grocery item
                grocery_item = {
                    'name': item_name,
                    'price': price,
                    'purchase_date': datetime.now().strftime("%Y-%m-%d")
                }
                
                grocery_items.append(grocery_item)
            except ValueError:
                # Skip lines where price cannot be parsed
                continue
    
    return grocery_items

def store_grocery_items(receipt_id, grocery_items):
    """
    Store the grocery items in DynamoDB.
    """
    table = dynamodb.Table(GROCERY_TABLE)
    
    for i, item in enumerate(grocery_items):
        # Generate a unique ID for each item
        item_id = f"{receipt_id}-{i+1}"
        
        # Prepare the item for DynamoDB
        db_item = {
            'ItemId': item_id,
            'ReceiptId': receipt_id,
            'Name': item['name'],
            'Price': item['price'],
            'PurchaseDate': item['purchase_date'],
            'CreatedAt': datetime.now().isoformat()
        }
        
        # Put the item in DynamoDB
        table.put_item(Item=db_item)
