from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.video_upload, name='video_upload'),
    path('live/', views.live_detection, name='live_detection'),
    path('live/feed/', views.live_feed, name='live_feed'),
    path('analysis/<int:analysis_id>/results/', views.analysis_results, name='analysis_results'),
    path('analysis/<int:analysis_id>/processing/', views.processing, name='processing'),
    path('analysis/<int:analysis_id>/status/', views.analysis_status, name='analysis_status'),

]