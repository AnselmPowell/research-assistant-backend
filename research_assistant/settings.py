"""
Django settings for research_assistant project.
"""

import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Check if we're in production
IS_PRODUCTION = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Define allowed hosts based on environment
if IS_PRODUCTION:
    # In production, use environment variables for allowed hosts
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
    # Clean up any empty strings from splitting
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
    
    # Add Railway/Render internal hosts
    RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL')
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RAILWAY_STATIC_URL:
        ALLOWED_HOSTS.append(RAILWAY_STATIC_URL.replace('https://', '').replace('http://', ''))
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
else:
    # In development, allow all hosts for convenience
    ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'channels',
    
    # Local apps
    'core',
    'auth_api.apps.AuthApiConfig',  # Authentication system
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.db_connection_middleware.DatabaseConnectionMiddleware',
    # Auth API middleware
    'auth_api.middleware.SecurityHeadersMiddleware',
    'auth_api.middleware.IPBlocklistMiddleware',
    'auth_api.middleware.RateLimitMiddleware',
]

# Add Whitenoise middleware in production only
if IS_PRODUCTION:
    # Insert Whitenoise middleware after SecurityMiddleware
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'research_assistant.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'research_assistant.wsgi.application'

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
    
    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.sqlite3',
    #         'NAME': BASE_DIR / 'db.sqlite3',
    #     }
    # }
   
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

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for static files in production
if IS_PRODUCTION:
    # Make sure whitenoise is installed before enabling these settings
    try:
        import whitenoise
        # Enable compression and caching with WhiteNoise
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        
        # Add compression config
        WHITENOISE_COMPRESSION_ENABLED = True
    except ImportError:
        # If whitenoise is not installed, log a warning but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("WhiteNoise is not installed. Static files will be served by the web server.")

# Secure cookie settings for production
if IS_PRODUCTION:
    # Security settings for CSRF - API-friendly configuration
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = False  # Allow JS access for API calls
    CSRF_COOKIE_SAMESITE = 'None'  # Cross-origin for Railway production
    CSRF_COOKIE_NAME = 'csrftoken'
    CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
    CSRF_USE_SESSIONS = False  # Use cookies, not sessions
    CSRF_COOKIE_AGE = 31449600  # 1 year
    
    # Security settings for session cookies - MATCH CSRF model
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'None'  # Cross-origin for Railway production
    
    # Security middleware settings
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Redirect all non-HTTPS requests to HTTPS
    SECURE_SSL_REDIRECT = True
    
    # Proxy configuration
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    # Development CSRF settings - less restrictive
    CSRF_COOKIE_SECURE = False  # Allow HTTP for development
    CSRF_COOKIE_HTTPONLY = False  # Allow JS access
    CSRF_COOKIE_SAMESITE = 'Lax'  # Standard for same-origin
    CSRF_COOKIE_NAME = 'csrftoken'
    CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
    
    # Development session settings
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# CORS settings
if IS_PRODUCTION:
    # In production, use environment variables for CORS origins
    # Try CORS_ORIGINS first, then fallback to CORS_ALLOWED_ORIGINS
    cors_origins_env = os.environ.get('CORS_ORIGINS', '') or os.environ.get('CORS_ALLOWED_ORIGINS', '')
    
    if cors_origins_env:
        CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        print(f"🔍 CORS DEBUG - Production CORS origins: {CORS_ALLOWED_ORIGINS}")
    else:
        # Emergency fallback - allow the known frontend URL
        CORS_ALLOWED_ORIGINS = [
            "https://research-assistant-frontend-production.up.railway.app"
        ]
        print(f"🔍 CORS DEBUG - Using emergency fallback CORS origins: {CORS_ALLOWED_ORIGINS}")
    
    CORS_ALLOW_ALL_ORIGINS = False
    
    # CRITICAL FIX: Explicitly set all CORS settings to ensure they work
    CORS_ALLOWED_ORIGIN_REGEXES = []
    CORS_ALLOW_CREDENTIALS = True
    CORS_PREFLIGHT_MAX_AGE = 86400
    
    # Debug: Print environment variables for troubleshooting
    print(f"🔍 CORS DEBUG - CORS_ORIGINS env: {os.environ.get('CORS_ORIGINS', 'NOT_SET')}")
    print(f"🔍 CORS DEBUG - CORS_ALLOWED_ORIGINS env: {os.environ.get('CORS_ALLOWED_ORIGINS', 'NOT_SET')}")
    print(f"🔍 CORS DEBUG - IS_PRODUCTION: {IS_PRODUCTION}")
    print(f"🔍 CORS DEBUG - CORS_ALLOW_CREDENTIALS: {CORS_ALLOW_CREDENTIALS}")
    print(f"🔍 CORS DEBUG - CORS_ALLOW_ALL_ORIGINS: {CORS_ALLOW_ALL_ORIGINS}")
else:
    # In development, allow localhost origins
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",  # Next.js development server
        "http://localhost:3001",  # Next.js development server alternate port
    ]
    CORS_ALLOW_ALL_ORIGINS = True  # For development only
    CORS_ALLOW_CREDENTIALS = True

# CORS Methods and Headers (shared for both production and development)
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF Settings for Cross-Origin API
CSRF_TRUSTED_ORIGINS = []
if IS_PRODUCTION:
    # Add production frontend URL to CSRF trusted origins
    frontend_url = "https://research-assistant-frontend-production.up.railway.app"
    CSRF_TRUSTED_ORIGINS.append(frontend_url)
    print(f"🔍 CSRF DEBUG - Production CSRF trusted origins: {CSRF_TRUSTED_ORIGINS}")
    print(f"🔍 CSRF DEBUG - CSRF_COOKIE_SAMESITE: None (cross-origin)")
    print(f"🔍 CSRF DEBUG - CSRF_COOKIE_HTTPONLY: False (JS accessible)")
    print(f"🔍 CSRF DEBUG - CSRF_COOKIE_SECURE: True (HTTPS only)")
else:
    # Development CSRF trusted origins
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    print(f"🔍 CSRF DEBUG - Development CSRF trusted origins: {CSRF_TRUSTED_ORIGINS}")
    print(f"🔍 CSRF DEBUG - CSRF_COOKIE_SAMESITE: Lax (same-origin)")
    print(f"🔍 CSRF DEBUG - CSRF_COOKIE_SECURE: False (HTTP allowed)")

# Remove the comment about CSRF exemption - we're using proper CSRF now
print(f"🔍 CSRF DEBUG - CSRF Protection: ENABLED for all POST/PUT/DELETE endpoints")

# API Keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

# Pydantic-AI configuration
PYDANTIC_AI_CONFIG = {
    'openai': {
        'api_key': OPENAI_API_KEY,
        'default_model': 'gpt-4o'
    },
    # Future providers can be added here
    # 'anthropic': {
    #     'api_key': os.environ.get('ANTHROPIC_API_KEY', ''),
    # },
}

# Set DEFAULT_MODEL in environment for LLM service
os.environ['DEFAULT_MODEL'] = 'openai:gpt-4o-mini'

# ============================================================================
# AUTHENTICATION & AUTHORIZATION SETTINGS
# ============================================================================

from datetime import timedelta

# Authentication settings
AUTH_SETTINGS = {
    'TOKEN_LIFETIME': 60,  # Access token lifetime in minutes
    'REFRESH_TOKEN_LIFETIME': 7,  # Refresh token lifetime in days
    'PASSWORD_RESET_TIMEOUT': 24,  # Password reset timeout in hours
    'MAX_LOGIN_ATTEMPTS': 5,  # Maximum failed login attempts before lockout
    'LOGIN_ATTEMPT_TIMEOUT': 15  # Lockout duration in minutes
}

# JWT token settings
JWT_SETTINGS = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.environ.get('JWT_SECRET', SECRET_KEY),  # Use dedicated JWT key or fallback to SECRET_KEY
    'VERIFYING_KEY': None,
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),  # Long-lived for development
    'REFRESH_TOKEN_LIFETIME': timedelta(days=31),
}

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'auth_api.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Default to requiring authentication
        # Views can explicitly require authentication with permission_classes = [IsAuthenticated]
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CORS credentials (required for authentication cookies)
CORS_ALLOW_CREDENTIALS = True

# IP Blocklist (can be managed dynamically later)
IP_BLOCKLIST = []

# Research Assistant Settings
SMALL_DOC_PAGE_THRESHOLD = 8  # Documents with 8 or fewer pages use the simple path
RELEVANCE_THRESHOLD = 0.18  # Cosine similarity threshold for identifying relevant pages
MAX_WORKERS = 4  # Maximum number of parallel workers

# ASGI Application
ASGI_APPLICATION = 'research_assistant.asgi.application'

# Channel Layers Configuration
if IS_PRODUCTION:
    # Use Redis for production - Railway provides REDIS_URL directly
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        print(f"🔍 REDIS DEBUG - Using Railway REDIS_URL: {redis_url}")
        
        # Test Redis connection
        try:
            import redis
            # Parse the Redis URL
            import urllib.parse as urlparse
            url = urlparse.urlparse(redis_url)
            r = redis.Redis(
                host=url.hostname,
                port=url.port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Try to ping Redis
            r.ping()
            print(f"🔍 REDIS DEBUG - Connection test SUCCESSFUL")
        except Exception as redis_error:
            print(f"🔍 REDIS DEBUG - Connection test FAILED: {redis_error}")
            print(f"🔍 REDIS DEBUG - This may cause WebSocket failures but HTTP should still work")
    else:
        # Fallback to individual components if REDIS_URL not available
        redis_host = os.environ.get('REDISHOST', 'localhost')
        redis_port = os.environ.get('REDISPORT', '6379')
        redis_user = os.environ.get('REDISUSER', 'default')
        redis_password = os.environ.get('REDIS_PASSWORD', '')
        
        if redis_password:
            redis_url = f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}"
            print(f"🔍 REDIS DEBUG - Built from components: redis://{redis_user}:***@{redis_host}:{redis_port}")
        else:
            redis_url = 'redis://localhost:6379/0'
            print(f"🔍 REDIS DEBUG - Using fallback: localhost")
    
    # Configure Channel Layers with error handling
    try:
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {
                    "hosts": [redis_url],
                },
            },
        }
        print(f"🔍 REDIS DEBUG - Channel layers configured successfully")
    except Exception as channel_error:
        print(f"🔍 REDIS DEBUG - Channel layer configuration failed: {channel_error}")
        # Fallback to in-memory for WebSocket if Redis fails
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
        print(f"🔍 REDIS DEBUG - Using fallback InMemoryChannelLayer")
else:
    # Use in-memory channel layer for development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if IS_PRODUCTION else 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if IS_PRODUCTION else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO' if IS_PRODUCTION else 'DEBUG',
            'propagate': False,
        },
        'auth_api': {
            'handlers': ['console'],
            'level': 'INFO' if IS_PRODUCTION else 'DEBUG',
            'propagate': False,
        },
    },
}