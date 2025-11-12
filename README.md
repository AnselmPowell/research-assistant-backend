# Research Assistant Backend

This is the Django backend for the Research Assistant application.

## Overview

The Research Assistant backend is built with Django and provides the following features:

- Real-time PDF processing with arXiv search
- LLM-powered information extraction
- WebSocket-based real-time updates
- Background task processing with Celery

## Setup

### Prerequisites

- Python 3.8+
- Redis (for Celery and Django Channels)
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>/backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the environment variables with your API keys and settings

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

### Running the Server

1. Start Redis:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A research_assistant worker -l info
```

3. Run the development server:
```bash
python manage.py runserver
```

4. Access the admin at http://localhost:8000/admin/

## API Endpoints

- `POST /api/research/start/`: Start a new research session
- `GET /api/research/session/<session_id>/`: Get session details
- `GET /api/research/session/<session_id>/notes/`: Get all notes for a session

## WebSocket

Connect to `ws://localhost:8000/ws/research/<session_id>/` to receive real-time updates.

## Architecture

The application follows a three-tier architecture:

1. **Web Layer**: Django views and WebSocket consumers
2. **Service Layer**: LLM service, PDF processing, arXiv search
3. **Data Layer**: Django models and database

Tasks are processed asynchronously using Celery to handle time-consuming operations like PDF processing and LLM extraction.
