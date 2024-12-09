# Configuration Guide

## Environment Variables

Create a `.env` file in the project root with the following configurations:

```env
# Debug Settings
DEBUG=True
DEVELOPMENT_MODE=True

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
# For PostgreSQL:
# DATABASE_URL=postgres://user:password@localhost:5432/vistav1

# Media Settings
MEDIA_ROOT=media/
MEDIA_URL=/media/

# YOLO Settings
YOLO_MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.5
IOU_THRESHOLD=0.45

# Processing Settings
MAX_UPLOAD_SIZE=524288000  # 500MB
PROCESS_BATCH_SIZE=32
MAX_CONCURRENT_PROCESSES=4

# WebSocket Settings
CHANNEL_LAYERS_HOST=localhost
CHANNEL_LAYERS_PORT=6379
```

## Django Settings

### Base Settings (settings.py)

```python
# Application Definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'vista.traffic_analyzer',
]

# Middleware Configuration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
```

## YOLO Configuration

### Model Settings

```python
# vista/traffic_analyzer/config.py

YOLO_CONFIG = {
    'model_path': 'yolov8n.pt',
    'confidence_threshold': 0.5,
    'iou_threshold': 0.45,
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
    'classes': [
        'bicycle',
        'car',
        'motorcycle',
        'bus',
        'truck'
    ]
}

DETECTION_CONFIG = {
    'max_detection_size': 1024,
    'min_detection_size': 32,
    'process_every_n_frames': 1,
}
```

## Processing Pipeline Configuration

### Queue Settings

```python
PROCESSING_CONFIG = {
    'max_queue_size': 100,
    'batch_size': 32,
    'max_concurrent_processes': 4,
    'timeout': 3600,  # 1 hour
}
```

### Storage Settings

```python
STORAGE_CONFIG = {
    'max_file_size': 524288000,  # 500MB
    'allowed_formats': ['mp4', 'avi', 'mov'],
    'temp_dir': 'temp/',
    'results_dir': 'results/',
}
```

## WebSocket Configuration

### Channel Layers

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('CHANNEL_LAYERS_HOST', 'localhost'),
                      int(os.getenv('CHANNEL_LAYERS_PORT', 6379)))],
        },
    },
}
```

## Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'vista.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'vista': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Security Configuration

```python
# Security Settings
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```
