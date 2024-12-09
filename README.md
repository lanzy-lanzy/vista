# Vista v1 - Traffic Analysis System

A modern and intelligent traffic analysis system built with Django and YOLOv8, designed to process and analyze traffic video feeds in real-time.

## Project Overview

Vista v1 is an advanced traffic monitoring and analysis platform that leverages computer vision to:
- Detect and classify different types of vehicles (cars, trucks, buses, motorcycles, bicycles)
- Process both uploaded videos and live camera feeds
- Generate real-time analytics and visualizations
- Track vehicle movements and generate traffic patterns
- Provide detailed analysis reports

## Features

- **Real-time Vehicle Detection**
  - Multi-class vehicle detection using YOLOv8
  - Support for various vehicle types
  - Confidence-based detection filtering

- **Video Processing**
  - Upload and process traffic videos
  - Live camera feed integration
  - Progress tracking for video analysis
  - Error handling and recovery

- **Analysis and Reporting**
  - Vehicle count statistics
  - Temporal distribution analysis
  - Detection zone configuration
  - Interactive visualizations

## Technical Architecture

### Models (`traffic_analyzer/models.py`)

- **VideoAnalysis**: Manages video processing state and results
  - Tracks processing status (pending/processing/completed/failed)
  - Stores analysis results and progress
  - Handles error reporting

- **VehicleCount**: Records individual vehicle detections
  - Stores vehicle type, position, and confidence
  - Tracks temporal information
  - Maintains bounding box coordinates

- **DetectionZone**: Defines areas of interest for analysis
  - Configurable detection zones
  - Coordinate-based zone definition

### Views (`traffic_analyzer/views.py`)

- Real-time video processing using YOLOv8
- WebSocket integration for live updates
- Comprehensive error handling
- Progress tracking and status updates
- Results visualization and reporting

## Getting Started

### Prerequisites

- Python 3.8+
- Django
- OpenCV
- YOLOv8
- Additional requirements:
  ```
  ultralytics
  opencv-python
  numpy
  plotly
  pandas
  channels
  ```

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure Django settings
4. Run migrations:
   ```bash
   python manage.py migrate
   ```

### Usage

1. Start the Django development server:
   ```bash
   python manage.py runserver
   ```
2. Access the application at `http://localhost:8000`
3. Upload a video for analysis or connect to a live camera feed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions and support, please open an issue in the repository.

---
Last updated: December 9, 2024
