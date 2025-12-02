from django.conf import settings

def debug_print(message):
    """Print only in DEBUG mode."""
    if settings.DEBUG:
        print(message)