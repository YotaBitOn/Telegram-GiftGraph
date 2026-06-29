from django.urls import path, re_path

from graph import views, consumers

ws_urlpatterns = [
    re_path(r'ws/graph/?$', consumers.GraphConsumer.as_asgi()),
]
