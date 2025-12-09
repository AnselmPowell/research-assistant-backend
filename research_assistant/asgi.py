

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')

# Initialize Django apps BEFORE importing routing
django.setup()

# Initialize HTTP ASGI application
django_asgi_app = get_asgi_application()

# TEMPORARY FIX: Disable WebSocket routing to test if it's causing 502 errors
# Try to import WebSocket routing, but fall back to HTTP-only if it fails
try:
    from core.routing import websocket_urlpatterns
    # If import succeeds, use full routing
    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    })
    print("🔌 WEBSOCKET DEBUG - Full routing with WebSocket support enabled")
except Exception as e:
    # If import fails, use HTTP-only
    print(f"🔌 WEBSOCKET DEBUG - WebSocket import failed: {e}")
    print("🔌 WEBSOCKET DEBUG - Using HTTP-only mode")
    application = ProtocolTypeRouter({
        "http": django_asgi_app,
    })
    # Use HTTP-only mode for now