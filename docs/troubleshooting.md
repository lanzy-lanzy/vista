# Troubleshooting Guide

This guide covers common issues you might encounter while using Vista v1 and their solutions.

## Common Issues

### Installation Problems

#### CUDA Not Found
```
Problem: RuntimeError: CUDA not available
```

**Solution:**
1. Verify CUDA installation:
```bash
nvidia-smi
```
2. Check PyTorch CUDA compatibility:
```python
import torch
print(torch.cuda.is_available())
```
3. Reinstall PyTorch with CUDA support:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Dependencies Installation Fails
```
Problem: Error: Microsoft Visual C++ 14.0 or greater is required
```

**Solution:**
1. Install Visual C++ Build Tools
2. Install Windows SDK
3. Retry installation

### Video Processing Issues

#### Video Upload Fails
```
Problem: Video upload times out or fails
```

**Solution:**
1. Check file size limits in settings
2. Verify file format is supported
3. Ensure sufficient disk space
4. Check network connection

#### Slow Processing Speed
```
Problem: Video analysis is taking too long
```

**Solution:**
1. Check GPU utilization
2. Reduce video resolution
3. Adjust batch size in configuration
4. Increase process_every_n_frames value

### Database Issues

#### Migration Errors
```
Problem: Django migration errors
```

**Solution:**
1. Reset migrations:
```bash
python manage.py migrate --fake
python manage.py makemigrations
python manage.py migrate
```

#### Database Locked
```
Problem: SQLite database is locked
```

**Solution:**
1. Close other connections
2. Check file permissions
3. Consider switching to PostgreSQL for production

### WebSocket Connection Issues

#### Connection Refused
```
Problem: WebSocket connection fails
```

**Solution:**
1. Verify Redis is running
2. Check channel layer configuration
3. Ensure correct WebSocket URL
4. Check firewall settings

## Performance Optimization

### Memory Usage

If the system is using too much memory:

1. Adjust batch size:
```python
PROCESSING_CONFIG = {
    'batch_size': 16,  # Reduce from default
}
```

2. Limit concurrent processes:
```python
PROCESSING_CONFIG = {
    'max_concurrent_processes': 2,
}
```

### CPU/GPU Usage

If experiencing high CPU/GPU usage:

1. Adjust processing frequency:
```python
DETECTION_CONFIG = {
    'process_every_n_frames': 2,  # Process every other frame
}
```

2. Lower resolution threshold:
```python
DETECTION_CONFIG = {
    'max_detection_size': 720,  # Reduce from 1024
}
```

## Logging and Debugging

### Enable Debug Logging

```python
# settings.py
LOGGING = {
    'handlers': {
        'file': {
            'level': 'DEBUG',  # Change from INFO
        },
    },
}
```

### Check System Logs

```bash
tail -f vista.log
```

## Common Error Messages

| Error Message | Possible Cause | Solution |
|--------------|----------------|-----------|
| "CUDA out of memory" | GPU memory exhausted | Reduce batch size or video resolution |
| "Connection refused" | Redis not running | Start Redis server |
| "File too large" | Exceeds upload limit | Adjust MAX_UPLOAD_SIZE in settings |
| "Database is locked" | Concurrent access | Implement connection pooling |

## Support Resources

- Check the [GitHub Issues](https://github.com/yourusername/vistav1/issues)
- Join our [Discord Community](https://discord.gg/vistav1)
- Contact support at support@vistav1.com
