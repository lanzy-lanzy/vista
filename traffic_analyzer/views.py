import cv2
import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators import gzip
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from .models import VideoAnalysis, VehicleCount, DetectionZone
from ultralytics import YOLO
from pathlib import Path
import threading
import queue
import time
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from django.conf import settings
import os
import json
from tqdm import tqdm
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import base64

# Initialize YOLO model
model = YOLO('yolov8n.pt')

class VideoProcessor:
    def __init__(self):
        self.model = model
        self.classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck']
        self.processing_queue = queue.Queue()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.active_analyses = {}
        self.thread.start()

    def _process_queue(self):
        while True:
            if not self.processing_queue.empty():
                analysis_id = self.processing_queue.get()
                try:
                    self._process_video(analysis_id)
                except Exception as e:
                    self._handle_processing_error(analysis_id, str(e))
                finally:
                    if analysis_id in self.active_analyses:
                        del self.active_analyses[analysis_id]
                self.processing_queue.task_done()
            time.sleep(1)

    def _handle_processing_error(self, analysis_id, error_message):
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            analysis.status = 'failed'
            analysis.error_message = f"Processing failed: {error_message}"
            analysis.save()
            
            # Notify frontend about the error
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'video_{analysis_id}',
                {
                    'type': 'processing_error',
                    'message': error_message
                }
            )
        except VideoAnalysis.DoesNotExist:
            print(f"Error: Analysis {analysis_id} not found")
        except Exception as e:
            print(f"Error handling processing error: {str(e)}")

    def _process_video(self, analysis_id):
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        channel_layer = get_channel_layer()
        
        try:
            if analysis.status != 'processing':
                analysis.status = 'processing'
                analysis.save()
                
            video_path = analysis.video.path
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise Exception("Could not open video file")
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            start_time = time.time()
            vehicle_counts = {'bicycle': 0, 'car': 0, 'truck': 0, 'bus': 0, 'motorcycle': 0}
            
            # Create detection zones if not exist
            if not DetectionZone.objects.filter(analysis=analysis).exists():
                DetectionZone.objects.create(
                    analysis=analysis,
                    name='Full Frame',
                    coordinates=json.dumps([[0, 0], [1, 0], [1, 1], [0, 1]])
                )
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                
                # Process every frame for bicycles
                # Enhance frame for better detection
                frame = cv2.convertScaleAbs(frame, alpha=1.3, beta=10)  # Increased contrast and brightness
                
                # First pass: detect only bicycles with very low threshold
                bicycle_results = self.model(frame, 
                                          classes=[1],  # bicycle only
                                          conf=0.2,    # Very low confidence threshold for bicycles
                                          iou=0.3)     # Lower IOU threshold
                
                # Second pass: detect other vehicles with normal threshold
                other_results = self.model(frame, 
                                         classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck
                                         conf=0.5,    # Normal confidence for other vehicles
                                         iou=0.45)
                
                # Combine results
                detections = []
                
                # Process bicycle detections first
                for r in bicycle_results:
                    boxes = r.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        
                        # Calculate relative size of detection
                        box_size = (x2 - x1) * (y2 - y1) / (frame.shape[0] * frame.shape[1])
                        
                        # Debug logging for bicycle detections
                        print(f"Frame {frame_count}: Bicycle detected - Confidence: {conf:.2f}, Size: {box_size:.6f}")
                        
                        if conf > 0.2:  # Very low threshold for bicycles
                            vehicle_type = 'bicycle'
                            vehicle_counts[vehicle_type] = vehicle_counts.get(vehicle_type, 0) + 1
                            detections.append({
                                'type': vehicle_type,
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)]
                            })
                
                # Process other vehicle detections
                for r in other_results:
                    boxes = r.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        
                        if conf > 0.5:  # Normal threshold for other vehicles
                            vehicle_type = self.get_vehicle_type(cls)
                            if vehicle_type:
                                vehicle_counts[vehicle_type] = vehicle_counts.get(vehicle_type, 0) + 1
                                detections.append({
                                    'type': vehicle_type,
                                    'confidence': conf,
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)]
                                })
                
                # Calculate current FPS
                elapsed_time = time.time() - start_time
                current_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                
                # Calculate progress
                progress = frame_count / total_frames
                
                # Send update through WebSocket
                async_to_sync(channel_layer.group_send)(
                    f'video_{analysis_id}',
                    {
                        'type': 'processing_update',
                        'progress': progress,
                        'fps': current_fps,
                        'counts': vehicle_counts,
                        'detections': detections
                    }
                )
                
                # Update progress in database
                analysis.processing_progress = progress
                analysis.save(update_fields=['processing_progress'])
                
                # Save detection to database
                for detection in detections:
                    VehicleCount.objects.create(
                        analysis=analysis,
                        frame_number=frame_count,
                        vehicle_type=detection['type'],
                        confidence=detection['confidence'],
                        bbox_x1=detection['bbox'][0],
                        bbox_y1=detection['bbox'][1],
                        bbox_x2=detection['bbox'][2],
                        bbox_y2=detection['bbox'][3],
                        timestamp=frame_count / fps
                    )
            
            cap.release()
            
            # Update analysis status
            analysis.status = 'completed'
            analysis.processed = True
            analysis.save()
            
            # Send completion message
            async_to_sync(channel_layer.group_send)(
                f'video_{analysis_id}',
                {
                    'type': 'processing_complete',
                    'results_url': f'/analysis/{analysis_id}/results/'
                }
            )
            
        except Exception as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
            
            async_to_sync(channel_layer.group_send)(
                f'video_{analysis_id}',
                {
                    'type': 'processing_error',
                    'message': str(e)
                }
            )
            raise
    
    def get_vehicle_type(self, class_id):
        class_map = {
            1: 'bicycle',
            2: 'car',
            3: 'motorcycle',
            5: 'bus',
            7: 'truck'
        }
        return class_map.get(class_id)
    
    def queue_video(self, analysis_id):
        self.processing_queue.put(analysis_id)

video_processor = VideoProcessor()

class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.model = model
        self.classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck']
        
    def __del__(self):
        if self.video and self.video.isOpened():
            self.video.release()
        cv2.destroyAllWindows()

    def get_frame(self):
        success, frame = self.video.read()
        if not success:
            return None
        
        results = self.model(frame)
        
        # Draw detection boxes
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if conf > 0.3 and self.classes[cls] in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f'{self.classes[cls]} {conf:.2f}',
                              (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@gzip.gzip_page
def live_feed(request):
    try:
        return StreamingHttpResponse(gen(VideoCamera()),
                                   content_type='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(e)
        return None

def home(request):
    recent_analyses = VideoAnalysis.objects.order_by('-timestamp')[:5]
    return render(request, 'traffic_analyzer/home.html', {'recent_analyses': recent_analyses})

def video_upload(request):
    if request.method == 'POST' and request.FILES.get('video'):
        video_file = request.FILES['video']
        
        # Check file size (1.5GB = 1572864000 bytes)
        if video_file.size > 1572864000:
            return render(request, 'traffic_analyzer/video_upload.html', {
                'error': 'Video file size must be less than 1.5GB'
            })
        
        analysis = VideoAnalysis.objects.create(
            video=video_file,
            status='pending'
        )
        return redirect('processing', analysis_id=analysis.id)
    return render(request, 'traffic_analyzer/video_upload.html')

def live_detection(request):
    return render(request, 'traffic_analyzer/live_detection.html')

def processing(request, analysis_id):
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id)
    
    if not analysis.video:
        return JsonResponse({
            'error': 'No video file found for this analysis.'
        }, status=400)
    
    # Queue the video for processing if not already processing
    if analysis.status == 'pending':
        analysis.status = 'processing'
        analysis.save()
        video_processor.queue_video(analysis_id)
    elif analysis.status == 'failed':
        # If previous attempt failed, retry
        analysis.status = 'processing'
        analysis.error_message = None
        analysis.save()
        video_processor.queue_video(analysis_id)
    
    context = {
        'analysis_id': analysis_id,
        'video_url': analysis.video.url,
        'video_name': analysis.video.name.split('/')[-1],
        'upload_time': analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'status': analysis.status,
        'error_message': analysis.error_message if analysis.status == 'failed' else None,
    }
    
    return render(request, 'traffic_analyzer/processing.html', context)

def analysis_results(request, analysis_id):
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id)
    
    # Get all detections for this analysis
    detections = VehicleCount.objects.filter(analysis=analysis)
    
    # Check if we have any detections
    if not detections.exists():
        context = {
            'analysis': analysis,
            'video_url': analysis.video.url if analysis.video else None,
            'detection_data': json.dumps([]),
            'vehicle_types': json.dumps(['bicycle', 'car', 'truck', 'bus', 'motorcycle']),
            'vehicle_counts': json.dumps([0, 0, 0, 0, 0]),
            'timestamps': json.dumps([]),
            'vehicle_counts_time': json.dumps([]),
            'analysis_data': {
                'peak_hours': {
                    'start': 'N/A',
                    'end': 'N/A',
                    'count': 0
                },
                'vehicle_composition': {
                    'bicycle': 0,
                    'car': 0,
                    'truck': 0,
                    'bus': 0,
                    'motorcycle': 0
                },
                'traffic_density': {
                    'average': 0,
                    'maximum': 0
                },
                'concerns': [
                    {
                        'title': 'No Detections',
                        'description': 'No vehicles were detected in the video.'
                    }
                ],
                'recommendations': [
                    {
                        'title': 'Video Quality',
                        'description': 'Check if the video quality is sufficient for detection.'
                    },
                    {
                        'title': 'Detection Settings',
                        'description': 'Verify that detection settings are properly configured.'
                    }
                ]
            }
        }
        return render(request, 'traffic_analyzer/analysis_results.html', context)
    
    # Format detection data for frontend
    detection_data = []
    for detection in detections:
        detection_data.append({
            'timestamp': detection.frame_number / 30.0,  # Assuming 30 fps
            'vehicle_type': detection.vehicle_type,
            'confidence': detection.confidence,
            'bbox_x1': detection.bbox_x1,
            'bbox_y1': detection.bbox_y1,
            'bbox_x2': detection.bbox_x2,
            'bbox_y2': detection.bbox_y2,
        })
    
    # Calculate vehicle type distribution
    vehicle_types = ['bicycle', 'car', 'truck', 'bus', 'motorcycle']
    vehicle_counts = [
        detections.filter(vehicle_type=vtype).count()
        for vtype in vehicle_types
    ]
    
    # Calculate peak hours (only if we have detections)
    total_duration = max(d['timestamp'] for d in detection_data) if detection_data else 0
    time_slots = {}
    slot_duration = 3600  # 1 hour in seconds
    
    for detection in detection_data:
        slot = int(detection['timestamp'] // slot_duration)
        time_slots[slot] = time_slots.get(slot, 0) + 1
    
    if time_slots:
        peak_slot = max(time_slots.items(), key=lambda x: x[1])[0]
        peak_start = time.strftime('%I:%M %p', time.gmtime(peak_slot * slot_duration))
        peak_end = time.strftime('%I:%M %p', time.gmtime((peak_slot + 1) * slot_duration))
    else:
        peak_start = 'N/A'
        peak_end = 'N/A'
    
    # Calculate vehicle composition percentages
    total_vehicles = sum(vehicle_counts)
    vehicle_composition = {
        vtype: (count / total_vehicles * 100) if total_vehicles > 0 else 0
        for vtype, count in zip(vehicle_types, vehicle_counts)
    }
    
    # Calculate average vehicle density
    time_windows = {}
    window_size = 300  # 5 minutes in seconds
    
    for detection in detection_data:
        window = int(detection['timestamp'] // window_size)
        time_windows[window] = time_windows.get(window, 0) + 1
    
    avg_density = sum(time_windows.values()) / len(time_windows) if time_windows else 0
    max_density = max(time_windows.values()) if time_windows else 0
    
    # Get timestamps and counts for time series
    timestamps = list(detections.values_list('timestamp', flat=True))
    vehicle_counts_time = list(detections.values_list('count', flat=True))
    
    # Prepare analysis data with proper handling of empty data
    analysis_data = {
        'vehicle_composition': vehicle_composition
    }
    
    # Add concerns based on actual data
    concerns = []
    if total_vehicles > 0:
        max_vehicle_type = max(vehicle_composition.items(), key=lambda x: x[1])
        min_vehicle_type = min(vehicle_composition.items(), key=lambda x: x[1])
        
        if max_vehicle_type[1] > 50:  # If any vehicle type is more than 50%
            concerns.append({
                'title': 'Vehicle Type Distribution',
                'description': f'High proportion of {max_vehicle_type[0]}s ({max_vehicle_type[1]:.1f}%) indicates potential traffic imbalance.'
            })
        
        if min_vehicle_type[1] < 10 and total_vehicles > 20:  # If any vehicle type is less than 10% with sufficient data
            concerns.append({
                'title': 'Low Vehicle Type Presence',
                'description': f'Low proportion of {min_vehicle_type[0]}s ({min_vehicle_type[1]:.1f}%) might indicate infrastructure limitations.'
            })
    
    analysis_data['concerns'] = concerns if concerns else [{
        'title': 'Traffic Volume Analysis',
        'description': 'Insufficient data for detailed traffic pattern analysis.'
    }]
    
    # Add recommendations based on actual data
    recommendations = []
    if total_vehicles > 0:
        if max_vehicle_type[1] > 50:
            recommendations.append({
                'title': 'Infrastructure Adaptation',
                'description': f'Consider adapting road infrastructure to better accommodate high {max_vehicle_type[0]} traffic.'
            })
        
        recommendations.append({
            'title': 'Vehicle Composition Analysis',
            'description': 'Regular monitoring of vehicle type distribution to identify long-term traffic patterns.'
        })
    
    analysis_data['recommendations'] = recommendations if recommendations else [{
        'title': 'Data Collection',
        'description': 'Continue collecting traffic data to establish baseline patterns for future analysis.'
    }]
    
    context = {
        'analysis': analysis,
        'video_url': analysis.video.url if analysis.video else None,
        'detection_data': json.dumps(detection_data),
        'vehicle_types': json.dumps(vehicle_types),
        'vehicle_counts': json.dumps(vehicle_counts),
        'timestamps': json.dumps([t.timestamp() for t in timestamps] if timestamps else []),
        'vehicle_counts_time': json.dumps(vehicle_counts_time),
        'analysis_data': analysis_data
    }
    
    return render(request, 'traffic_analyzer/analysis_results.html', context)

@require_http_methods(["GET"])
def analysis_status(request, analysis_id):
    """Get the current status of video analysis."""
    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        
        # Get processing progress from the analysis object
        progress_data = {
            'status': analysis.status,
            'progress': analysis.progress,
            'stage_progress': {
                'loading': analysis.loading_progress,
                'extracting': analysis.extraction_progress,
                'detecting': analysis.detection_progress,
                'analyzing': analysis.analysis_progress,
            },
            'detection_counts': {
                'cars': analysis.car_count,
                'trucks': analysis.truck_count,
                'buses': analysis.bus_count,
                'motorcycles': analysis.motorcycle_count,
            }
        }
        
        return JsonResponse(progress_data)
    except VideoAnalysis.DoesNotExist:
        return JsonResponse({'error': 'Analysis not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)