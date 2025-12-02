"""
ASGI config for research_assistant project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')

# Initialize Django apps BEFORE importing routing
django.setup()

# Now safely import routing (after Django apps are loaded)
from core.routing import websocket_urlpatterns

# Initialize HTTP ASGI application
django_asgi_app = get_asgi_application()

# Create the main ASGI application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
