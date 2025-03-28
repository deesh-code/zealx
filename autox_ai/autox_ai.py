# autox_ai.py - Decision-Making & Task Handling for ZealX

import json
import random
import time
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.api_manager import AutoXAIManager
from autox_ai.logger import log_error
from storagex.storage_manager import store_file_data, read_file_data
from storagex.database import store_memory, fetch_recent_memory
from storagex.faiss_manager import add_faiss_embedding, search_faiss_embedding

# Constants
DECISION_THRESHOLD = 0.75  # Confidence threshold for making decisions
CONTEXT_WINDOW = 5  # Number of recent events to consider for context
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts for API calls

class AutoXAI:
    """Intelligent automation brain for ZealX, processes triggers and makes decisions."""
    
    def __init__(self):
        """Initialize AutoX AI with API manager."""
        self.api_manager = AutoXAIManager()
        self.context_history = []
        self.decision_cache = {}  # Cache for similar decisions to reduce API calls
        self.last_api_call = None
        self.retry_count = 0
    
    def process_trigger(self, app_id, trigger_type, trigger_data):
        """Process a trigger from an app and decide on the appropriate action.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger (notification, message, ui_change, etc.)
            trigger_data (dict): Data associated with the trigger
            
        Returns:
            dict: Task to execute
        """
        # Add trigger to context history
        self.add_to_context(app_id, trigger_type, trigger_data)
        
        # Check if we have a cached decision for similar triggers
        cache_key = self._generate_cache_key(app_id, trigger_type, trigger_data)
        if cache_key in self.decision_cache:
            cached_task = self.decision_cache[cache_key]
            # Check if cache is still valid (not expired)
            if datetime.now().timestamp() - cached_task.get('timestamp', 0) < 300:  # 5 minutes
                return cached_task.get('task')
        
        # Get recent context for decision making
        context = self._get_recent_context()
        
        # Generate task using AI
        task = self._generate_task_with_ai(app_id, trigger_type, trigger_data, context)
        
        # Cache the decision for future similar triggers
        if task:
            self.decision_cache[cache_key] = {
                'task': task,
                'timestamp': datetime.now().timestamp()
            }
        
        return task
    
    def add_to_context(self, app_id, trigger_type, trigger_data):
        """Add a trigger to the context history.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger
            trigger_data (dict): Data associated with the trigger
        """
        context_entry = {
            'app_id': app_id,
            'trigger_type': trigger_type,
            'trigger_data': trigger_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.context_history.append(context_entry)
        
        # Limit context history size
        if len(self.context_history) > 100:  # Keep last 100 entries
            self.context_history = self.context_history[-100:]
    
    def _get_recent_context(self):
        """Get recent context for decision making.
        
        Returns:
            list: Recent context entries
        """
        # Get the most recent entries
        recent_context = self.context_history[-CONTEXT_WINDOW:] if len(self.context_history) > CONTEXT_WINDOW else self.context_history
        
        # Also fetch recent memories from storage for additional context
        try:
            recent_memories = fetch_recent_memory(limit=CONTEXT_WINDOW)
            # Convert memories to context format if needed
            memory_context = []
            for memory in recent_memories:
                try:
                    # Memories are stored as JSON strings
                    memory_data = json.loads(memory['text'])
                    memory_context.append(memory_data)
                except json.JSONDecodeError:
                    # If not JSON, add as raw text
                    memory_context.append({'text': memory['text'], 'type': 'memory'})
            
            # Combine recent triggers and memories
            combined_context = recent_context + memory_context
            return combined_context
        except Exception as e:
            log_error(f"Error fetching memory context: {str(e)}")
            return recent_context
    
    def _generate_task_with_ai(self, app_id, trigger_type, trigger_data, context):
        """Generate a task using AI based on trigger and context.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger
            trigger_data (dict): Data associated with the trigger
            context (list): Recent context for decision making
            
        Returns:
            dict: Task to execute
        """
        try:
            # Prepare input for AI model
            prompt = self._prepare_ai_prompt(app_id, trigger_type, trigger_data, context)
            
            # Call AI model through API manager
            model = "@cf/meta/mistral-7b-instruct"  # Default model
            response = self.api_manager.run(model, prompt)
            
            # Parse AI response into a task
            task = self._parse_ai_response(response, app_id)
            
            # Reset retry count on success
            self.retry_count = 0
            self.last_api_call = datetime.now().timestamp()
            
            return task
        except Exception as e:
            log_error(f"Error generating task with AI: {str(e)}")
            
            # Implement retry logic
            if self.retry_count < MAX_RETRY_ATTEMPTS:
                self.retry_count += 1
                time.sleep(1)  # Wait before retry
                return self._generate_task_with_ai(app_id, trigger_type, trigger_data, context)
            
            # If all retries fail, fall back to rule-based approach
            return self._fallback_rule_based_task(app_id, trigger_type, trigger_data)
    
    def _prepare_ai_prompt(self, app_id, trigger_type, trigger_data, context):
        """Prepare a prompt for the AI model.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger
            trigger_data (dict): Data associated with the trigger
            context (list): Recent context for decision making
            
        Returns:
            dict: Prompt for AI model
        """
        # Format context into a readable format for the AI
        formatted_context = []
        for ctx in context:
            if isinstance(ctx, dict):
                formatted_context.append(json.dumps(ctx))
            else:
                formatted_context.append(str(ctx))
        
        # Create a structured prompt for the AI
        prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are AutoX AI, the intelligent automation brain for ZealX. Your role is to process user interactions, make automation decisions, and send structured execution commands. You are currently processing a {trigger_type} from {app_id}."
                },
                {
                    "role": "user",
                    "content": f"I received a {trigger_type} from {app_id} with the following data: {json.dumps(trigger_data)}. Recent context: {formatted_context}. Please generate a structured task command to handle this trigger appropriately."
                }
            ]
        }
        
        return prompt
    
    def _parse_ai_response(self, response, app_id):
        """Parse AI response into a task.
        
        Args:
            response (str): Response from AI model
            app_id (str): Identifier for the app
            
        Returns:
            dict: Task to execute
        """
        try:
            # Try to parse response as JSON
            if isinstance(response, dict):
                # If response is already a dict, use it directly
                task_data = response
            else:
                # Try to extract JSON from text response
                # Look for JSON-like structure in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx+1]
                    task_data = json.loads(json_str)
                else:
                    # If no JSON found, create a simple task based on text
                    task_data = {
                        "action": "message",
                        "data": {
                            "text": response.strip()
                        }
                    }
            
            # Ensure task has required fields
            if "action" not in task_data:
                task_data["action"] = "unknown"
            
            # Add app_id if not present
            if "app_id" not in task_data:
                task_data["app_id"] = app_id
            
            # Ensure data field exists
            if "data" not in task_data:
                task_data["data"] = {}
            
            return task_data
        except Exception as e:
            log_error(f"Error parsing AI response: {str(e)}")
            
            # Return a simple fallback task
            return {
                "action": "message",
                "app_id": app_id,
                "data": {
                    "text": "I processed your request but couldn't generate a specific action."
                }
            }
    
    def _fallback_rule_based_task(self, app_id, trigger_type, trigger_data):
        """Generate a fallback task using rule-based approach when AI fails.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger
            trigger_data (dict): Data associated with the trigger
            
        Returns:
            dict: Task to execute
        """
        # Simple rule-based fallback logic
        if trigger_type == "message":
            return {
                "action": "reply",
                "app_id": app_id,
                "data": {
                    "message": "I received your message and will process it soon.",
                    "chat_id": trigger_data.get("chat_id")
                }
            }
        elif trigger_type == "notification":
            return {
                "action": "click",
                "app_id": app_id,
                "data": {
                    "element_id": trigger_data.get("notification_id")
                }
            }
        elif trigger_type == "ui_change":
            return {
                "action": "observe",
                "app_id": app_id,
                "data": {
                    "element_id": trigger_data.get("element_id")
                }
            }
        else:
            return {
                "action": "log",
                "app_id": app_id,
                "data": {
                    "message": f"Received {trigger_type} but no specific action defined."
                }
            }
    
    def _generate_cache_key(self, app_id, trigger_type, trigger_data):
        """Generate a cache key for similar triggers.
        
        Args:
            app_id (str): Identifier for the app
            trigger_type (str): Type of trigger
            trigger_data (dict): Data associated with the trigger
            
        Returns:
            str: Cache key
        """
        # Create a simplified version of trigger_data for the cache key
        # This helps match similar but not identical triggers
        simplified_data = {}
        
        if trigger_type == "message" and "text" in trigger_data:
            # For messages, use first few words as key
            text = trigger_data["text"]
            words = text.split()[:5]  # First 5 words
            simplified_data["text_prefix"] = " ".join(words)
        elif "id" in trigger_data:
            # For triggers with IDs, use the ID
            simplified_data["id"] = trigger_data["id"]
        
        # Create a string key
        key_parts = [app_id, trigger_type]
        for k, v in simplified_data.items():
            key_parts.append(f"{k}:{v}")
        
        return "|".join(key_parts)

# Example usage
if __name__ == "__main__":
    # Create AutoX AI instance
    autox_ai = AutoXAI()
    
    # Process a sample trigger
    task = autox_ai.process_trigger(
        app_id="whatsapp",
        trigger_type="message",
        trigger_data={
            "chat_id": "123456",
            "sender": "John Doe",
            "text": "Hello, can you help me with something?"
        }
    )
    
    print(f"Generated task: {json.dumps(task, indent=2)}")