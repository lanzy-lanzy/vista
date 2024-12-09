# API Reference

## REST API Endpoints

### Video Analysis

#### Upload Video
```http
POST /api/videos/upload/
Content-Type: multipart/form-data

Parameters:
- video_file: File (required)
- analysis_config: JSON (optional)
```

Response:
```json
{
    "analysis_id": "string",
    "status": "pending",
    "upload_time": "datetime"
}
```

#### Get Analysis Status
```http
GET /api/analysis/{analysis_id}/status/
```

Response:
```json
{
    "analysis_id": "string",
    "status": "string",
    "progress": float,
    "error_message": "string",
    "processing_time": float
}
```

#### Get Analysis Results
```http
GET /api/analysis/{analysis_id}/results/
```

Response:
```json
{
    "analysis_id": "string",
    "vehicle_counts": {
        "car": integer,
        "truck": integer,
        "bus": integer,
        "motorcycle": integer,
        "bicycle": integer
    },
    "temporal_distribution": [
        {
            "timestamp": "datetime",
            "counts": object
        }
    ],
    "zone_statistics": [
        {
            "zone_id": "string",
            "counts": object
        }
    ]
}
```

### Live Feed

#### Start Live Feed
```http
POST /api/live/start/
Content-Type: application/json

{
    "camera_id": "string",
    "config": object
}
```

Response:
```json
{
    "session_id": "string",
    "stream_url": "string",
    "status": "string"
}
```

#### Stop Live Feed
```http
POST /api/live/stop/
Content-Type: application/json

{
    "session_id": "string"
}
```

### Detection Zones

#### Create Zone
```http
POST /api/zones/create/
Content-Type: application/json

{
    "name": "string",
    "coordinates": array,
    "analysis_id": "string"
}
```

#### List Zones
```http
GET /api/zones/
```

## WebSocket API

### Connection

Connect to:
```
ws://host/ws/analysis/{analysis_id}/
```

### Message Types

#### Processing Updates
```json
{
    "type": "processing_update",
    "data": {
        "progress": float,
        "fps": float,
        "counts": object,
        "detections": array
    }
}
```

#### Status Changes
```json
{
    "type": "status_change",
    "data": {
        "status": "string",
        "message": "string"
    }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400  | Bad Request |
| 401  | Unauthorized |
| 404  | Not Found |
| 500  | Internal Server Error |
| 503  | Service Unavailable |

## Rate Limits

- API calls: 100 requests per minute
- Video uploads: 10 per hour
- WebSocket connections: 5 concurrent per user
