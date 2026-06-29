"""
ASGI config for graph project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from graph import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tgg.settings')

application = ProtocolTypeRouter({
    # 1. Handle standard HTTP requests
    "http": get_asgi_application(),

    # 2. Handle WebSocket requests
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.ws_urlpatterns
        )
    ),
})