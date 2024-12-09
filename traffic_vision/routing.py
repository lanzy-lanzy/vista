from django.urls import path
from traffic_analyzer.consumers import VideoProcessingConsumer

websocket_urlpatterns = [
    path('ws/processing/<str:analysis_id>/', VideoProcessingConsumer.as_asgi()),
]
