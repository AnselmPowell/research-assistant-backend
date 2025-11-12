# Technical Context: AI Academic Research Assistant Backend (Database Implementation)

This update to the Technical Context document focuses on the Neon PostgreSQL database implementation, which complements the existing technical stack.

## Database Technologies

1. **Neon PostgreSQL**
   - Cloud-based PostgreSQL service with autoscaling capabilities
   - Connection pooling for improved performance
   - SSL-secured connections (sslmode=require)
   - Located in AWS Europe West 2 (London) region
   - PostgreSQL version 17

2. **Database Connectivity**
   - psycopg2-binary (v2.9.9) for PostgreSQL connectivity
   - dj-database-url (v2.1.0) for connection string parsing
   - Connection pooling with pooler endpoint

3. **Database Optimization**
   - Strategic indexes on frequently queried fields
   - JSON field optimizations for PostgreSQL
   - Connection retry logic with exponential backoff
   - Thread-safe database operations

## Database Configuration

### Connection Settings

The application uses environment-based configuration for database connections:

```python
# Database Configuration
# Get database URL from environment
database_url = os.environ.get('DATABASE_URL')

# Configure database with dj-database-url
if database_url:
    # Using Neon PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,  # connection lifetime in seconds
            conn_health_checks=True,  # enable connection health checks
            ssl_require=True  # require SSL for Neon connection
        )
    }
    
    # Add SSL configuration for Neon
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
    }
    
    # Additional settings based on environment
    if IS_PRODUCTION:
        # In production, close connections after each request to prevent connection limits
        DATABASES['default']['CONN_MAX_AGE'] = 0
        # Increase timeout for potentially longer operations
        DATABASES['default']['OPTIONS']['connect_timeout'] = 30
    else:
        # For development, log the database URL (but mask credentials)
        masked_url = database_url.replace(database_url.split('@')[0], '******')
        print(f"Using database: {masked_url}")
else:
    # Fallback to SQLite if no database URL is provided
    print("WARNING: No DATABASE_URL found. Using SQLite as fallback.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

### Environment Variables

The database connection is configured using these environment variables:

```
# Database Configuration
DATABASE_URL=postgresql://neondb_owner:npg_pyPOVSRQH1d8@ep-bitter-violet-abc259vp-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Environment settings
IS_PRODUCTION=false
```

## Database Model Optimization

### Model Indexes

Each model has been optimized with appropriate indexes:

```python
class ResearchSession(models.Model):
    # Fields...
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class Paper(models.Model):
    # Fields...
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class Note(models.Model):
    # Fields...
    
    class Meta:
        ordering = ['page_number', 'created_at']
        indexes = [
            models.Index(fields=['paper']),
            models.Index(fields=['note_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
```

### Database Migrations

A dedicated migration has been created to add indexes to existing tables:

```python
# 0006_add_model_indexes.py
class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_alter_researchsession_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='researchsession',
            index=models.Index(fields=['status'], name='session_status_idx'),
        ),
        # Additional index operations...
    ]
```

## Database Connection Management

### Connection Middleware

A dedicated middleware handles database connection errors:

```python
class DatabaseConnectionMiddleware:
    """Middleware to handle database connection issues."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check connection before processing request
        try:
            connection.ensure_connection()
        except OperationalError:
            # Try to reconnect
            if not ensure_connection():
                # Return a simple error response if reconnection fails
                return JsonResponse({
                    "error": "Database connection error",
                    "message": "The server is experiencing database connectivity issues."
                }, status=503)
        
        # Process the request
        response = self.get_response(request)
        return response
```

### Connection Retry Logic

The system includes robust retry logic for database connections:

```python
def ensure_connection():
    """Ensure database connection is active, retry if needed."""
    db_conn = connections['default']
    try:
        c = db_conn.cursor()
        c.execute("SELECT 1")
        return True
    except OperationalError as e:
        logger.warning(f"Database connection error: {e}")
        
        # Connection might be closed, try to reconnect
        for i in range(3):  # Try 3 times
            try:
                logger.info(f"Attempting database reconnection (attempt {i+1}/3)")
                db_conn.close()
                db_conn.connect()
                logger.info("Database reconnection successful")
                return True
            except OperationalError as e:
                logger.warning(f"Reconnection attempt {i+1} failed: {e}")
                time.sleep(1 * (i + 1))  # Exponential backoff
        
        logger.error("All database reconnection attempts failed")
        return False
```

## Query Optimization Patterns

### Efficient Relationship Querying

The system uses select_related and prefetch_related for efficient relationship querying:

```python
# Efficient: Use select_related to reduce queries when accessing Paper from Note
notes = Note.objects.filter(status='pending').select_related('paper')
for note in notes:
    # This won't trigger additional queries
    paper_title = note.paper.title

# Efficient: Use prefetch_related when accessing multiple notes from a paper
papers = Paper.objects.filter(session_id=session_id).prefetch_related('notes')
for paper in papers:
    # This won't trigger additional queries
    notes_count = paper.notes.count()
```

### Optimized Field Selection

When only specific fields are needed:

```python
# Efficient: Use values() when you only need specific fields
note_contents = Note.objects.filter(paper_id=paper_id).values('content', 'page_number')
```

## Database Testing

A dedicated testing script validates database connectivity:

```python
def test_connection():
    """Test connection to the Neon PostgreSQL database."""
    load_dotenv()
    database_url = os.environ.get('DATABASE_URL')
    
    try:
        print(f"Connecting to Neon database...")
        # Mask credentials in logs
        masked_url = database_url.replace(database_url.split('@')[0], '******')
        print(f"Using: {masked_url}")
        
        # Connect to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        # Test a simple table creation and query
        print("Testing database operations...")
        cursor.execute("CREATE TABLE IF NOT EXISTS connection_test (id SERIAL PRIMARY KEY);")
        cursor.execute("INSERT INTO connection_test DEFAULT VALUES RETURNING id;")
        test_id = cursor.fetchone()[0]
        
        # Clean up test table
        cursor.execute("DROP TABLE connection_test;")
        conn.commit()
        
        print(f"Successfully connected to PostgreSQL. Version: {db_version[0]}")
        print(f"Database connection test successful. Created test record with ID: {test_id}")
        return True
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return False
```

## Production Considerations

### Connection Management

For production environments:

```python
# In production, close connections after each request to prevent connection limits
DATABASES['default']['CONN_MAX_AGE'] = 0

# Increase timeout for potentially longer operations
DATABASES['default']['OPTIONS']['connect_timeout'] = 30
```

### SSL Configuration

All Neon PostgreSQL connections require SSL:

```python
# Add SSL configuration for Neon
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}
```

### Connection Pooling

The system uses Neon's connection pooling for improved performance:

```
# Connection string with pooler endpoint
postgresql://username:password@ep-name-code-pooler.region.aws.neon.tech/dbname?sslmode=require
```

## Integration with Existing Stack

The Neon PostgreSQL database integrates with the existing technology stack:

- **Django ORM**: Abstracts database operations through models
- **Thread Pool**: Database operations are thread-safe for parallel processing
- **WebSockets**: Status updates include database operation results
- **LLM Service**: Database stores AI-generated content including justifications
- **Embedding Service**: Database stores relevance scores for validation
- **PDF Service**: Database stores paper metadata and extracted notes

This database implementation provides a robust, production-ready storage solution for the Research Assistant application, ensuring data persistence, reliability, and performance optimization.