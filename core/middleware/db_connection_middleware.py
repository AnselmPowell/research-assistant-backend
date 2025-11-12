"""
Database connection middleware for handling connection errors.
"""

import logging
from django.db import connection
from django.db.utils import OperationalError
from core.utils.db_utils import ensure_connection

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    """
    Middleware to handle database connection issues.
    
    This middleware checks for and attempts to recover from database
    connection errors before processing each request.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check connection before processing request
        try:
            connection.ensure_connection()
        except OperationalError:
            # Try to reconnect
            logger.warning("Database connection lost before processing request")
            if not ensure_connection():
                logger.error("Failed to reconnect to database")
                # Return a simple error response
                from django.http import JsonResponse
                return JsonResponse({
                    "error": "Database connection error",
                    "message": "The server is experiencing database connectivity issues. Please try again later."
                }, status=503)
        
        # Process the request
        response = self.get_response(request)
        
        # Return the response
        return response