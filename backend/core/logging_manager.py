"""
Structured Logging Manager for ZealX Backend
Provides comprehensive logging for AutoX actions and system events
"""

import logging
import json
import os
import time
import sqlite3
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

from backend.models.api import AutoXLog

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create logger
logger = logging.getLogger("zealx")

class SQLiteLogHandler:
    """
    SQLite-based log handler for persistent storage of execution logs
    Thread-safe implementation with connection pooling
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.local = threading.local()
        self._initialize_db()
    
    def _get_connection(self):
        """Get a thread-local SQLite connection"""
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.local.connection.execute("PRAGMA foreign_keys = ON")
        return self.local.connection
    
    def _initialize_db(self):
        """Initialize the SQLite database with required tables"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            # Create tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    app_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            
            # Create logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Create index for faster queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_task_id ON logs(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
            
            conn.commit()
            logger.info(f"SQLite log database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")
        finally:
            conn.close()
    
    def log_task(self, task_id: str, app_id: str, action_type: str, 
                action_data: Dict[str, Any], priority: int, status: str):
        """Log a new task or update an existing task"""
        self.executor.submit(self._log_task, task_id, app_id, action_type, 
                           action_data, priority, status)
    
    def _log_task(self, task_id: str, app_id: str, action_type: str, 
                action_data: Dict[str, Any], priority: int, status: str):
        """Internal method to log a task (runs in thread pool)"""
        conn = self._get_connection()
        try:
            # Check if task exists
            cursor = conn.execute(
                "SELECT task_id FROM tasks WHERE task_id = ?", 
                (task_id,)
            )
            task_exists = cursor.fetchone() is not None
            
            if task_exists:
                # Update existing task
                completed_at = datetime.now().isoformat() if status in ["completed", "failed"] else None
                conn.execute(
                    """
                    UPDATE tasks 
                    SET status = ?, completed_at = ?
                    WHERE task_id = ?
                    """,
                    (status, completed_at, task_id)
                )
            else:
                # Insert new task
                conn.execute(
                    """
                    INSERT INTO tasks 
                    (task_id, app_id, action_type, action_data, priority, created_at, status, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id, 
                        app_id, 
                        action_type, 
                        json.dumps(action_data), 
                        priority,
                        datetime.now().isoformat(),
                        status,
                        None
                    )
                )
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging task: {e}")
            conn.rollback()
    
    def log_action(self, log_entry: AutoXLog):
        """Log an action for a task"""
        self.executor.submit(self._log_action, log_entry)
    
    def _log_action(self, log_entry: AutoXLog):
        """Internal method to log an action (runs in thread pool)"""
        conn = self._get_connection()
        try:
            log_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO logs 
                (log_id, task_id, timestamp, action, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    log_entry.task_id,
                    log_entry.timestamp.isoformat(),
                    log_entry.action,
                    log_entry.status,
                    json.dumps(log_entry.details)
                )
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            conn.rollback()
    
    def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific task"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT log_id, task_id, timestamp, action, status, details
                FROM logs
                WHERE task_id = ?
                ORDER BY timestamp ASC
                """,
                (task_id,)
            )
            
            logs = []
            for row in cursor.fetchall():
                log_id, task_id, timestamp, action, status, details = row
                logs.append({
                    "log_id": log_id,
                    "task_id": task_id,
                    "timestamp": timestamp,
                    "action": action,
                    "status": status,
                    "details": json.loads(details) if details else {}
                })
            
            return logs
        except Exception as e:
            logger.error(f"Error retrieving task logs: {e}")
            return []
    
    def get_recent_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tasks with their status"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT task_id, app_id, action_type, action_data, priority, created_at, status, completed_at
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            
            tasks = []
            for row in cursor.fetchall():
                task_id, app_id, action_type, action_data, priority, created_at, status, completed_at = row
                tasks.append({
                    "task_id": task_id,
                    "app_id": app_id,
                    "action_type": action_type,
                    "action_data": json.loads(action_data),
                    "priority": priority,
                    "created_at": created_at,
                    "status": status,
                    "completed_at": completed_at
                })
            
            return tasks
        except Exception as e:
            logger.error(f"Error retrieving recent tasks: {e}")
            return []
    
    def close(self):
        """Close the executor and connections"""
        self.executor.shutdown(wait=True)
        if hasattr(self.local, "connection"):
            self.local.connection.close()

class LoggingManager:
    """
    Manages logging across the ZealX backend
    Provides structured logging for AutoX actions and system events
    """
    
    def __init__(self, log_dir: str = "logs"):
        # Ensure log directory exists
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize SQLite log handler
        db_path = os.path.join(log_dir, "zealx_logs.db")
        self.sqlite_handler = SQLiteLogHandler(db_path)
        
        # Set up file handler for general logs
        file_handler = logging.FileHandler(os.path.join(log_dir, "zealx.log"))
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to root logger
        logger.addHandler(file_handler)
        
        logger.info("Logging manager initialized")
    
    async def log_task(self, task_id: str, app_id: str, action_type: str, 
                     action_data: Dict[str, Any], priority: int, status: str):
        """Log a task asynchronously"""
        self.sqlite_handler.log_task(task_id, app_id, action_type, action_data, priority, status)
        logger.info(f"Task {task_id} ({action_type}) status: {status}")
    
    async def log_action(self, task_id: str, action: str, status: str, details: Dict[str, Any] = None):
        """Log an action for a task asynchronously"""
        log_entry = AutoXLog(
            task_id=task_id,
            action=action,
            status=status,
            details=details or {}
        )
        
        self.sqlite_handler.log_action(log_entry)
        
        # Also log to standard logger
        log_msg = f"Task {task_id} - {action}: {status}"
        if details:
            log_msg += f" - {json.dumps(details)}"
        
        if status == "error":
            logger.error(log_msg)
        else:
            logger.info(log_msg)
        
        return log_entry
    
    async def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific task"""
        return self.sqlite_handler.get_task_logs(task_id)
    
    async def get_recent_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tasks with their status"""
        return self.sqlite_handler.get_recent_tasks(limit)
    
    def close(self):
        """Close the logging manager"""
        self.sqlite_handler.close()
        logger.info("Logging manager closed")

# Singleton instance for application-wide use
logging_manager = LoggingManager()
