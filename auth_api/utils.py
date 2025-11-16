# auth_api/utils.py

from datetime import datetime, timedelta
from .models import LoginAttempt
from django.conf import settings


def get_client_ip(request):
    """
    Extract client IP address from request.
    Handles both direct connections and proxied requests.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the chain (client's real IP)
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def check_login_attempts(email, ip_address):
    """
    Check if user/IP has exceeded maximum failed login attempts.
    
    Args:
        email: User's email address
        ip_address: IP address of the request
        
    Returns:
        bool: True if login attempt is allowed, False if rate limited
    """
    timeout_minutes = settings.AUTH_SETTINGS['LOGIN_ATTEMPT_TIMEOUT']
    max_attempts = settings.AUTH_SETTINGS['MAX_LOGIN_ATTEMPTS']
    
    # Calculate cutoff time for recent attempts
    cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
    
    # Count recent failed attempts for this email/IP combination
    recent_attempts = LoginAttempt.objects.filter(
        email=email,
        ip_address=ip_address,
        attempt_time__gte=cutoff_time,
        was_successful=False
    ).count()
    
    # Allow login if under the limit
    return recent_attempts < max_attempts


def log_login_attempt(email, ip_address, success):
    """
    Log a login attempt for security tracking.
    
    Args:
        email: User's email address
        ip_address: IP address of the request
        success: Whether the login was successful
    """
    LoginAttempt.objects.create(
        email=email,
        ip_address=ip_address,
        was_successful=success
    )


def cleanup_old_login_attempts(days=7):
    """
    Clean up old login attempt records.
    Should be run periodically via cron or Celery.
    
    Args:
        days: Number of days to keep records (default 7)
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = LoginAttempt.objects.filter(
        attempt_time__lt=cutoff_date
    ).delete()[0]
    return deleted_count
