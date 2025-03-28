# brainx_core.py - Core implementation of BrainX with FireLayers X++ architecture

import os
import json
import time
import threading
from datetime import datetime
import sys
import numpy as np
import requests
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.api_manager import AutoXAIManager
from autox_ai.logger import log_error, log_warning
from storagex.storage_manager import store_file_data, read_file_data
from storagex.database import store_memory, fetch_recent_memory
from storagex.faiss_manager import add_faiss_embedding, search_faiss_embedding

# Constants
BRAINX_DIR = "brainx_data"
FIRELAYERS_CONFIG = "firelayers_config.json"
MICROLEARNING_THRESHOLD = 5  # Number of events before triggering micro-learning
CLOUD_SYNC_INTERVAL = 300  # Sync with cloud every 5 minutes
MAX_VECTOR_DIMENSION = 512  # Default vector dimension

# Ensure BrainX directory exists
os.makedirs(os.path.join("storagex_data", BRAINX_DIR), exist_ok=True)

class FireLayersX:
    """FireLayers X++ - Adaptive Real-Time Learning System for BrainX.
    
    A multi-layered approach where AI processes structured and unstructured 
    user interactions, optimizing decision-making and automation.
    """
    
    def __init__(self, user_id, is_premium=False):
        """Initialize FireLayers X++ with user information.
        
        Args:
            user_id (str): Unique identifier for the user
            is_premium (bool): Whether the user has premium access
        """
        self.user_id = user_id
        self.is_premium = is_premium
        self.ai_manager = AutoXAIManager()  # Reuse existing API manager
        self.learning_events = []  # Track events for micro-learning
        self.last_learning = datetime.now()
        self.last_cloud_sync = datetime.now()
        self.lock = threading.Lock()
        
        # Load FireLayers configuration
        self.config = self._load_config()
        
        # Initialize layers
        self.layers = {
            "perception": {"active": True, "weight": 1.0},
            "comprehension": {"active": True, "weight": 1.0},
            "decision": {"active": True, "weight": 1.0},
            "execution": {"active": True, "weight": 1.0},
            "reflection": {"active": True, "weight": 0.8}
        }
        
        # Statistics for optimization
        self.stats = {
            "total_events": 0,
            "micro_learning_sessions": 0,
            "cloud_syncs": 0,
            "last_updated": datetime.now().isoformat()
        }
    
    def _load_config(self):
        """Load FireLayers configuration from storage."""
        config_path = os.path.join("storagex_data", BRAINX_DIR, FIRELAYERS_CONFIG)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_error(f"Failed to load FireLayers config: {str(e)}")
        
        # Default configuration
        default_config = {
            "user_id": self.user_id,
            "is_premium": self.is_premium,
            "micro_learning": {
                "threshold": MICROLEARNING_THRESHOLD,
                "auto_trigger": True
            },
            "cloud_sync": {
                "interval": CLOUD_SYNC_INTERVAL,
                "auto_sync": True
            },
            "layers": self.layers,
            "created_at": datetime.now().isoformat()
        }
        
        # Save default config
        self._save_config(default_config)
        
        return default_config
    
    def _save_config(self, config=None):
        """Save FireLayers configuration to storage."""
        if config is None:
            config = self.config
        
        config["last_updated"] = datetime.now().isoformat()
        
        config_path = os.path.join("storagex_data", BRAINX_DIR, FIRELAYERS_CONFIG)
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            log_error(f"Failed to save FireLayers config: {str(e)}")
            return False
    
    def process_event(self, event_type, event_data):
        """Process an event through FireLayers X++.
        
        Args:
            event_type (str): Type of event (user_action, system_event, etc.)
            event_data (dict): Data associated with the event
            
        Returns:
            dict: Processed result with FireLayers enhancements
        """
        # Add timestamp to event data
        event_data["timestamp"] = datetime.now().isoformat()
        
        # Create event record
        event = {
            "type": event_type,
            "data": event_data,
            "user_id": self.user_id,
            "processed": False
        }
        
        # Process through each active layer
        result = self._process_through_layers(event)
        
        # Add to learning events
        with self.lock:
            self.learning_events.append(event)
            self.stats["total_events"] += 1
        
        # Check if we should trigger micro-learning
        self._check_micro_learning_trigger()
        
        # Check if we should sync with cloud
        self._check_cloud_sync()
        
        return result
    
    def _process_through_layers(self, event):
        """Process an event through each active FireLayer.
        
        Args:
            event (dict): Event to process
            
        Returns:
            dict: Processed result
        """
        result = {"original_event": event, "layer_results": {}}
        
        # Process through perception layer (data intake)
        if self.layers["perception"]["active"]:
            result["layer_results"]["perception"] = self._perception_layer(event)
        
        # Process through comprehension layer (understanding)
        if self.layers["comprehension"]["active"]:
            result["layer_results"]["comprehension"] = self._comprehension_layer(event, result)
        
        # Process through decision layer (action planning)
        if self.layers["decision"]["active"]:
            result["layer_results"]["decision"] = self._decision_layer(event, result)
        
        # Process through execution layer (action implementation)
        if self.layers["execution"]["active"]:
            result["layer_results"]["execution"] = self._execution_layer(event, result)
        
        # Process through reflection layer (learning & improvement)
        if self.layers["reflection"]["active"]:
            result["layer_results"]["reflection"] = self._reflection_layer(event, result)
        
        # Mark event as processed
        event["processed"] = True
        
        return result
    
    def _perception_layer(self, event):
        """Process event through perception layer (data intake).
        
        Args:
            event (dict): Event to process
            
        Returns:
            dict: Perception layer result
        """
        # Extract relevant features from event
        features = {
            "event_type": event["type"],
            "timestamp": event["data"].get("timestamp"),
            "user_id": self.user_id
        }
        
        # Add event-specific features
        if event["type"] == "user_action":
            features["action"] = event["data"].get("action")
            features["context"] = event["data"].get("context")
        elif event["type"] == "system_event":
            features["system"] = event["data"].get("system")
            features["event"] = event["data"].get("event")
        
        # Store event in memory for future reference
        try:
            store_memory(json.dumps(event), np.random.rand(MAX_VECTOR_DIMENSION).tolist())
        except Exception as e:
            log_error(f"Failed to store event in memory: {str(e)}")
        
        return {"features": features, "status": "processed"}
    
    def _comprehension_layer(self, event, result):
        """Process event through comprehension layer (understanding).
        
        Args:
            event (dict): Event to process
            result (dict): Results from previous layers
            
        Returns:
            dict: Comprehension layer result
        """
        # Get perception features
        features = result["layer_results"]["perception"]["features"]
        
        # Retrieve relevant context from memory
        context = self._retrieve_relevant_context(event)
        
        # Analyze event in context
        understanding = {
            "event_type": features["event_type"],
            "context": context,
            "patterns": self._identify_patterns(event, context),
            "relevance": self._calculate_relevance(event)
        }
        
        return {"understanding": understanding, "status": "processed"}
    
    def _decision_layer(self, event, result):
        """Process event through decision layer (action planning).
        
        Args:
            event (dict): Event to process
            result (dict): Results from previous layers
            
        Returns:
            dict: Decision layer result
        """
        # Get comprehension understanding
        understanding = result["layer_results"]["comprehension"]["understanding"]
        
        # Generate potential actions based on understanding
        actions = self._generate_potential_actions(event, understanding)
        
        # Evaluate and rank actions
        ranked_actions = self._rank_actions(actions, understanding)
        
        # Select best action
        selected_action = ranked_actions[0] if ranked_actions else None
        
        return {
            "potential_actions": actions,
            "ranked_actions": ranked_actions,
            "selected_action": selected_action,
            "status": "processed"
        }
    
    def _execution_layer(self, event, result):
        """Process event through execution layer (action implementation).
        
        Args:
            event (dict): Event to process
            result (dict): Results from previous layers
            
        Returns:
            dict: Execution layer result
        """
        # Get decision result
        decision = result["layer_results"]["decision"]
        selected_action = decision["selected_action"]
        
        # If no action selected, return empty result
        if not selected_action:
            return {"status": "no_action"}
        
        # Prepare action for execution
        execution_plan = self._prepare_execution(selected_action)
        
        # Execute action (or prepare for execution)
        execution_result = self._execute_action(execution_plan)
        
        return {
            "execution_plan": execution_plan,
            "execution_result": execution_result,
            "status": "executed" if execution_result.get("success") else "failed"
        }
    
    def _reflection_layer(self, event, result):
        """Process event through reflection layer (learning & improvement).
        
        Args:
            event (dict): Event to process
            result (dict): Results from previous layers
            
        Returns:
            dict: Reflection layer result
        """
        # Analyze execution result
        execution = result["layer_results"].get("execution", {})
        execution_status = execution.get("status")
        
        # Generate insights
        insights = self._generate_insights(event, result)
        
        # Identify improvement opportunities
        improvements = self._identify_improvements(event, result)
        
        # Store learning points for micro-learning
        learning_points = {
            "event_id": id(event),
            "insights": insights,
            "improvements": improvements,
            "execution_status": execution_status
        }
        
        # Store for future micro-learning
        self._store_learning_points(learning_points)
        
        return {
            "insights": insights,
            "improvements": improvements,
            "learning_points": learning_points,
            "status": "processed"
        }
    
    def _retrieve_relevant_context(self, event):
        """Retrieve relevant context for an event from memory.
        
        Args:
            event (dict): Event to find context for
            
        Returns:
            list: Relevant context items
        """
        try:
            # Generate a simple embedding for the event
            event_embedding = np.random.rand(MAX_VECTOR_DIMENSION).astype('float32')
            
            # Search for similar events in memory
            similar_indices = search_faiss_embedding(event_embedding, top_k=5)
            
            # Fetch recent memories
            recent_memories = fetch_recent_memory(limit=10)
            
            # Combine similar and recent memories
            context = []
            for memory in recent_memories:
                try:
                    memory_data = json.loads(memory["text"])
                    context.append(memory_data)
                except json.JSONDecodeError:
                    # If not JSON, add as raw text
                    context.append({"text": memory["text"], "type": "memory"})
            
            return context
        except Exception as e:
            log_error(f"Failed to retrieve context: {str(e)}")
            return []
    
    def _identify_patterns(self, event, context):
        """Identify patterns in event and context.
        
        Args:
            event (dict): Current event
            context (list): Context items
            
        Returns:
            list: Identified patterns
        """
        # Simple pattern identification (placeholder for more complex implementation)
        patterns = []
        
        # Check for repeated event types
        event_types = [item.get("type") for item in context if isinstance(item, dict) and "type" in item]
        if event["type"] in event_types:
            patterns.append({"type": "repeated_event", "event_type": event["type"]})
        
        # Check for time-based patterns (e.g., events at similar times)
        # This would be more sophisticated in a real implementation
        
        return patterns
    
    def _calculate_relevance(self, event):
        """Calculate relevance score for an event.
        
        Args:
            event (dict): Event to calculate relevance for
            
        Returns:
            float: Relevance score (0-1)
        """
        # Simple relevance calculation (placeholder for more complex implementation)
        # In a real implementation, this would consider user preferences, history, etc.
        
        # Default medium relevance
        relevance = 0.5
        
        # Increase relevance for user actions
        if event["type"] == "user_action":
            relevance += 0.3
        
        # Cap relevance at 1.0
        return min(1.0, relevance)
    
    def _generate_potential_actions(self, event, understanding):
        """Generate potential actions based on event understanding.
        
        Args:
            event (dict): Current event
            understanding (dict): Comprehension layer understanding
            
        Returns:
            list: Potential actions
        """
        # Simple action generation (placeholder for more complex implementation)
        actions = []
        
        # Add default "no action" option
        actions.append({"type": "no_action", "reason": "Default option"})
        
        # Generate event-specific actions
        if event["type"] == "user_action":
            # Add response action
            actions.append({
                "type": "respond",
                "data": {
                    "message": "Automated response to user action",
                    "context": understanding["context"]
                }
            })
        elif event["type"] == "system_event":
            # Add system handling action
            actions.append({
                "type": "system_handle",
                "data": {
                    "event": event["data"].get("event"),
                    "response": "Automated system event handling"
                }
            })
        
        return actions
    
    def _rank_actions(self, actions, understanding):
        """Rank potential actions based on understanding.
        
        Args:
            actions (list): Potential actions
            understanding (dict): Comprehension layer understanding
            
        Returns:
            list: Ranked actions
        """
        # Simple action ranking (placeholder for more complex implementation)
        # In a real implementation, this would use ML models to rank actions
        
        # Assign scores to actions
        scored_actions = []
        for action in actions:
            # Skip "no action" for scoring
            if action["type"] == "no_action":
                score = 0.1  # Low default score
            elif action["type"] == "respond":
                score = 0.7  # Medium-high score for responses
            elif action["type"] == "system_handle":
                score = 0.8  # High score for system handling
            else:
                score = 0.5  # Medium score for other actions
            
            # Adjust score based on relevance
            score *= understanding["relevance"]
            
            # Add to scored actions
            scored_actions.append({**action, "score": score})
        
        # Sort by score (descending)
        ranked_actions = sorted(scored_actions, key=lambda x: x["score"], reverse=True)
        
        return ranked_actions
    
    def _prepare_execution(self, action):
        """Prepare an action for execution.
        
        Args:
            action (dict): Action to prepare
            
        Returns:
            dict: Execution plan
        """
        # Simple execution preparation
        execution_plan = {
            "action": action,
            "prepared_at": datetime.now().isoformat(),
            "execution_id": f"exec_{int(time.time())}"
        }
        
        # Add action-specific execution details
        if action["type"] == "respond":
            execution_plan["execution_details"] = {
                "response_type": "message",
                "content": action["data"]["message"],
                "context": action["data"]["context"]
            }
        elif action["type"] == "system_handle":
            execution_plan["execution_details"] = {
                "handler": "system_event_handler",
                "event": action["data"]["event"],
                "response": action["data"]["response"]
            }
        
        return execution_plan
    
    def _execute_action(self, execution_plan):
        """Execute an action based on execution plan.
        
        Args:
            execution_plan (dict): Plan for execution
            
        Returns:
            dict: Execution result
        """
        # Simple action execution (placeholder for actual implementation)
        action = execution_plan["action"]
        
        # Default result
        result = {
            "success": True,
            "execution_id": execution_plan["execution_id"],
            "executed_at": datetime.now().isoformat()
        }
        
        # Execute based on action type
        if action["type"] == "no_action":
            result["details"] = "No action taken"
        elif action["type"] == "respond":
            # Simulate sending a response
            result["details"] = f"Response sent: {action['data']['message']}"
        elif action["type"] == "system_handle":
            # Simulate handling a system event
            result["details"] = f"System event handled: {action['data']['event']}"
        else:
            # Unknown action type
            result["success"] = False
            result["details"] = f"Unknown action type: {action['type']}"
        
        return result
    
    def _generate_insights(self, event, result):
        """Generate insights from event processing.
        
        Args:
            event (dict): Processed event
            result (dict): Processing results
            
        Returns:
            list: Generated insights
        """
        # Simple insight generation (placeholder for more complex implementation)
        insights = []
        
        # Add basic event insight
        insights.append({
            "type": "event_processed",
            "event_type": event["type"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Add layer-specific insights
        for layer, layer_result in result["layer_results"].items():
            if layer == "execution" and layer_result.get("status") == "executed":
                insights.append({
                    "type": "action_executed",
                    "action": layer_result.get("execution_plan", {}).get("action", {}).get("type"),
                    "success": layer_result.get("execution_result", {}).get("success", False)
                })
        
        return insights
    
    def _identify_improvements(self, event, result):
        """Identify potential improvements from event processing.
        
        Args:
            event (dict): Processed event
            result (dict): Processing results
            
        Returns:
            list: Potential improvements
        """
        # Simple improvement identification (placeholder for more complex implementation)
        improvements = []
        
        # Check execution result
        execution = result["layer_results"].get("execution", {})
        if execution.get("status") == "failed":
            improvements.append({
                "type": "execution_failure",
                "action": execution.get("execution_plan", {}).get("action", {}).get("type"),
                "suggestion": "Improve action execution reliability"
            })
        
        # Check decision quality
        decision = result["layer_results"].get("decision", {})
        if not decision.get("potential_actions") or len(decision.get("potential_actions", [])) <= 1:
            improvements.append({
                "type": "limited_actions",
                "event_type": event["type"],
                "suggestion": "Expand action generation for this event type"
            })
        
        return improvements
    
    def _store_learning_points(self, learning_points):
        """Store learning points for future micro-learning.
        
        Args:
            learning_points (dict): Learning points to store
        """
        # Simple storage (placeholder for more sophisticated storage)
        learning_file = os.path.join("storagex_data", BRAINX_DIR, "learning_points.json")
        
        # Load existing learning points
        existing_points = []
        if os.path.exists(learning_file):
            try:
                with open(learning_file, 'r') as f:
                    existing_points = json.load(f)
            except Exception as e:
                log_error(f"Failed to load learning points: {str(e)}")
        
        # Add new learning points
        existing_points.append({
            **learning_points,
            "stored_at": datetime.now().isoformat()
        })
        
        # Limit to recent points (keep last 100)
        if len(existing_points) > 100:
            existing_points = existing_points[-100:]
        
        # Save updated learning points
        try:
            with open(learning_file, 'w') as f:
                json.dump(existing_points, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save learning points: {str(e)}")
    
    def _check_micro_learning_trigger(self):
        """Check if micro-learning should be triggered."""
        # Skip if auto-trigger is disabled
        if not self.config.get("micro_learning", {}).get("auto_trigger", True):
            return
        
        with self.lock:
            # Check if we have enough events
            if len(self.learning_events) >= self.config.get("micro_learning", {}).get("threshold", MICROLEARNING_THRESHOLD):
                # Trigger micro-learning
                self._trigger_micro_learning()
    
    def _trigger_micro_learning(self):
        """Trigger a micro-learning session."""
        with self.lock:
            # Get learning events
            events = self.learning_events.copy()
            self.learning_events = []  # Clear events
            
            # Update statistics
            self.stats["micro_learning_sessions"] += 1
            self.last_learning = datetime.now()
            
            # Save statistics
            self._save_stats()
        
        # Process events for learning (in a separate thread)
        threading.Thread(target=self._process_micro_learning, args=(events,)).start()
    
    def _process_micro_learning(self, events):
        """Process events for micro-learning.
        
        Args:
            events (list): Events to process for learning
        """
        # Simple micro-learning implementation (placeholder for more complex implementation)
        # In a real implementation, this would update model weights, adjust parameters, etc.
        
        # Extract learning points
        learning_points = []
        for event in events:
            # Skip unprocessed events
            if not event.get("processed", False):
                continue
            
            # Add event data for learning
            learning_points.append({
                "event_type": event["type"],
                "timestamp": event["data"].get("timestamp"),
                "user_id": self.user_id
            })
        
        # Save learning results
        learning_result = {
            "session_id": f"ml_{int(time.time())}",
            "events_processed": len(events),
            "learning_points": len(learning_points),
            "timestamp": datetime.now().isoformat()
        }
        
        # Save learning result
        learning_file = os.path.join("storagex_data", BRAINX_DIR, "micro_learning_sessions.json")
        
        # Load existing sessions
        existing_sessions = []
        if os.path.exists(learning_file):
            try:
                with open(learning_file, 'r') as f:
                    existing_sessions = json.load(f)
            except Exception as e:
                log_error(f"Failed to load micro-learning sessions: {str(e)}")
        
        # Add new session
        existing_sessions.append(learning_result)
        
        # Save updated sessions
        try:
            with open(learning_file, 'w') as f:
                json.dump(existing_sessions, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save micro-learning sessions: {str(e)}")
    
    def _check_cloud_sync(self):
        """Check if cloud sync should be triggered."""
        # Skip if auto-sync is disabled
        if not self.config.get("cloud_sync", {}).get("auto_sync", True):
            return
        
        # Check if it's time to sync
        now = datetime.now()
        interval = self.config.get("cloud_sync", {}).get("interval", CLOUD_SYNC_INTERVAL)
        
        if (now - self.last_cloud_sync).total_seconds() >= interval:
            # Trigger cloud sync
            self._trigger_cloud_sync()
    
    def _trigger_cloud_sync(self):
        """Trigger a cloud sync session."""
        # Update timestamp
        self.last_cloud_sync = datetime.now()
        
        # Update statistics
        self.stats["cloud_syncs"] += 1
        self._save_stats()
        
        # Process cloud sync (in a separate thread)
        threading.Thread(target=self._process_cloud_sync).start()
        
    def _save_stats(self):
        """Save FireLayers statistics to storage."""
        # Update timestamp
        self.stats["last_updated"] = datetime.now().isoformat()
        
        # Save stats to file
        stats_file = os.path.join("storagex_data", BRAINX_DIR, "firelayers_stats.json")
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            return True
        except Exception as e:
            log_error(f"Failed to save FireLayers stats: {str(e)}")
            return False
    
    def _process_cloud_sync(self):
        """Process cloud sync."""
        # Simple cloud sync implementation (placeholder for actual implementation)
        # In a real implementation, this would sync data with cloud storage
        
        # Save sync result
        sync_result = {
            "sync_id": f"sync_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        # Save sync result
        sync_file = os.path.join("storagex_data", BRAINX_DIR, "cloud_syncs.json")
        
        # Load existing syncs
        existing_syncs = []
        if os.path.exists(sync_file):
            try:
                with open(sync_file, 'r') as f:
                    existing_syncs = json.load(f)
            except Exception as e:
                log_error(f"Failed to load cloud syncs: {str(e)}")
        
        # Add new sync result
        existing_syncs.append(sync_result)
        
        # Save updated syncs
        try:
            with open(sync_file, 'w') as f:
                json.dump(existing_syncs, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save cloud syncs: {str(e)}")
            
        return sync_result