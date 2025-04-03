import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
GROCERY_TABLE = os.environ['GROCERY_TABLE']
RECIPE_TABLE = os.environ['RECIPE_TABLE']
DEEPSEEK_ENDPOINT = os.environ['DEEPSEEK_ENDPOINT']

def lambda_handler(event, context):
    """
    Lambda function to recommend recipes based on available grocery items.
    
    This function:
    1. Retrieves current grocery inventory
    2. Uses DeepSeek AI to generate recipe recommendations
    3. Stores the recipes in DynamoDB
    4. Returns the recommended recipes
    """
    try:
        # Determine the HTTP method
        http_method = event.get('httpMethod', 'GET')
        
        if http_method == 'GET':
            # Get query parameters
            query_params = event.get('queryStringParameters', {}) or {}
            
            # Check if we need to filter by expiring items
            use_expiring = query_params.get('use_expiring', 'false').lower() == 'true'
            days_to_expiration = None
            if use_expiring and 'expiring_within_days' in query_params:
                try:
                    days_to_expiration = int(query_params['expiring_within_days'])
                except ValueError:
                    days_to_expiration = 3  # Default to 3 days
            
            # Get the grocery inventory
            inventory = get_grocery_inventory(days_to_expiration if use_expiring else None)
            
            if not inventory:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'No grocery items found'})
                }
            
            # Generate recipe recommendations
            recipes = generate_recipe_recommendations(inventory)
            
            # Store the recipes in DynamoDB
            store_recipes(recipes)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'recipes_count': len(recipes),
                    'recipes': recipes
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

def generate_recipe_recommendations(inventory):
    """
    Use DeepSeek AI to generate recipe recommendations based on available grocery items.
    """
    # Extract item names from inventory
    item_names = [item['Name'] for item in inventory]
    items_list = ", ".join(item_names)
    
    # Prepare the prompt for DeepSeek
    prompt = f"""
    You are a creative chef who specializes in creating recipes from available ingredients.
    Please suggest 3 recipes that can be made using some or all of the following ingredients:
    
    {items_list}
    
    For each recipe, provide:
    1. Recipe name
    2. Ingredients needed (indicate which ones are from the provided list)
    3. Brief cooking instructions
    4. Approximate cooking time
    
    Format your response as JSON with the following structure:
    {{
        "recipes": [
            {{
                "name": "Recipe Name",
                "ingredients": ["Ingredient 1", "Ingredient 2", ...],
                "instructions": "Brief cooking instructions",
                "cooking_time_minutes": 30
            }},
            ...
        ]
    }}
    """
    
    # Prepare the payload for DeepSeek
    payload = {
        "prompt": prompt,
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    # Invoke the DeepSeek endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=DEEPSEEK_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    # Parse the response
    result = json.loads(response['Body'].read().decode())
    
    # Extract the recipes from the response
    if 'generated_text' in result:
        recipes_text = result['generated_text']
        
        # Extract JSON from the text
        import re
        json_match = re.search(r'({.*})', recipes_text, re.DOTALL)
        if json_match:
            try:
                recipes_json = json.loads(json_match.group(1))
                return recipes_json.get('recipes', [])
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract recipes manually
                return parse_recipes_manually(recipes_text)
        else:
            return parse_recipes_manually(recipes_text)
    else:
        raise Exception("Failed to generate recipe recommendations")

def parse_recipes_manually(recipes_text):
    """
    Manually parse recipes from text if JSON parsing fails.
    This is a fallback method.
    """
    recipes = []
    
    # Split by recipe sections (assuming recipes are numbered)
    recipe_sections = re.split(r'\d+\.', recipes_text)
    
    for section in recipe_sections:
        if not section.strip():
            continue
        
        recipe = {}
        
        # Try to extract recipe name
        name_match = re.search(r'(?:Recipe name:|Name:)?\s*([^\n]+)', section)
        if name_match:
            recipe['name'] = name_match.group(1).strip()
        else:
            continue  # Skip if no name found
        
        # Try to extract ingredients
        ingredients_match = re.search(r'(?:Ingredients:|Ingredients needed:)([^#]*?)(?:Instructions:|Brief cooking instructions:|$)', section, re.DOTALL)
        if ingredients_match:
            ingredients_text = ingredients_match.group(1).strip()
            ingredients = [ing.strip() for ing in re.split(r'[\n,]', ingredients_text) if ing.strip()]
            recipe['ingredients'] = ingredients
        else:
            recipe['ingredients'] = []
        
        # Try to extract instructions
        instructions_match = re.search(r'(?:Instructions:|Brief cooking instructions:)([^#]*?)(?:Cooking time:|Approximate cooking time:|$)', section, re.DOTALL)
        if instructions_match:
            recipe['instructions'] = instructions_match.group(1).strip()
        else:
            recipe['instructions'] = "No instructions provided."
        
        # Try to extract cooking time
        time_match = re.search(r'(?:Cooking time:|Approximate cooking time:)\s*(\d+)', section)
        if time_match:
            recipe['cooking_time_minutes'] = int(time_match.group(1))
        else:
            recipe['cooking_time_minutes'] = 30  # Default
        
        recipes.append(recipe)
    
    return recipes

def store_recipes(recipes):
    """
    Store the recommended recipes in DynamoDB.
    """
    table = dynamodb.Table(RECIPE_TABLE)
    
    for recipe in recipes:
        # Generate a unique ID for the recipe
        recipe_id = f"recipe-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(recipe['name']) % 10000}"
        
        # Prepare the recipe for DynamoDB
        db_recipe = {
            'RecipeId': recipe_id,
            'Name': recipe['name'],
            'Ingredients': recipe['ingredients'],
            'Instructions': recipe['instructions'],
            'CookingTimeMinutes': recipe['cooking_time_minutes'],
            'CreatedAt': datetime.now().isoformat()
        }
        
        # Put the recipe in DynamoDB
        table.put_item(Item=db_recipe)
