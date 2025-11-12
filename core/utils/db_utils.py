"""
Database utilities for connection handling and retries.
"""

import time
import logging
from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)

def ensure_connection():
    """
    Ensure database connection is active, retry if needed.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    db_conn = connections['default']
    try:
        c = db_conn.cursor()
        c.execute("SELECT 1")
        return True
    except OperationalError as e:
        logger.warning(f"Database connection error: {e}")
        
        # Connection might be closed, try to reconnect
        for i in range(3):  # Try 3 times
            try:
                logger.info(f"Attempting database reconnection (attempt {i+1}/3)")
                db_conn.close()
                db_conn.connect()
                logger.info("Database reconnection successful")
                return True
            except OperationalError as e:
                logger.warning(f"Reconnection attempt {i+1} failed: {e}")
                time.sleep(1 * (i + 1))  # Exponential backoff
        
        logger.error("All database reconnection attempts failed")
        return False
