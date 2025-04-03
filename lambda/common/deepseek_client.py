import boto3
import json
import os

class DeepSeekClient:
    """
    Client for interacting with DeepSeek AI on AWS SageMaker.
    
    This class provides methods to:
    1. Invoke the DeepSeek model for text generation
    2. Process images with DeepSeek vision capabilities
    3. Handle structured output from DeepSeek
    """
    
    def __init__(self, endpoint_name=None):
        """
        Initialize the DeepSeek client.
        
        Args:
            endpoint_name (str, optional): The name of the SageMaker endpoint.
                If not provided, it will be read from the DEEPSEEK_ENDPOINT environment variable.
        """
        self.endpoint_name = endpoint_name or os.environ.get('DEEPSEEK_ENDPOINT')
        if not self.endpoint_name:
            raise ValueError("DeepSeek endpoint name must be provided or set in DEEPSEEK_ENDPOINT environment variable")
        
        self.sagemaker_runtime = boto3.client('sagemaker-runtime')
    
    def generate_text(self, prompt, max_tokens=1000, temperature=0.2):
        """
        Generate text using the DeepSeek model.
        
        Args:
            prompt (str): The prompt to send to the model
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 1000.
            temperature (float, optional): Temperature for sampling. Defaults to 0.2.
                
        Returns:
            str: The generated text
        """
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        return self._invoke_endpoint(payload)
    
    def process_image(self, image_base64, prompt, max_tokens=1000, temperature=0.2):
        """
        Process an image using DeepSeek vision capabilities.
        
        Args:
            image_base64 (str): Base64-encoded image data
            prompt (str): The prompt describing what to do with the image
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 1000.
            temperature (float, optional): Temperature for sampling. Defaults to 0.2.
                
        Returns:
            str: The generated text based on the image
        """
        payload = {
            "prompt": prompt,
            "image_base64": image_base64,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        return self._invoke_endpoint(payload)
    
    def generate_structured_output(self, prompt, output_format, max_tokens=2000, temperature=0.2):
        """
        Generate structured output (like JSON) using the DeepSeek model.
        
        Args:
            prompt (str): The prompt to send to the model
            output_format (str): Description of the expected output format
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 2000.
            temperature (float, optional): Temperature for sampling. Defaults to 0.2.
                
        Returns:
            dict: The parsed structured output
        """
        # Enhance the prompt to request structured output
        enhanced_prompt = f"""
        {prompt}
        
        Please provide your response in the following format:
        {output_format}
        
        Ensure your response is valid JSON and contains only the requested structure.
        """
        
        payload = {
            "prompt": enhanced_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response_text = self._invoke_endpoint(payload)
        
        # Extract and parse JSON from the response
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                raise ValueError("No JSON found in the response")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing structured output: {str(e)}")
            print(f"Raw response: {response_text}")
            # Return the raw text if parsing fails
            return {"raw_response": response_text}
    
    def _invoke_endpoint(self, payload):
        """
        Invoke the SageMaker endpoint with the given payload.
        
        Args:
            payload (dict): The payload to send to the endpoint
                
        Returns:
            str: The generated text from the model
        """
        response = self.sagemaker_runtime.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse the response
        result = json.loads(response['Body'].read().decode())
        
        # Extract the generated text
        if 'generated_text' in result:
            return result['generated_text']
        else:
            raise Exception("Failed to generate response from DeepSeek endpoint")
