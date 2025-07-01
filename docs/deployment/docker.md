---
title: Docker Deployment
description: Containerized deployment of LarryBot2 using Docker and Docker Compose
last_updated: 2025-06-28
---

# Docker Deployment 🐳

This guide explains how to deploy LarryBot2 using Docker and Docker Compose.

## 🐋 Dockerfile Example
Create a `Dockerfile` in your project root:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "larrybot"]
```

## 🛠️ Build and Run the Container
```bash
docker build -t larrybot2 .
docker run --env-file .env -v $(pwd)/larrybot.db:/app/larrybot.db larrybot2
```

## 🧩 Docker Compose Example
Create a `docker-compose.yml` for multi-service orchestration:

```yaml
version: '3.8'
services:
  larrybot:
    build: .
    env_file: .env
    volumes:
      - ./larrybot.db:/app/larrybot.db
    restart: unless-stopped
```

## 🔐 Environment Configuration
- Use `.env` for secrets and configuration
- Never hardcode secrets in Dockerfile or compose files

## 🛠️ Best Practices
- Use multi-stage builds for smaller images
- Mount volumes for persistent data
- Set resource limits in production
- Use healthchecks in `docker-compose.yml`

## 🚨 Troubleshooting
- **Build errors**: Check Dockerfile syntax and requirements
- **Database not persisting**: Ensure volume is mounted
- **Environment not loaded**: Use `env_file` or `-e` flags

---

**Related Guides**: [Deployment Guide](deployment.md) | [Monitoring](monitoring.md) 