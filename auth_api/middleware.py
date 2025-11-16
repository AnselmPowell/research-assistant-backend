# auth_api/middleware.py

from django.conf import settings
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.
    Protects against common web vulnerabilities.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Force HTTPS in production
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response['Content-Security-Policy'] = "default-src 'self'"
        
        return response


class IPBlocklistMiddleware:
    """
    Block requests from suspicious or banned IP addresses.
    IP blocklist can be configured in settings or managed via admin.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Load blocklist from settings or database
        self.ip_blocklist = getattr(settings, 'IP_BLOCKLIST', [])

    def __call__(self, request):
        ip = self.get_client_ip(request)
        
        # Check if IP is blocked
        if ip in self.ip_blocklist:
            return HttpResponseForbidden('Access denied: Your IP address has been blocked.')
        
        return self.get_response(request)

    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class RateLimitMiddleware:
    """
    Basic rate limiting to prevent abuse.
    Limits requests per IP address per time window.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {}  # Store: {ip: [timestamp1, timestamp2, ...]}

    def __call__(self, request):
        ip = self.get_client_ip(request)
        now = datetime.now()

        # Clean up old entries periodically
        self.cleanup_old_entries(now)

        # Check if this IP is rate limited
        if self.is_rate_limited(ip, now):
            return HttpResponseForbidden('Rate limit exceeded. Please try again later.')

        # Record this request
        self.record_request(ip, now)

        return self.get_response(request)

    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def cleanup_old_entries(self, now):
        """Remove timestamps older than 1 minute"""
        cutoff = now - timedelta(minutes=1)
        self.rate_limits = {
            ip: [t for t in times if t > cutoff]
            for ip, times in self.rate_limits.items()
            if any(t > cutoff for t in times)
        }

    def is_rate_limited(self, ip, now):
        """Check if IP has exceeded rate limit"""
        if ip not in self.rate_limits:
            return False
        
        # Count requests in the last minute
        recent_requests = len([
            t for t in self.rate_limits[ip]
            if t > now - timedelta(minutes=1)
        ])
        
        # Allow 100 requests per minute (adjust as needed)
        return recent_requests >= 100

    def record_request(self, ip, now):
        """Record a request timestamp for this IP"""
        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
        self.rate_limits[ip].append(now)
