from django.db import models
import json

class VideoAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    video = models.FileField(upload_to='videos/')
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_progress = models.FloatField(default=0)  # Progress percentage
    error_message = models.TextField(null=True, blank=True)
    results_data = models.TextField(null=True, blank=True)  # Changed from JSONField to TextField
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    def get_results_data(self):
        if self.results_data:
            try:
                return json.loads(self.results_data)
            except json.JSONDecodeError:
                return None
        return None

    def set_results_data(self, data):
        if data is not None:
            self.results_data = json.dumps(data)
        else:
            self.results_data = None
    
    def get_vehicle_counts(self):
        return self.vehiclecount_set.all()
    
    def get_hourly_distribution(self):
        counts = self.vehiclecount_set.all()
        hourly_data = {}
        for count in counts:
            hour = count.timestamp.strftime('%H:00')
            if hour not in hourly_data:
                hourly_data[hour] = {}
            if count.vehicle_type not in hourly_data[hour]:
                hourly_data[hour][count.vehicle_type] = 0
            hourly_data[hour][count.vehicle_type] += count.count
        return hourly_data

    def __str__(self):
        return f"Analysis {self.id} - {self.timestamp}"

class VehicleCount(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('bus', 'Bus'),
        ('motorcycle', 'Motorcycle'),
        ('bicycle', 'Bicycle'),
    ]
    
    analysis = models.ForeignKey(VideoAnalysis, on_delete=models.CASCADE)
    frame_number = models.IntegerField()
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    confidence = models.FloatField()
    bbox_x1 = models.FloatField()
    bbox_y1 = models.FloatField()
    bbox_x2 = models.FloatField()
    bbox_y2 = models.FloatField()
    speed = models.FloatField(default=0.0)  # Speed in km/h
    timestamp = models.DateTimeField(auto_now_add=True)
    count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['timestamp']
    
    def get_center(self):
        return ((self.bbox_x1 + self.bbox_x2) / 2, (self.bbox_y1 + self.bbox_y2) / 2)

    def get_area(self):
        return (self.bbox_x2 - self.bbox_x1) * (self.bbox_y2 - self.bbox_y1)

    def __str__(self):
        return f"{self.vehicle_type} at {self.timestamp}"

class DetectionZone(models.Model):
    analysis = models.ForeignKey(VideoAnalysis, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    coordinates = models.TextField()  # Changed from JSONField to TextField
    
    def get_coordinates(self):
        if self.coordinates:
            try:
                return json.loads(self.coordinates)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_coordinates(self, coords):
        if coords is not None:
            self.coordinates = json.dumps(coords)
        else:
            self.coordinates = None
    
    def __str__(self):
        return f"{self.name}: {self.count}"