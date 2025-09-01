# Deployment Guide

This guide covers deploying the Chinese Flashcard Application in various environments, from local development to production cloud deployments.

## Table of Contents

1. [Local Development](#local-development)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Platforms](#cloud-platforms)
5. [Configuration](#configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (for version control)
- 2GB RAM minimum
- 1GB free disk space

### Quick Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/chinese-flashcard-app.git
   cd chinese-flashcard-app
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

5. **Access the application**:
   Open `http://localhost:8501` in your browser

### Development Configuration

Create a `.env` file for local development:
```env
# Development settings
DEBUG=true
LOG_LEVEL=debug
CACHE_TTL=300
MAX_CARDS_PER_SESSION=1000

# Optional: Custom ports
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

### Hot Reloading

Streamlit automatically reloads when files change. For faster development:
```bash
streamlit run app.py --server.runOnSave true
```

## Production Deployment

### System Requirements

#### Minimum Requirements
- 2 CPU cores
- 4GB RAM
- 10GB disk space
- Python 3.8+
- Linux/Windows Server

#### Recommended Requirements
- 4 CPU cores
- 8GB RAM
- 50GB SSD storage
- Load balancer (for high availability)
- Reverse proxy (nginx/Apache)

### Production Setup

1. **Prepare the server**:
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and dependencies
   sudo apt install python3.8 python3-pip python3-venv nginx -y
   ```

2. **Create application user**:
   ```bash
   sudo useradd -m -s /bin/bash flashcard
   sudo su - flashcard
   ```

3. **Deploy application**:
   ```bash
   git clone https://github.com/your-org/chinese-flashcard-app.git
   cd chinese-flashcard-app
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env.production
   # Edit .env.production with production settings
   ```

5. **Create systemd service**:
   ```bash
   sudo nano /etc/systemd/system/flashcard.service
   ```

   ```ini
   [Unit]
   Description=Chinese Flashcard Application
   After=network.target

   [Service]
   Type=simple
   User=flashcard
   WorkingDirectory=/home/flashcard/chinese-flashcard-app
   Environment=PATH=/home/flashcard/chinese-flashcard-app/venv/bin
   ExecStart=/home/flashcard/chinese-flashcard-app/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

6. **Start and enable service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable flashcard
   sudo systemctl start flashcard
   ```

### Reverse Proxy Configuration

#### Nginx Configuration

Create `/etc/nginx/sites-available/flashcard`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/flashcard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL/TLS Configuration

Use Let's Encrypt for free SSL certificates:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Docker Deployment

### Dockerfile

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 flashcard && chown -R flashcard:flashcard /app
USER flashcard

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  flashcard-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - PYTHONPATH=/app
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - flashcard-app
    restart: unless-stopped
```

### Build and Deploy

```bash
# Build the image
docker build -t flashcard-app .

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f flashcard-app

# Scale the application
docker-compose up -d --scale flashcard-app=3
```

## Cloud Platforms

### AWS Deployment

#### Using AWS App Runner

1. **Create apprunner.yaml**:
   ```yaml
   version: 1.0
   runtime: python3
   build:
     commands:
       build:
         - pip install -r requirements.txt
   run:
     runtime-version: 3.9
     command: streamlit run app.py --server.port 8080 --server.address 0.0.0.0
     network:
       port: 8080
       env: PORT
   ```

2. **Deploy via AWS Console**:
   - Go to AWS App Runner
   - Create service from source code
   - Connect GitHub repository
   - Configure build settings

#### Using ECS with Fargate

1. **Create task definition**:
   ```json
   {
     "family": "flashcard-app",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "flashcard-app",
         "image": "your-account.dkr.ecr.region.amazonaws.com/flashcard-app:latest",
         "portMappings": [
           {
             "containerPort": 8501,
             "protocol": "tcp"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/flashcard-app",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

### Google Cloud Platform

#### Using Cloud Run

1. **Deploy with gcloud**:
   ```bash
   gcloud run deploy flashcard-app \
     --image gcr.io/PROJECT-ID/flashcard-app \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8501 \
     --memory 1Gi \
     --cpu 1
   ```

2. **Configure custom domain**:
   ```bash
   gcloud run domain-mappings create \
     --service flashcard-app \
     --domain your-domain.com \
     --region us-central1
   ```

### Heroku Deployment

1. **Create Procfile**:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. **Deploy to Heroku**:
   ```bash
   heroku create your-app-name
   git push heroku main
   heroku ps:scale web=1
   ```

## Configuration

### Environment Variables

#### Production Configuration
```env
# Application settings
DEBUG=false
LOG_LEVEL=info
SECRET_KEY=your-secret-key-here

# Performance settings
CACHE_TTL=3600
MAX_CARDS_PER_SESSION=5000
WORKER_PROCESSES=4

# Security settings
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true

# External services
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

#### Streamlit Configuration

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### Logging Configuration

Create `logging.conf`:
```ini
[loggers]
keys=root,streamlit,app

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter,detailedFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_streamlit]
level=WARNING
handlers=consoleHandler
qualname=streamlit
propagate=0

[logger_app]
level=INFO
handlers=consoleHandler,fileHandler
qualname=app
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=detailedFormatter
args=('app.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

[formatter_detailedFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s
```

## Monitoring and Maintenance

### Health Checks

Implement health check endpoint:
```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app_version
    }
```

### Monitoring Tools

#### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('app_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request latency')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

#### Log Monitoring
```bash
# Monitor application logs
tail -f /var/log/flashcard/app.log

# Monitor system resources
htop
iostat -x 1
```

### Backup Strategy

#### Database Backups
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump flashcard_db > /backups/flashcard_db_$DATE.sql
find /backups -name "flashcard_db_*.sql" -mtime +7 -delete
```

#### Application Data
```bash
# Backup user data
tar -czf /backups/user_data_$DATE.tar.gz /app/data/
```

### Updates and Maintenance

#### Rolling Updates
```bash
# Zero-downtime deployment
docker-compose pull
docker-compose up -d --no-deps flashcard-app
```

#### Database Migrations
```bash
# Run migrations
python manage.py migrate
```

## Security Considerations

### Network Security
- Use HTTPS/TLS encryption
- Configure firewall rules
- Implement rate limiting
- Use VPN for admin access

### Application Security
- Regular dependency updates
- Input validation and sanitization
- CSRF protection
- Secure session management

### Infrastructure Security
- Regular OS updates
- Secure SSH configuration
- Monitoring and alerting
- Backup encryption

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check service status
sudo systemctl status flashcard

# Check logs
sudo journalctl -u flashcard -f

# Check port availability
sudo netstat -tlnp | grep 8501
```

#### High Memory Usage
```bash
# Monitor memory usage
free -h
ps aux | grep streamlit

# Restart service if needed
sudo systemctl restart flashcard
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificates
sudo certbot renew --dry-run
```

### Performance Optimization

#### Caching
- Implement Redis for session storage
- Use CDN for static assets
- Enable browser caching

#### Database Optimization
- Index frequently queried columns
- Implement connection pooling
- Regular maintenance tasks

#### Application Tuning
- Optimize Python code
- Use async operations where possible
- Implement lazy loading

Remember to always test deployments in a staging environment before deploying to production!
