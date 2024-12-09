# Deployment Guide

This guide covers the deployment process for Vista v1 in various environments.

## Production Deployment

### Prerequisites

- Linux server (Ubuntu 20.04 LTS recommended)
- Python 3.8+
- PostgreSQL
- Redis
- Nginx
- SSL certificate

### System Setup

1. Update System
```bash
sudo apt update
sudo apt upgrade
```

2. Install Dependencies
```bash
sudo apt install python3-pip python3-venv nginx postgresql redis-server
```

3. Create User
```bash
sudo useradd -m -s /bin/bash vista
sudo usermod -aG sudo vista
```

### Application Setup

1. Clone Repository
```bash
git clone https://github.com/yourusername/vistav1.git
cd vistav1
```

2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Requirements
```bash
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Database Setup

1. Create PostgreSQL Database
```sql
CREATE DATABASE vistav1;
CREATE USER vista_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE vistav1 TO vista_user;
```

2. Configure Environment Variables
```bash
cat << EOF > .env
DEBUG=False
SECRET_KEY=your_secret_key_here
DATABASE_URL=postgres://vista_user:your_password@localhost:5432/vistav1
ALLOWED_HOSTS=your_domain.com
EOF
```

### Gunicorn Setup

1. Create Systemd Service
```bash
sudo nano /etc/systemd/system/vista.service
```

```ini
[Unit]
Description=Vista v1 Application
After=network.target

[Service]
User=vista
Group=www-data
WorkingDirectory=/home/vista/vistav1
Environment="PATH=/home/vista/vistav1/venv/bin"
ExecStart=/home/vista/vistav1/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/vista/vistav1/vista.sock \
    vista.wsgi:application

[Install]
WantedBy=multi-user.target
```

2. Start Service
```bash
sudo systemctl start vista
sudo systemctl enable vista
```

### Nginx Configuration

1. Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/vista
```

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/vista/vistav1;
    }

    location /media/ {
        root /home/vista/vistav1;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/vista/vistav1/vista.sock;
    }

    location /ws/ {
        proxy_pass http://unix:/home/vista/vistav1/vista.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

2. Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/vista /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Setup

1. Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx
```

2. Obtain Certificate
```bash
sudo certbot --nginx -d your_domain.com
```

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose

### Docker Configuration

1. Create Dockerfile
```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "vista.wsgi:application"]
```

2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn vista.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=vistav1
      - POSTGRES_USER=vista_user
      - POSTGRES_PASSWORD=your_password

  redis:
    image: redis:6
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Deploy with Docker

1. Build and Start
```bash
docker-compose up --build -d
```

2. Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

## Monitoring

### Setup Prometheus

1. Install Prometheus
```bash
sudo apt install prometheus
```

2. Configure monitoring
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vista'
    static_configs:
      - targets: ['localhost:8000']
```

### Setup Grafana

1. Install Grafana
```bash
sudo apt install grafana
```

2. Configure dashboards for:
- System metrics
- Application performance
- Video processing stats

## Backup Strategy

1. Database Backup
```bash
pg_dump vistav1 > backup.sql
```

2. Media Files Backup
```bash
rsync -av /home/vista/vistav1/media/ /backup/media/
```

3. Automated Backup Script
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup"

# Database backup
pg_dump vistav1 > $BACKUP_DIR/db_$DATE.sql

# Media backup
rsync -av /home/vista/vistav1/media/ $BACKUP_DIR/media_$DATE/

# Cleanup old backups
find $BACKUP_DIR -name "db_*" -mtime +7 -delete
find $BACKUP_DIR -name "media_*" -mtime +7 -delete
```
