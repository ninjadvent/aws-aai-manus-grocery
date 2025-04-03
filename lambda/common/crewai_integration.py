import json
import boto3
import os
from crewai import Agent, Task, Crew, Process

# Initialize AWS clients
lambda_client = boto3.client('lambda')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
DEEPSEEK_ENDPOINT = os.environ['DEEPSEEK_ENDPOINT']

def lambda_handler(event, context):
    """
    CrewAI orchestration Lambda function for the Grocery Management System.
    
    This function:
    1. Sets up CrewAI agents for each task
    2. Defines tasks for the agents
    3. Creates a crew to execute the tasks
    4. Returns the results
    """
    try:
        # Parse the incoming event
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Get the receipt image data
        if 'image' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No image provided'})
            }
        
        image_data = body['image']
        
        # Set up the CrewAI agents
        receipt_agent = create_receipt_agent()
        expiration_agent = create_expiration_agent()
        inventory_agent = create_inventory_agent()
        recipe_agent = create_recipe_agent()
        
        # Define the tasks
        receipt_task = create_receipt_task(receipt_agent, image_data)
        expiration_task = create_expiration_task(expiration_agent)
        inventory_task = create_inventory_task(inventory_agent)
        recipe_task = create_recipe_task(recipe_agent)
        
        # Create the crew
        crew = Crew(
            agents=[receipt_agent, expiration_agent, inventory_agent, recipe_agent],
            tasks=[receipt_task, expiration_task, inventory_task, recipe_task],
            process=Process.sequential  # Execute tasks in sequence
        )
        
        # Execute the crew
        result = crew.kickoff()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Grocery management workflow completed successfully',
                'result': result
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def create_receipt_agent():
    """
    Create a CrewAI agent for receipt interpretation.
    """
    return Agent(
        role='Receipt Interpreter',
        goal='Extract grocery items from receipt images with high accuracy',
        backstory='You are an expert at analyzing receipts and extracting structured data from them.',
        verbose=True,
        llm=DeepSeekLLM()  # Custom LLM class for DeepSeek integration
    )

def create_expiration_agent():
    """
    Create a CrewAI agent for expiration date estimation.
    """
    return Agent(
        role='Expiration Date Estimator',
        goal='Accurately predict expiration dates for grocery items',
        backstory='You are an expert at food preservation and shelf life estimation.',
        verbose=True,
        llm=DeepSeekLLM()
    )

def create_inventory_agent():
    """
    Create a CrewAI agent for grocery inventory tracking.
    """
    return Agent(
        role='Grocery Tracker',
        goal='Maintain an accurate inventory of grocery items',
        backstory='You are an organized inventory manager who keeps track of all items.',
        verbose=True,
        llm=DeepSeekLLM()
    )

def create_recipe_agent():
    """
    Create a CrewAI agent for recipe recommendations.
    """
    return Agent(
        role='Recipe Recommender',
        goal='Suggest creative and practical recipes based on available ingredients',
        backstory='You are a creative chef who can make delicious meals from any ingredients.',
        verbose=True,
        llm=DeepSeekLLM()
    )

def create_receipt_task(agent, image_data):
    """
    Create a task for receipt interpretation.
    """
    return Task(
        description=f"Analyze this receipt image and extract all grocery items with their prices. The image data is: {image_data[:100]}...",
        agent=agent,
        expected_output="A list of grocery items with their prices"
    )

def create_expiration_task(agent):
    """
    Create a task for expiration date estimation.
    """
    return Task(
        description="Estimate the expiration dates for the grocery items extracted from the receipt.",
        agent=agent,
        expected_output="A list of grocery items with their estimated expiration dates"
    )

def create_inventory_task(agent):
    """
    Create a task for inventory tracking.
    """
    return Task(
        description="Update the grocery inventory with the new items and their expiration dates.",
        agent=agent,
        expected_output="Updated inventory status"
    )

def create_recipe_task(agent):
    """
    Create a task for recipe recommendation.
    """
    return Task(
        description="Recommend recipes based on the current grocery inventory, prioritizing items that will expire soon.",
        agent=agent,
        expected_output="A list of recommended recipes using available ingredients"
    )

class DeepSeekLLM:
    """
    Custom LLM class for DeepSeek integration with CrewAI.
    """
    def __init__(self):
        self.endpoint_name = DEEPSEEK_ENDPOINT
    
    def generate(self, prompt, **kwargs):
        """
        Generate a response from DeepSeek.
        """
        # Prepare the payload for DeepSeek
        payload = {
            "prompt": prompt,
            "max_tokens": kwargs.get('max_tokens', 1000),
            "temperature": kwargs.get('temperature', 0.2)
        }
        
        # Add image if present
        if 'image' in kwargs:
            payload['image_base64'] = kwargs['image']
        
        # Invoke the DeepSeek endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse the response
        result = json.loads(response['Body'].read().decode())
        
        # Return the generated text
        if 'generated_text' in result:
            return result['generated_text']
        else:
            raise Exception("Failed to generate response from DeepSeek")
