from django.contrib import admin
from .models import VideoAnalysis, VehicleCount, DetectionZone

@admin.register(VideoAnalysis)
class VideoAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'status')
    list_filter = ('status',)

@admin.register(VehicleCount)
class VehicleCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle_type', 'frame_number', 'confidence', 'speed')
    list_filter = ('vehicle_type',)

@admin.register(DetectionZone)
class DetectionZoneAdmin(admin.ModelAdmin):
    list_display = ['id']
