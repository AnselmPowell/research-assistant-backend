# ResearchNotes Backend - Production Deployment Guide

This document provides instructions for deploying the ResearchNotes backend to production.

## Prerequisites

- Docker and Docker Compose installed
- A Neon PostgreSQL database instance
- An OpenAI API key
- A Redis instance (for Channels)

## Production Deployment Steps

### 1. Environment Configuration

1. Create a `.env.production` file based on the example:

```bash
cp .env.production.example .env.production
```

2. Update the values in `.env.production`:
   - Generate a strong `DJANGO_SECRET_KEY`
   - Add your PostgreSQL connection string to `DATABASE_URL`
   - Set your `OPENAI_API_KEY`
   - Add your Redis URL
   - Update domain names in settings.py (`ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`)

### 2. Build and Test the Docker Image

```bash
# Build the Docker image
docker-compose build

# Run the container locally for testing
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 3. Deploy to Production

#### Option 1: Docker-based Deployment

1. Push your Docker image to a container registry:

```bash
docker build -t your-registry/researchnotes-backend:latest .
docker push your-registry/researchnotes-backend:latest
```

2. Deploy to your hosting platform using the Docker image.

#### Option 2: Platform-specific Deployment

Follow the deployment instructions for your chosen platform:

- **Render**: Connect your GitHub repository and use the Dockerfile
- **DigitalOcean App Platform**: Connect your repository and configure environment variables
- **AWS/GCP/Azure**: Use container services like ECS, Cloud Run, or ACI

### 4. Database Management

The application will automatically apply migrations during startup, but you may need to create a superuser manually:

```bash
# Connect to the running container
docker exec -it <container_name> bash

# Create a superuser
python manage.py createsuperuser
```

### 5. Monitoring and Maintenance

- Set up logging to a service like Papertrail or Datadog
- Configure monitoring for your Docker containers
- Set up database backups for your Neon PostgreSQL instance

## Security Considerations

- The application uses secure cookies in production
- CORS is restricted to only your frontend domain
- Rate limiting is enabled for API endpoints
- HTTPS redirection is enforced
- Proper HTTP security headers are set

## Troubleshooting

- Check Docker container logs: `docker logs <container_name>`
- Verify environment variables are correctly set
- Ensure Neon PostgreSQL and Redis are accessible from your deployment environment
- Check Django error logs for more detailed information
