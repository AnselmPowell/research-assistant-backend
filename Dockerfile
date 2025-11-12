###############################################
# Python 3.10 base image
###############################################
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=research_assistant.settings

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies - include all production dependencies
COPY requirements.txt requirements.production.txt* ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ -f requirements.production.txt ]; then pip install --no-cache-dir -r requirements.production.txt; fi

# Copy project files
COPY . .

# Create a non-root user and switch to it
RUN useradd -m djangouser
RUN chown -R djangouser:djangouser /app
USER djangouser

# Run collectstatic (adjust the settings as needed)
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Create the entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Start Daphne ASGI server (for WebSocket support)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "research_assistant.asgi:application"]
