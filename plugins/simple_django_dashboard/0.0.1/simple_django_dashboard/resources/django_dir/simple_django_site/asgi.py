import os
from django.core.asgi import get_asgi_application

from dashboard import websocket

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sockets.settings')

django_asgi_app = get_asgi_application()

async def application(scope, receive, send):
    if scope['type'] == 'http':
        await django_asgi_app(scope, receive, send)
    elif scope['type'] == 'websocket':
        await websocket.websocket_application(scope, receive, send)
    else:
        raise NotImplementedError(f"Unsupported scope type: {scope['type']}")