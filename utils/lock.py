"""Utility for managing bot instance locking."""

import os
import sys
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

class BotLock:
    """Class to manage bot instance locking."""
    
    def __init__(self, lock_file_path: Optional[str] = None):
        """Initialize the bot lock.
        
        Args:
            lock_file_path: Optional path to the lock file. If not provided,
                           uses the default path in the project directory.
        """
        if lock_file_path is None:
            # Use the project root directory for the lock file
            project_root = Path(__file__).parent.parent
            self.lock_file = project_root / 'crypto_agent.lock'
        else:
            self.lock_file = Path(lock_file_path)
    
    def acquire(self) -> bool:
        """Try to acquire the lock.
        
        Returns:
            bool: True if lock was acquired, False if another instance is running.
        """
        try:
            # Check if lock file exists
            if self.lock_file.exists():
                # Check if the process in the lock file is still running
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Check if process is running
                try:
                    os.kill(pid, 0)  # Doesn't actually kill the process
                    logger.error(f"Another bot instance is already running (PID: {pid})")
                    return False
                except OSError:
                    # Process is not running, we can remove the stale lock
                    logger.warning("Found stale lock file, removing it")
                    self.release()
            
            # Create lock file with current PID
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            return True
            
        except Exception as e:
            logger.error(f"Error while acquiring lock: {str(e)}")
            return False
    
    def release(self) -> None:
        """Release the lock by removing the lock file."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.error(f"Error while releasing lock: {str(e)}")