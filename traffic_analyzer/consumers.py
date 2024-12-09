import json
import asyncio
import cv2
import base64
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from ultralytics import YOLO
from asgiref.sync import sync_to_async
from .models import VideoAnalysis, VehicleCount
import torch
import time
from collections import defaultdict
from channels.db import database_sync_to_async

class VideoProcessingConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = YOLO('yolov8n.pt')
        self.vehicle_classes = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
        self.is_processing = True
        self.is_paused = False
        self.analysis_id = None
        self.current_frame = 0
        self.cap = None
        self.processing_task = None
        self.room_group_name = None

    async def connect(self):
        self.analysis_id = self.scope['url_route']['kwargs']['analysis_id']
        self.room_group_name = f'processing_{self.analysis_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Start processing monitoring
        asyncio.create_task(self.monitor_processing())

        self.processing_task = asyncio.create_task(self.process_video())

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        self.is_processing = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'pause':
                self.is_paused = True
                await self.send(json.dumps({
                    'type': 'status',
                    'message': 'Processing paused'
                }))
            elif action == 'resume':
                self.is_paused = False
                await self.send(json.dumps({
                    'type': 'status',
                    'message': 'Processing resumed'
                }))
            elif action == 'restart':
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame = 0
                    self.is_paused = False
                    await self.send(json.dumps({
                        'type': 'status',
                        'message': 'Processing restarted'
                    }))
            elif action == 'request_status':
                # Send current processing status
                status = await self.get_processing_status()
                await self.send_status_update(status)

        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
        except Exception as e:
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def processing_update(self, event):
        # Send processing update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'overall_progress': event['overall_progress'],
            'current_stage': event['current_stage'],
            'stage_progress': event['stage_progress'],
            'stats': event['stats']
        }))

    @database_sync_to_async
    def get_processing_status(self):
        analysis = VideoAnalysis.objects.get(id=self.analysis_id)
        return {
            'status': analysis.status,
            'progress': analysis.progress,
            'frames_processed': analysis.frames_processed,
            'total_frames': analysis.total_frames,
            'vehicles_detected': analysis.vehicles_detected,
            'current_stage': analysis.current_stage,
            'stage_progress': analysis.stage_progress
        }

    async def send_status_update(self, status):
        await self.send(json.dumps({
            'type': 'status_update',
            'status': status
        }))

    async def monitor_processing(self):
        """Monitor processing progress and send updates."""
        while True:
            try:
                status = await self.get_processing_status()
                
                # Calculate stage-specific progress
                stage_info = {
                    'loading': (1, 0),
                    'extracting': (2, 25),
                    'detecting': (3, 50),
                    'analyzing': (4, 75)
                }
                
                current_stage = status['current_stage']
                stage_num, base_progress = stage_info.get(current_stage, (1, 0))
                stage_progress = status['stage_progress']
                
                # Calculate overall progress
                overall_progress = base_progress + (stage_progress * 0.25)
                
                # Prepare stats
                stats = {
                    'frames_processed': status['frames_processed'],
                    'total_frames': status['total_frames'],
                    'vehicles_detected': status['vehicles_detected']
                }
                
                # Send update through channel layer
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'processing_update',
                        'overall_progress': overall_progress,
                        'current_stage': stage_num,
                        'stage_progress': stage_progress,
                        'stats': stats
                    }
                )
                
                # Check if processing is complete
                if status['status'] == 'completed':
                    break
                    
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Error in monitor_processing: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    @sync_to_async
    def get_video_path(self):
        analysis = VideoAnalysis.objects.get(id=self.analysis_id)
        return analysis.video.path

    @sync_to_async
    def save_detection(self, frame_number, detection_data):
        analysis = VideoAnalysis.objects.get(id=self.analysis_id)
        VehicleCount.objects.create(
            analysis=analysis,
            frame_number=frame_number,
            vehicle_type=detection_data['type'],
            confidence=detection_data['confidence'],
            bbox_x1=detection_data['bbox'][0],
            bbox_y1=detection_data['bbox'][1],
            bbox_x2=detection_data['bbox'][2],
            bbox_y2=detection_data['bbox'][3]
        )

    def calculate_traffic_insights(self, detections, frame_size):
        # Calculate congestion level
        frame_area = frame_size[0] * frame_size[1]
        occupied_area = sum([(box[2] - box[0]) * (box[3] - box[1]) for box in [d['bbox'] for d in detections]])
        congestion_ratio = occupied_area / frame_area
        
        # Determine congestion level
        if congestion_ratio < 0.1:
            congestion_level = "Low"
        elif congestion_ratio < 0.2:
            congestion_level = "Moderate"
        else:
            congestion_level = "High"

        # Calculate average speeds and identify speeding vehicles
        speeds = [d.get('speed', 0) for d in detections]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        speeding_vehicles = len([s for s in speeds if s > 60])  # Assuming 60 km/h speed limit

        # Calculate vehicle type distribution
        vehicle_types = [d['type'] for d in detections]
        type_distribution = {vtype: vehicle_types.count(vtype) for vtype in set(vehicle_types)}

        # Identify potential concerns
        concerns = []
        if congestion_ratio > 0.2:
            concerns.append("High traffic congestion detected")
        if speeding_vehicles > 0:
            concerns.append(f"{speeding_vehicles} vehicles exceeding speed limit")
        if len([v for v in vehicle_types if v in ['truck', 'bus']]) / (len(vehicle_types) or 1) > 0.3:
            concerns.append("High proportion of heavy vehicles")

        # Generate recommendations
        recommendations = []
        if congestion_ratio > 0.2:
            recommendations.append("Consider implementing traffic flow management")
        if speeding_vehicles > 0:
            recommendations.append("Enhance speed monitoring and enforcement")
        if avg_speed < 20 and len(detections) > 5:
            recommendations.append("Consider adding additional lanes or alternative routes")

        return {
            "congestion_level": congestion_level,
            "average_speed": round(avg_speed, 1),
            "vehicle_distribution": type_distribution,
            "concerns": concerns,
            "recommendations": recommendations
        }

    async def process_video(self):
        try:
            video = cv2.VideoCapture(self.video_path)
            while self.is_processing and video.isOpened():
                if not self.is_paused:
                    ret, frame = video.read()
                    if not ret:
                        break

                    # Process frame with YOLO
                    results = self.model(frame)
                
                    # Draw detections and get stats
                    frame_draw, detections = self.process_detections(results, frame)
                
                    # Convert frame to base64
                    _, buffer = cv2.imencode('.jpg', frame_draw)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                    # Send frame and detections to client
                    await self.send(json.dumps({
                        'type': 'frame_update',
                        'frame': frame_base64,
                        'detections': detections,
                        'vehicle_counts': self.vehicle_counts,
                        'frame_number': self.current_frame,
                        'timestamp': self.current_frame / self.fps
                    }))

                    self.current_frame += 1
                
                await asyncio.sleep(1/30)  # Limit to 30 FPS
            
        except Exception as e:
            print(f"Error in process_video: {e}")
        finally:
            if video.isOpened():
                video.release()
