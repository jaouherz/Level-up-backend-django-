"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import api.routing  # <-- make sure api/routing.py exists

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# First, create the normal Django ASGI app
django_asgi_app = get_asgi_application()

# Then wrap it in ProtocolTypeRouter for HTTP + WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(api.routing.websocket_urlpatterns)
    ),
})
