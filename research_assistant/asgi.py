

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')

# Initialize Django apps BEFORE any imports
django.setup()

# CRITICAL FIX: Try WebSocket routing first, fall back to HTTP-only
try:
    from core.routing import websocket_urlpatterns
    
    # Create ASGI application with full routing
    application = ProtocolTypeRouter({
        "http": get_asgi_application(),  # Create Django ASGI app here
        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    })
    print("🔌 WEBSOCKET DEBUG - Full routing with WebSocket support enabled")
    print("🔌 ASGI DEBUG - Django HTTP app created within ProtocolTypeRouter")
    
except Exception as e:
    # If WebSocket import fails, use HTTP-only with proper Django app
    print(f"🔌 WEBSOCKET DEBUG - WebSocket import failed: {e}")
    print("🔌 WEBSOCKET DEBUG - Using HTTP-only mode")
    
    # Create HTTP-only ASGI application
    application = get_asgi_application()
    print("🔌 ASGI DEBUG - Using direct Django ASGI application")