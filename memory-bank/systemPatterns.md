# System Patterns: AI Academic Research Assistant Backend

## System Architecture

The AI Academic Research Assistant backend follows a modular service-oriented architecture with a clear separation of concerns. The system is built around Django's request-response cycle for API endpoints, with WebSockets for real-time updates and background processing for research tasks.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Django Framework                     │
├─────────────┬─────────────────────┬─────────────────────┤
│  REST API   │   WebSockets        │    Background       │
│  Endpoints  │   (Channels)        │    Processing       │
└─────────────┴─────────────────────┴─────────────────────┘
        │               │                    │
        v               v                    v
┌─────────────┬─────────────────────┬─────────────────────┐
│  Session    │    Document         │     AI              │
│  Management │    Processing       │     Services        │
└─────────────┴─────────────────────┴─────────────────────┘
        │               │                    │
        └───────────────┼────────────────────┘
                        v
                ┌──────────────────┐
                │     Database     │
                └──────────────────┘
```

### Data Flow

1. Frontend submits research request via REST API
2. Backend creates research session and begins processing
3. WebSocket connection established for real-time updates
4. Background processing handles paper discovery and analysis
5. LLM extracts content with justifications for relevance
6. Results are stored in database with organization structure
7. Notes with organization and context are sent to frontend
8. Real-time updates provided throughout the process

## Key Technical Patterns

### 1. Service-Based Structure

The application uses a service-based pattern with specialized modules:

```python
# Service-based organization
core/
  services/
    llm_service.py      # OpenAI/Pydantic-AI integration
    embedding_service.py # Vector embeddings for semantic search
    pdf_service.py      # PDF downloading and processing
    search_service.py   # arXiv search and query enhancement
```

This structure:
- Isolates external dependencies
- Simplifies testing and mocking
- Provides clear separation of concerns
- Enables modular development

### 2. Thread Pool Pattern for Parallel Processing

The system uses thread pools for concurrent paper processing:

```python
def _process_research_session_thread(session_id: str):
    # Get maximum workers from settings
    max_workers = getattr(settings, 'MAX_WORKERS', 4)
    
    # Process papers in parallel using a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all papers to the thread pool
        future_to_paper = {
            executor.submit(
                _process_paper_thread_safe, 
                str(paper.id), 
                search_terms,
                query_embedding, 
                session.info_queries,
                explanation
            ): paper for paper in papers
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_paper):
            paper = future_to_paper[future]
            try:
                result = future.result()
                # Handle result, e.g., send update via WebSocket
            except Exception as e:
                logger.error(f"Error processing paper: {e}")
```

This pattern:
- Processes multiple papers simultaneously
- Provides resource-efficient concurrency
- Handles results as they become available
- Ensures thread-safe database operations

### 3. Two-Path Document Processing Strategy

The system implements distinct processing paths based on document size:

```python
def process_pdf(pdf_path, queries, query_embedding):
    # Load the PDF
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    
    # Extract enhanced metadata
    metadata = extract_enhanced_metadata_with_llm(doc)
    
    # Choose processing strategy based on size
    if page_count <= SMALL_DOC_THRESHOLD:
        # Simple path - process entire document
        all_text = extract_full_document_text(doc)
        extracted_items = extract_information_from_text(all_text, queries)
    else:
        # Advanced path - use embeddings to find relevant sections
        extracted_items = process_large_document(doc, queries, query_embedding)
    
    # Validate relevance of extracted items
    validated_items = validate_item_relevance(extracted_items, query_embedding)
```

This strategy pattern:
- Optimizes processing based on document characteristics
- Reduces API costs for large documents
- Focuses analysis on most relevant content
- Balances thoroughness with performance

### 4. Observer Pattern with WebSockets

The system implements the observer pattern for real-time updates:

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
    
    async def disconnect(self, close_code):
        """Handle disconnection from the WebSocket."""
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
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

WebSocket sender functions:
```python
def send_status_update(session_id: str, status: str, message: str = None):
    """Send session status update via WebSocket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"research_{session_id}",
        {
            'type': 'status_message',
            'data': {
                'stage': status,
                'message': message or f"Session status: {status}"
            }
        }
    )

def send_paper_update(session_id: str, paper_data: Dict[str, Any]):
    """Send paper update via WebSocket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"research_{session_id}",
        {
            'type': 'result_message',
            'data': paper_data
        }
    )
```

This pattern:
- Decouples producers from consumers
- Supports multiple clients per session
- Enables real-time updates
- Organizes clients by session ID
- Provides typed messages for different updates

### 5. Structured LLM Integration with Pydantic-AI

```python
class LLM:
    """Class for interacting with LLMs using Pydantic-AI."""
    
    def __init__(self, model: str = None, max_retries: int = 3):
        """Initialize the LLM class."""
        self.model = model or os.environ.get("DEFAULT_MODEL", 'openai:gpt-4o-mini')
        self.max_retries = max_retries
        
        # Create the Pydantic-AI agent
        self.agent = Agent(self.model)
    
    def structured_output(self, prompt: str, output_schema: dict, system_prompt: str = None) -> Dict[str, Any]:
        """Get structured output from the LLM."""
        try:
            # Create a system prompt with schema instructions
            schema_instructions = f"Your response must be a valid JSON object following this schema: {json.dumps(output_schema)}"
            
            if system_prompt:
                full_system_prompt = f"{system_prompt}\n\n{schema_instructions}"
            else:
                full_system_prompt = schema_instructions
            
            # Create a combined prompt
            full_prompt = f"{full_system_prompt}\n\n{prompt}"
            
            # Call the agent synchronously to get JSON response
            result = asyncio.run(self.agent.run(full_prompt))
            
            # Extract the content from the output attribute
            output = result.output
            
            # Check if response is wrapped in markdown code blocks
            if isinstance(output, str) and output.startswith("```") and "```" in output:
                # Extract content between code blocks
                content_start = output.find("\n") + 1
                content_end = output.rfind("```")
                if content_start > 0 and content_end > content_start:
                    output = output[content_start:content_end].strip()
            
            # Try to parse as JSON if it's a string
            if isinstance(output, str):
                parsed_json = json.loads(output)
                return parsed_json
            elif isinstance(output, dict):
                # If it's already a dict, return it directly
                return output
```

This pattern:
- Encapsulates LLM interaction details
- Ensures structured outputs with schema validation
- Provides error handling and retries
- Simplifies integration with business logic

### 6. Hierarchical Data Model

The system implements a hierarchical data model for both research content and organization:

```
ResearchSession
    └── Paper 1
        └── Note 1.1 ──┬── Project 1
        │              └── Section 1
        └── Note 1.2 ──┬── Project 1
                       └── Group 2
    └── Paper 2
        └── Note 2.1 ──┬── Project 2
                       └── Section 2
                           └── Group 3
```

Database schema:

```python
class ResearchSession(models.Model):
    """A research session initiated by a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    topics = models.JSONField(default=list)
    info_queries = models.JSONField(default=list)
    direct_urls = models.JSONField(default=list)
    status = models.CharField(max_length=50, choices=[...])

class Paper(models.Model):
    """A paper processed during a research session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE)
    url = models.URLField()
    title = models.CharField(max_length=500, blank=True)
    authors = models.JSONField(default=list)
    # Other fields...

class Note(models.Model):
    """A research note extracted from a paper."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    content = models.TextField()
    page_number = models.IntegerField(default=1)
    # Other fields...
    
    # Organization fields (many-to-many relationships)
    projects = models.ManyToManyField('Project', related_name='notes')
    sections = models.ManyToManyField('Section', related_name='notes')
    groups = models.ManyToManyField('Group', related_name='notes')

class Project(models.Model):
    """User-created project for organizing research notes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Other fields...

class Section(models.Model):
    """Section within a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey(Project, related_name='sections')
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    # Other fields...

class Group(models.Model):
    """Group within a section or directly in a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    section = models.ForeignKey(Section, related_name='groups', null=True)
    project = models.ForeignKey(Project, related_name='project_groups')
    order = models.IntegerField(default=0)
    # Other fields...
```

This model:
- Maintains clear data provenance from session to paper to note
- Supports flexible organization with many-to-many relationships
- Enables hierarchical navigation through related objects
- Allows notes to appear in multiple projects, sections, and groups

## Critical Implementation Paths

### 1. Research Initiation Flow

```
Frontend Request → StartResearchView → process_research_session() 
  → Thread creation → Search term generation
  → arXiv search → Paper object creation
  → ThreadPoolExecutor → Parallel paper processing
```

### 2. Paper Processing Flow

```
_process_paper_thread_safe()
  → PDF download → Two-path processing
  → (Small document) → Full document processing
  → (Large document) → Embedding-based relevance detection 
  → LLM extraction → Note creation → Justification generation
  → WebSocket notification → Frontend display
```

### 3. Note Organization Flow

```
NoteOrganizationView → Update many-to-many relationships
  → Project/Section/Group assignment
  → Database update → Frontend response
```

### 4. Hierarchical Data Retrieval Flow

```
ProjectListCreateView → Project.objects.all()
  → For each project: sections.all() and project_groups.filter()
  → For each section: groups.all()
  → Nested serialization with to_dict()
  → Frontend response
```

## Design Patterns Summary

| Pattern | Implementation | Purpose |
|---------|----------------|---------|
| **Service** | Specialized service modules | Separation of concerns, modular design |
| **Observer** | WebSocket with Channel Layers | Real-time updates to connected clients |
| **Strategy** | Two-path document processing | Optimize based on document characteristics |
| **Thread Pool** | ThreadPoolExecutor | Parallel paper processing with resource control |
| **Repository** | Django ORM | Database abstraction and query optimization |
| **Factory** | Enhanced metadata extraction | Structured creation of complex objects |
| **Decorator** | Database connection middleware | Add connection retry behavior |

This architecture provides a robust foundation for academic research with advanced organization capabilities, efficient parallel processing, and comprehensive bidirectional synchronization with the frontend.