# Technical Context: AI Academic Research Assistant Backend

## Technologies Used

The AI Academic Research Assistant backend leverages a modern Python-based stack centered on Django and related technologies:

### Core Technologies

1. **Django Framework** (v4.2.11)
   - REST Framework for API endpoints
   - Django Channels for WebSockets
   - ORM for database interactions
   - Models for data structure

2. **Python** (v3.13)
   - concurrent.futures for parallel processing
   - Threading for background tasks
   - Type hints for code clarity
   - Exception handling for robustness

3. **AI Services**
   - Pydantic-AI for LLM interactions
   - OpenAI API (GPT-4o) for information extraction
   - Text embedding API for semantic search
   - Structured output for reliable data extraction

4. **PDF Processing**
   - PyMuPDF (v1.23.8) for PDF handling
   - Text extraction with page context
   - Metadata parsing and enhancement
   - Large document optimization

5. **Search Integration**
   - arXiv API for academic paper discovery
   - Query optimization with AI
   - Custom search patterns for relevance
   - Direct URL support

6. **Database**
   - Neon PostgreSQL (serverless)
   - Connection pooling
   - SSL security
   - JSON field support
   - Strategic indexing

7. **Real-time Communication**
   - Django Channels (WebSockets)
   - ASGI configuration
   - Group-based messaging
   - Status and result updates

## Database Configuration

The system uses Neon PostgreSQL, a serverless Postgres service:

```python
# Database Configuration using dj-database-url
DATABASES = {
    'default': dj_database_url.config(
        default=database_url,
        conn_max_age=600,      # Connection lifetime
        conn_health_checks=True, # Health checks
        ssl_require=True       # SSL for security
    )
}

# SSL Configuration
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}

# Production Settings
if IS_PRODUCTION:
    DATABASES['default']['CONN_MAX_AGE'] = 0  # Fresh connections
    DATABASES['default']['OPTIONS']['connect_timeout'] = 30
```

### Connection Management

The system implements robust connection handling with retry logic:

```python
class DatabaseConnectionMiddleware:
    """Middleware to ensure database connection."""
    
    def __call__(self, request):
        try:
            connection.ensure_connection()
        except OperationalError:
            # Reconnection logic with exponential backoff
            if not ensure_connection():
                return JsonResponse({
                    "error": "Database connection error",
                }, status=503)
        return self.get_response(request)

def ensure_connection(max_attempts=3):
    """Ensure database connection with retry logic."""
    for attempt in range(max_attempts):
        try:
            connection.connect()
            return True
        except OperationalError:
            if attempt < max_attempts - 1:
                # Exponential backoff
                time.sleep(2 ** attempt)
            else:
                return False
```

### Model Optimization

Models are optimized with strategic indexes for performance:

```python
class Note(models.Model):
    # Fields...
    
    class Meta:
        indexes = [
            models.Index(fields=['paper']),
            models.Index(fields=['note_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class Project(models.Model):
    # Fields...
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
        ]

class Section(models.Model):
    # Fields...
    
    class Meta:
        indexes = [
            models.Index(fields=['project']),
        ]

class Group(models.Model):
    # Fields...
    
    class Meta:
        indexes = [
            models.Index(fields=['section']),
            models.Index(fields=['project']),
        ]
```

## Key Implementation Patterns

### 1. Pydantic-AI Integration

The system uses Pydantic-AI for structured LLM interactions:

```python
class LLM:
    """Class for interacting with LLMs using Pydantic-AI."""
    
    def __init__(self, model: str = None, max_retries: int = 3):
        """Initialize the LLM class."""
        self.model = model or os.environ.get("DEFAULT_MODEL", 'openai:gpt-4o-mini')
        self.max_retries = max_retries
        
        # Create the Pydantic-AI agent
        self.agent = Agent(self.model)
    
    async def call(self, prompt: str, system_prompt: str = None, attempt: int = 0) -> str:
        """Call the LLM with the given prompt."""
        try:
            # Prepare the prompt with system prompt if provided
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            # Call the agent
            result = await self.agent.run(full_prompt)
            
            # Access the output attribute
            output = result.output
            
            # Handle markdown code blocks
            if isinstance(output, str) and output.startswith("```") and "```" in output:
                content_start = output.find("\n") + 1
                content_end = output.rfind("```")
                if content_start > 0 and content_end > content_start:
                    output = output[content_start:content_end].strip()
            
            return output
        
        except Exception as e:
            if attempt < self.max_retries:
                # Retry with exponential backoff
                await asyncio.sleep(2 ** attempt)
                return await self.call(prompt, system_prompt, attempt + 1)
            else:
                return f"Error after {self.max_retries} attempts: {str(e)}"
```

### 2. Embedding Service for Semantic Search

```python
def get_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text."""
    if not text or not text.strip():
        return [0.0] * 1536  # Default dimension for embeddings
    
    try:
        # Initialize OpenAI client
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        client = OpenAI(api_key=api_key)
        
        # Call the API
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        
        # Return the embedding
        return response.data[0].embedding
    
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return zero vector as fallback
        return [0.0] * 1536

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    try:
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return similarity
    
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0
```

### 3. Enhanced Metadata Extraction

```python
def extract_enhanced_metadata_with_llm(doc, max_pages=3):
    """Extract enhanced metadata from the first few pages using LLM."""
    # Extract text from first few pages
    page_count = min(max_pages, len(doc))
    first_pages_text = ""
    
    for i in range(page_count):
        page_text = doc[i].get_text()
        first_pages_text += f"[PAGE {i+1}]\n{page_text}\n[END PAGE {i+1}]\n"
    
    # Define schema for structured extraction
    output_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "authors": {"type": "array", "items": {"type": "string"}},
            "year": {"type": ["string", "number", "null"]},
            "summary": {"type": "string"}
        }
    }
    
    # Extract structured data with LLM
    result = llm.structured_output(first_pages_text, output_schema, system_prompt)
    
    # Format Harvard reference
    harvard_ref = create_harvard_reference(result)
    
    return {
        'title': result.get('title', ''),
        'authors': result.get('authors', []),
        'year': result.get('year', ''),
        'summary': result.get('summary', ''),
        'harvard_reference': harvard_ref,
        'total_pages': len(doc)
    }
```

### 4. WebSocket Communication

```python
class ResearchConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for research sessions."""
    
    async def connect(self):
        """Handle connection to the WebSocket."""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"research_{self.session_id}"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Check if session exists and send initial status
        session = await self.get_session()
        if session:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'data': {
                    'stage': session['status'],
                    'message': f"Connected to session {self.session_id}"
                }
            }))

    async def status_message(self, event):
        """Send status message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': event['data']
        }))
    
    async def result_message(self, event):
        """Send result message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'result',
            'data': event['data']
        }))
```

### 5. Thread-Safe Database Operations

```python
def _process_paper_thread_safe(paper_id, search_terms, query_embedding, info_queries, explanation):
    """Thread-safe version of process_paper_thread."""
    # Close old connections to ensure thread safety with Django's DB connections
    close_old_connections()
    
    try:
        # Get paper
        paper = Paper.objects.get(id=paper_id)
        
        # Update status
        paper.status = 'processing'
        paper.save()
        
        # Process the PDF
        result = process_pdf(paper.url, search_terms, query_embedding, info_queries, explanation)
        
        # Update paper with results
        with transaction.atomic():
            paper.title = result.get('title', 'Unknown')
            paper.authors = result.get('authors', [])
            paper.year = result.get('year', '')
            paper.summary = result.get('summary', '')
            paper.harvard_reference = result.get('harvard_reference', '')
            paper.total_pages = result.get('total_pages', 0)
            paper.status = result.get('status', 'error')
            paper.error_message = result.get('error_message', '')
            paper.save()
            
            # Create Note objects for each extracted note
            if result.get('status') == 'success' and result.get('notes'):
                for note_data in result.get('notes', []):
                    Note.objects.create(
                        paper=paper,
                        content=note_data.get('content', ''),
                        page_number=note_data.get('page_number', 1),
                        note_type=note_data.get('note_type', 'quote'),
                        search_criteria=note_data.get('search_criteria', ''),
                        matches_topic=note_data.get('matches_topic', ''),
                        justification=note_data.get('justification', ''),
                        inline_citations=note_data.get('inline_citations', []),
                        reference_list=note_data.get('reference_list', {})
                    )
        
        # Send real-time update to frontend via WebSocket
        paper_data = {
            'paper_id': str(paper.id),
            'title': paper.title,
            'authors': paper.authors,
            'year': paper.year,
            'summary': paper.summary,
            'harvard_reference': paper.harvard_reference,
            'total_pages': paper.total_pages,
            'status': paper.status,
            'notes_count': paper.notes.count(),
            'notes': [note.to_frontend_format() for note in paper.notes.all()]
        }
        
        # Send update to frontend
        send_paper_update(str(paper.session.id), paper_data)
        
        return {
            "paper_id": paper_id,
            "status": result.get('status', 'error'),
            "paper_data": paper_data
        }
    
    except Exception as e:
        logger.error(f"Error processing paper {paper_id}: {e}")
        try:
            paper = Paper.objects.get(id=paper_id)
            paper.status = 'error'
            paper.error_message = str(e)
            paper.save()
            return {"paper_id": paper_id, "status": "error", "error": str(e)}
        except:
            return {"paper_id": paper_id, "status": "error", "error": "Unknown error"}
```

## Technical Constraints

### Current Constraints

1. **AI Provider Limitations**
   - OpenAI API dependency with rate limits
   - API costs increase with usage volume
   - Multiple LLM calls per paper increase costs
   - Limited testing with non-OpenAI providers

2. **PDF Processing Limitations**
   - Complex layouts may not parse correctly
   - Tables and figures are not extracted
   - First 3 pages may not contain all metadata
   - Large documents require chunking

3. **arXiv API Limitations**
   - Limited to arXiv as the main source
   - Subject to rate limiting
   - No access to papers behind paywalls
   - Depends on quality of initial queries

4. **Threading Limitations**
   - No persistent queuing if server restarts
   - No recovery for interrupted sessions
   - Thread management overhead for large batches
   - Need for thread safety with database operations

5. **WebSocket Production Readiness**
   - ASGI server selection needed for production
   - Connection pooling optimization required
   - Performance under load needs evaluation
   - Reconnection handling for network issues

6. **Database Scaling Considerations**
   - Connection limits with Neon PostgreSQL
   - Query optimization for high volume
   - Backup and recovery procedures needed
   - Connection pooling configuration for production

## Dependencies

### Core Dependencies

```
django==4.2.11
djangorestframework==3.14.0
pydantic==2.6.1
openai==1.12.0
pydantic-ai==1.0.0
pymupdf==1.23.8
requests==2.31.0
python-dotenv==1.0.0
arxiv==2.0.0
numpy==1.26.3
drf-yasg==1.21.7
psycopg2-binary==2.9.9
dj-database-url==2.1.0
```

### WebSocket Dependencies

```
channels==4.0.0
channels-redis==4.1.0
```

### Additional Dependencies

```
tenacity==8.2.3  # For retry logic
concurrent.futures  # Built-in for parallel processing
```

## Running in Production

For production deployment, consider:

1. **ASGI Server Selection**
   - Use Daphne, Uvicorn, or Hypercorn
   - Configure proper worker processes
   - Set appropriate timeouts
   - Ensure WebSocket compatibility

2. **Database Configuration**
   - Optimize connection pooling settings
   - Configure proper timeouts
   - Implement health checks
   - Set up connection retry logic

3. **Environment Variables**
   - Configure through .env file
   - Set DEBUG=False in production
   - Secure API keys and credentials
   - Configure proper logging levels

4. **Error Handling and Logging**
   - Configure comprehensive logging
   - Set up error monitoring
   - Implement proper error responses
   - Add detailed context to error logs