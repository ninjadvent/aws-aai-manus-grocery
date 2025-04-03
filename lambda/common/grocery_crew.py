import json
import boto3
import os
from crewai import Agent, Task, Crew, Process
from common.deepseek_client import DeepSeekClient

class GroceryManagementCrew:
    """
    CrewAI orchestration for the Grocery Management System.
    
    This class:
    1. Sets up CrewAI agents for each task
    2. Defines tasks for the agents
    3. Creates a crew to execute the tasks
    4. Provides methods to run the workflow
    """
    
    def __init__(self):
        """
        Initialize the GroceryManagementCrew.
        """
        # Initialize DeepSeek client
        self.deepseek_client = DeepSeekClient()
        
        # Set up the agents
        self.receipt_agent = self._create_receipt_agent()
        self.expiration_agent = self._create_expiration_agent()
        self.inventory_agent = self._create_inventory_agent()
        self.recipe_agent = self._create_recipe_agent()
    
    def process_receipt(self, receipt_image_base64):
        """
        Process a receipt image and run the full grocery management workflow.
        
        Args:
            receipt_image_base64 (str): Base64-encoded receipt image
            
        Returns:
            dict: Results of the workflow execution
        """
        # Define the tasks
        receipt_task = self._create_receipt_task(receipt_image_base64)
        expiration_task = self._create_expiration_task()
        inventory_task = self._create_inventory_task()
        recipe_task = self._create_recipe_task()
        
        # Create the crew
        crew = Crew(
            agents=[
                self.receipt_agent,
                self.expiration_agent,
                self.inventory_agent,
                self.recipe_agent
            ],
            tasks=[
                receipt_task,
                expiration_task,
                inventory_task,
                recipe_task
            ],
            process=Process.sequential  # Execute tasks in sequence
        )
        
        # Execute the crew
        result = crew.kickoff()
        
        return {
            'message': 'Grocery management workflow completed successfully',
            'result': result
        }
    
    def _create_receipt_agent(self):
        """
        Create a CrewAI agent for receipt interpretation.
        """
        return Agent(
            role='Receipt Interpreter',
            goal='Extract grocery items from receipt images with high accuracy',
            backstory='You are an expert at analyzing receipts and extracting structured data from them.',
            verbose=True,
            tools=[self._extract_items_from_receipt]
        )
    
    def _create_expiration_agent(self):
        """
        Create a CrewAI agent for expiration date estimation.
        """
        return Agent(
            role='Expiration Date Estimator',
            goal='Accurately predict expiration dates for grocery items',
            backstory='You are an expert at food preservation and shelf life estimation.',
            verbose=True,
            tools=[self._estimate_expiration_dates]
        )
    
    def _create_inventory_agent(self):
        """
        Create a CrewAI agent for grocery inventory tracking.
        """
        return Agent(
            role='Grocery Tracker',
            goal='Maintain an accurate inventory of grocery items',
            backstory='You are an organized inventory manager who keeps track of all items.',
            verbose=True,
            tools=[self._update_inventory]
        )
    
    def _create_recipe_agent(self):
        """
        Create a CrewAI agent for recipe recommendations.
        """
        return Agent(
            role='Recipe Recommender',
            goal='Suggest creative and practical recipes based on available ingredients',
            backstory='You are a creative chef who can make delicious meals from any ingredients.',
            verbose=True,
            tools=[self._recommend_recipes]
        )
    
    def _create_receipt_task(self, receipt_image_base64):
        """
        Create a task for receipt interpretation.
        """
        return Task(
            description=f"Analyze this receipt image and extract all grocery items with their prices.",
            agent=self.receipt_agent,
            expected_output="A list of grocery items with their prices",
            context={"receipt_image": receipt_image_base64}
        )
    
    def _create_expiration_task(self):
        """
        Create a task for expiration date estimation.
        """
        return Task(
            description="Estimate the expiration dates for the grocery items extracted from the receipt.",
            agent=self.expiration_agent,
            expected_output="A list of grocery items with their estimated expiration dates"
        )
    
    def _create_inventory_task(self):
        """
        Create a task for inventory tracking.
        """
        return Task(
            description="Update the grocery inventory with the new items and their expiration dates.",
            agent=self.inventory_agent,
            expected_output="Updated inventory status"
        )
    
    def _create_recipe_task(self):
        """
        Create a task for recipe recommendation.
        """
        return Task(
            description="Recommend recipes based on the current grocery inventory, prioritizing items that will expire soon.",
            agent=self.recipe_agent,
            expected_output="A list of recommended recipes using available ingredients"
        )
    
    def _extract_items_from_receipt(self, receipt_image_base64):
        """
        Tool for extracting items from a receipt image.
        
        Args:
            receipt_image_base64 (str): Base64-encoded receipt image
            
        Returns:
            list: Extracted grocery items
        """
        prompt = """
        You are an expert at extracting information from grocery receipts.
        Please analyze this receipt image and extract all grocery items with their prices.
        Format the output as a JSON array of items, where each item has a 'name' and 'price' field.
        """
        
        # Process the image with DeepSeek
        result = self.deepseek_client.process_image(
            receipt_image_base64,
            prompt,
            max_tokens=1000,
            temperature=0.2
        )
        
        # Try to parse the result as JSON
        try:
            import re
            json_match = re.search(r'(\[.*\])', result, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group(1))
                return items
            else:
                # If no JSON array is found, try to parse manually
                items = []
                lines = result.strip().split('\n')
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 1)
                        name = parts[0].strip()
                        price_match = re.search(r'(\d+\.\d+)', parts[1])
                        if price_match:
                            price = float(price_match.group(1))
                            items.append({"name": name, "price": price})
                return items
        except Exception as e:
            print(f"Error parsing receipt items: {str(e)}")
            return []
    
    def _estimate_expiration_dates(self, items):
        """
        Tool for estimating expiration dates for grocery items.
        
        Args:
            items (list): List of grocery items
            
        Returns:
            list: Items with estimated expiration dates
        """
        # Prepare the list of items for DeepSeek
        items_list = "\n".join([f"{item['name']}" for item in items])
        
        prompt = f"""
        You are an expert at estimating expiration dates for grocery items.
        Please estimate the typical shelf life (in days) for each of the following grocery items:
        
        {items_list}
        
        For each item, provide only the name and the number of days until expiration.
        Format your response as JSON: [{"name": "item name", "shelf_life_days": days}, ...]
        """
        
        # Get expiration estimates from DeepSeek
        output_format = '[{"name": "item name", "shelf_life_days": days}, ...]'
        result = self.deepseek_client.generate_structured_output(
            prompt,
            output_format,
            max_tokens=1000,
            temperature=0.2
        )
        
        # If we got a valid result
        if isinstance(result, list):
            # Create a mapping of item name to shelf life
            shelf_life_map = {item['name'].lower(): item['shelf_life_days'] for item in result}
            
            # Update the original items with expiration dates
            from datetime import datetime, timedelta
            today = datetime.now()
            
            for item in items:
                item_name = item['name'].lower()
                # Find the closest match in our shelf life map
                best_match = None
                best_score = 0
                for name in shelf_life_map:
                    if item_name in name or name in item_name:
                        score = len(name) / max(len(item_name), len(name))
                        if score > best_score:
                            best_score = score
                            best_match = name
                
                if best_match and best_score > 0.5:
                    days = shelf_life_map[best_match]
                else:
                    # Default to 7 days if no match found
                    days = 7
                
                # Add expiration date to the item
                expiration_date = today + timedelta(days=days)
                item['expiration_date'] = expiration_date.strftime("%Y-%m-%d")
                item['shelf_life_days'] = days
        
        return items
    
    def _update_inventory(self, items):
        """
        Tool for updating the grocery inventory.
        
        Args:
            items (list): List of grocery items with expiration dates
            
        Returns:
            dict: Updated inventory status
        """
        # In a real implementation, this would update a database
        # For this example, we'll just return the updated inventory
        return {
            "status": "success",
            "updated_at": datetime.now().isoformat(),
            "inventory": items
        }
    
    def _recommend_recipes(self, inventory):
        """
        Tool for recommending recipes based on inventory.
        
        Args:
            inventory (dict): Current inventory status
            
        Returns:
            list: Recommended recipes
        """
        # Extract item names from inventory
        items = inventory.get('inventory', [])
        item_names = [item['name'] for item in items]
        items_list = ", ".join(item_names)
        
        prompt = f"""
        You are a creative chef who specializes in creating recipes from available ingredients.
        Please suggest 3 recipes that can be made using some or all of the following ingredients:
        
        {items_list}
        
        For each recipe, provide:
        1. Recipe name
        2. Ingredients needed (indicate which ones are from the provided list)
        3. Brief cooking instructions
        4. Approximate cooking time in minutes
        
        Format your response as JSON with the following structure:
        [
            {{
                "name": "Recipe Name",
                "ingredients": ["Ingredient 1", "Ingredient 2", ...],
                "instructions": "Brief cooking instructions",
                "cooking_time_minutes": 30
            }},
            ...
        ]
        """
        
        # Get recipe recommendations from DeepSeek
        output_format = '[{"name": "Recipe Name", "ingredients": ["Ingredient 1", "Ingredient 2"], "instructions": "Brief cooking instructions", "cooking_time_minutes": 30}, ...]'
        result = self.deepseek_client.generate_structured_output(
            prompt,
            output_format,
            max_tokens=2000,
            temperature=0.7
        )
        
        return result
