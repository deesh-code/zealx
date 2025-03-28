"""
FireLayers X++ - Adaptive Learning System for BrainX
Optimizes Mistral 7B interactions with dynamic learning patterns
"""

import time
import logging
import json
from typing import List, Dict, Any, Optional, Union
import numpy as np
from datetime import datetime
import asyncio
from pydantic import BaseModel

from backend.models.api import Message, FireLayersConfig

# Configure logger
logger = logging.getLogger("zealx.firelayers")

class ContextCompressor:
    """
    Compresses conversation context to optimize token usage
    Uses semantic similarity to identify and merge similar messages
    """
    
    def __init__(self, config: FireLayersConfig):
        self.config = config
        self.compression_threshold = 0.85  # Similarity threshold for compression
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two text segments
        This is a simplified version - in production would use embeddings
        """
        # Simple word overlap similarity for demonstration
        # In production, use proper embeddings from a model
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def compress_messages(self, messages: List[Message]) -> List[Message]:
        """
        Compress messages by merging similar consecutive user messages
        Preserves system and assistant messages
        """
        if not self.config.context_compression or len(messages) < 3:
            return messages
        
        compressed = []
        i = 0
        
        while i < len(messages):
            current = messages[i]
            
            # Always keep system messages
            if current.role == "system":
                compressed.append(current)
                i += 1
                continue
            
            # For user messages, check if we can compress with next user message
            if current.role == "user" and i + 2 < len(messages):
                # Look for next user message (skipping assistant response)
                if messages[i+2].role == "user":
                    similarity = self._calculate_similarity(
                        current.content, 
                        messages[i+2].content
                    )
                    
                    if similarity > self.compression_threshold:
                        # Merge the messages and skip the next user message
                        merged_content = f"{current.content}\n{messages[i+2].content}"
                        compressed.append(Message(
                            role="user",
                            content=merged_content
                        ))
                        # Include the assistant response
                        compressed.append(messages[i+1])
                        i += 3
                        continue
            
            # Default case: keep the message as is
            compressed.append(current)
            i += 1
        
        compression_ratio = len(compressed) / len(messages) if messages else 1.0
        logger.debug(f"Context compression: {len(messages)} → {len(compressed)} messages (ratio: {compression_ratio:.2f})")
        
        return compressed

class TemperatureAdapter:
    """
    Dynamically adjusts temperature based on conversation context and patterns
    Higher temperature for creative tasks, lower for factual/precise tasks
    """
    
    def __init__(self, config: FireLayersConfig):
        self.config = config
        self.factual_keywords = [
            "what is", "how to", "explain", "define", "calculate", 
            "solve", "find", "list", "when", "where", "who"
        ]
        self.creative_keywords = [
            "imagine", "create", "design", "suggest", "brainstorm", 
            "generate", "story", "creative", "idea", "alternative"
        ]
    
    def analyze_message_intent(self, message: str) -> float:
        """
        Analyze message to determine if it's factual or creative
        Returns a score between 0 (factual) and 1 (creative)
        """
        message = message.lower()
        
        factual_score = 0
        for keyword in self.factual_keywords:
            if keyword in message:
                factual_score += 1
        
        creative_score = 0
        for keyword in self.creative_keywords:
            if keyword in message:
                creative_score += 1
        
        # Normalize scores
        total = factual_score + creative_score
        if total == 0:
            return 0.5  # Neutral
        
        # Higher score means more creative (higher temperature)
        return creative_score / total
    
    def get_adaptive_temperature(self, messages: List[Message], base_temperature: float) -> float:
        """
        Calculate adaptive temperature based on message content and patterns
        """
        if not self.config.dynamic_temperature:
            return base_temperature
        
        # Get the last user message
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return base_temperature
        
        last_user_message = user_messages[-1].content
        
        # Analyze intent
        intent_score = self.analyze_message_intent(last_user_message)
        
        # Calculate adaptive temperature
        # Lower bound: config.min_temperature
        # Upper bound: config.max_temperature
        # Intent score of 0 → min_temperature
        # Intent score of 1 → max_temperature
        temperature_range = self.config.max_temperature - self.config.min_temperature
        adaptive_temp = self.config.min_temperature + (intent_score * temperature_range)
        
        # Blend with base temperature (70% adaptive, 30% base)
        final_temp = (0.7 * adaptive_temp) + (0.3 * base_temperature)
        
        # Ensure within bounds
        final_temp = max(self.config.min_temperature, min(self.config.max_temperature, final_temp))
        
        logger.debug(f"Adaptive temperature: {final_temp:.2f} (base: {base_temperature:.2f}, intent: {intent_score:.2f})")
        
        return final_temp

class PatternRecognizer:
    """
    Recognizes patterns in user interactions to optimize responses
    Tracks frequent queries and adapts model behavior
    """
    
    def __init__(self, config: FireLayersConfig):
        self.config = config
        self.pattern_cache = {}  # Simple in-memory cache for patterns
        self.pattern_threshold = 3  # Number of similar queries to establish a pattern
    
    def _get_pattern_key(self, message: str) -> str:
        """Generate a simplified key for pattern matching"""
        # In production, would use more sophisticated NLP techniques
        words = message.lower().split()
        if len(words) <= 5:
            return " ".join(words)
        
        # For longer messages, use first 3 and last 2 words as signature
        return " ".join(words[:3] + ["..."] + words[-2:])
    
    def update_patterns(self, message: str) -> None:
        """Update pattern recognition with new message"""
        if not self.config.pattern_recognition:
            return
        
        pattern_key = self._get_pattern_key(message)
        
        if pattern_key in self.pattern_cache:
            self.pattern_cache[pattern_key]["count"] += 1
            self.pattern_cache[pattern_key]["last_seen"] = datetime.now()
        else:
            self.pattern_cache[pattern_key] = {
                "count": 1,
                "first_seen": datetime.now(),
                "last_seen": datetime.now()
            }
    
    def get_recognized_patterns(self) -> Dict[str, Any]:
        """Get recognized patterns that exceed the threshold"""
        if not self.config.pattern_recognition:
            return {}
        
        recognized = {}
        for key, data in self.pattern_cache.items():
            if data["count"] >= self.pattern_threshold:
                recognized[key] = data
        
        return recognized

class FireLayersX:
    """
    Main FireLayers X++ implementation
    Integrates all components for adaptive learning with Mistral 7B
    """
    
    def __init__(self, config: Optional[FireLayersConfig] = None):
        self.config = config or FireLayersConfig()
        self.context_compressor = ContextCompressor(self.config)
        self.temperature_adapter = TemperatureAdapter(self.config)
        self.pattern_recognizer = PatternRecognizer(self.config)
        self.inference_times = []  # Track inference times for optimization
    
    def preprocess_messages(self, messages: List[Message]) -> List[Message]:
        """Preprocess messages before sending to Mistral 7B"""
        if not self.config.enabled:
            return messages
        
        # Apply context compression
        compressed_messages = self.context_compressor.compress_messages(messages)
        
        # Update pattern recognition with latest user message
        user_messages = [m for m in compressed_messages if m.role == "user"]
        if user_messages:
            self.pattern_recognizer.update_patterns(user_messages[-1].content)
        
        return compressed_messages
    
    def get_optimized_parameters(self, messages: List[Message], params: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimized parameters for Mistral 7B request"""
        if not self.config.enabled:
            return params
        
        optimized = params.copy()
        
        # Apply adaptive temperature
        base_temp = params.get("temperature", 0.7)
        optimized["temperature"] = self.temperature_adapter.get_adaptive_temperature(
            messages, base_temp
        )
        
        return optimized
    
    def record_inference_time(self, time_ms: int) -> None:
        """Record inference time for adaptive optimization"""
        self.inference_times.append(time_ms)
        
        # Keep only the last 100 inference times
        if len(self.inference_times) > 100:
            self.inference_times = self.inference_times[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about FireLayers X++ performance"""
        avg_inference_time = np.mean(self.inference_times) if self.inference_times else 0
        
        return {
            "enabled": self.config.enabled,
            "adaptive_temp_enabled": self.config.dynamic_temperature,
            "compression_enabled": self.config.context_compression,
            "pattern_recognition_enabled": self.config.pattern_recognition,
            "avg_inference_time_ms": round(avg_inference_time, 2),
            "recognized_patterns_count": len(self.pattern_recognizer.get_recognized_patterns()),
            "learning_rate": self.config.learning_rate
        }

# Singleton instance for application-wide use
fire_layers = FireLayersX()
