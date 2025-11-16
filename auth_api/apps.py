"""
Django app configuration for auth_api.
"""

from django.apps import AppConfig


class AuthApiConfig(AppConfig):
    """Configuration for the auth_api application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_api'
    verbose_name = 'Authentication & User Management'
    
    def ready(self):
        """
        Initialize the application.
        Import signals and perform any startup tasks.
        """
        # Import signals if needed in future
        pass
