# AI Workflow Generator - Docker Deployment

This directory contains Docker configuration for running the AI Workflow Generator service.

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available

### 2. Setup

```bash
# Navigate to deploy directory
cd deploy/docker

# Copy environment template
cp .env.example.ai-workflow .env.ai-workflow

# Edit .env.ai-workflow with your configuration
# - Set FASTGPT_API_URL to your FastGPT instance
# - Set FASTGPT_API_KEY for LLM calls

# Start services
docker-compose -f docker-compose.ai-workflow-generator.yml up -d
```

### 3. Verify

```bash
# Check service status
docker-compose -f docker-compose.ai-workflow-generator.yml ps

# Check logs
docker-compose -f docker-compose.ai-workflow-generator.yml logs -f ai-workflow-agent

# Test health endpoint
curl http://localhost:8000/health
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| ai-workflow-agent | 8000 | Python FastAPI agent service |
| mongo-aiworkflow | 27018 | MongoDB for session storage |
| redis-aiworkflow | 6380 | Redis for caching/queue |
| minio-aiworkflow | 9000/9001 | MinIO for file storage |

## Environment Variables

See `.env.example.ai-workflow` for all configuration options.

### Required

- `FASTGPT_API_URL` - Your FastGPT instance URL
- `FASTGPT_API_KEY` - FastGPT API key for LLM calls

### Optional

- `MONGODB_URI` - MongoDB connection (defaults to container)
- `REDIS_URL` - Redis connection (defaults to container)
- `MINIO_ENDPOINT` - MinIO endpoint (defaults to container)

## Integration with Existing FastGPT

To connect to an existing FastGPT installation instead of starting new databases:

1. Edit `docker-compose.ai-workflow-generator.yml`
2. Comment out the `mongo-aiworkflow`, `redis-aiworkflow`, and `minio-aiworkflow` services
3. Update `.env.ai-workflow`:
   - Set `MONGODB_URI` to your existing MongoDB
   - Set `REDIS_URL` to your existing Redis

## Development

For local development with hot-reload:

```bash
# Start with volume mount for live code reloading
docker-compose -f docker-compose.ai-workflow-generator.yml up -d

# View logs
docker-compose -f docker-compose.ai-workflow-generator.yml logs -f
```

## Building the Docker Image

```bash
# Build the Python agent image
cd ../projects/opencode-agent
docker build -t fastgpt-ai-workflow-agent:latest .

# Or build with docker-compose
docker-compose -f ../deploy/docker/docker-compose.ai-workflow-generator.yml build
```

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose -f docker-compose.ai-workflow-generator.yml logs

# Check health status
docker inspect fastgpt-ai-workflow-agent | grep -A 20 Health
```

### Cannot connect to FastGPT

```bash
# Verify network connectivity
docker exec -it fastgpt-ai-workflow-agent curl http://host.docker.internal:3000/health

# Check FASTGPT_API_URL in .env.ai-workflow
```

### Database connection issues

```bash
# Check MongoDB is running
docker-compose -f docker-compose.ai-workflow-generator.yml ps mongo-aiworkflow

# Check MongoDB logs
docker-compose -f docker-compose.ai-workflow-generator.yml logs mongo-aiworkflow

# Verify connection string
docker exec -it fastgpt-ai-workflow-agent sh -c 'echo $MONGODB_URI'
```

## Stopping

```bash
# Stop all services
docker-compose -f docker-compose.ai-workflow-generator.yml down

# Stop and remove volumes (warning: deletes data)
docker-compose -f docker-compose.ai-workflow-generator.yml down -v
```

## Production Considerations

For production deployment:

1. Change default passwords in `.env.ai-workflow`
2. Use production-grade MongoDB (not the containerized one)
3. Enable TLS/SSL for all connections
4. Set `APP_ENV=production`
5. Set `LOG_LEVEL=info` or `LOG_LEVEL=warning`
6. Configure proper health check intervals
7. Set up monitoring and alerting

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│                   (ai-workflow-network)                      │
│                                                              │
│  ┌──────────────────┐   ┌──────────────────┐             │
│  │ ai-workflow-agent │   │  mongo-aiworkflow │             │
│  │    (Python)       │◄──►│    (MongoDB)      │             │
│  │   Port: 8000      │   │   Port: 27017     │             │
│  └──────────────────┘   └──────────────────┘             │
│           │                      │                       │
│           ▼                      ▼                       │
│  ┌──────────────────┐   ┌──────────────────┐             │
│  │  redis-aiworkflow │   │ minio-aiworkflow  │             │
│  │   Port: 6379      │   │  Ports: 9000/9001 │             │
│  └──────────────────┘   └──────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│              External FastGPT Instance                       │
│                  (user-provided)                            │
└─────────────────────────────────────────────────────────────┘
```
