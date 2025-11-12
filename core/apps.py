"""
App configuration for the core application.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Research Assistant Core'
    
    def ready(self):
        """Run when the app is ready."""
        import core.signals  # noqa
