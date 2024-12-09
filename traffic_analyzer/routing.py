from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/processing/(?P<analysis_id>\d+)/$', consumers.VideoProcessingConsumer.as_asgi()),
]
