"""
Django admin configuration for auth_api.
"""

from django.contrib import admin
from .models import UserProfile, UserSession, LoginAttempt


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile."""
    list_display = ('email', 'first_name', 'last_name', 'is_social_account', 'account_created')
    list_filter = ('is_social_account', 'is_email_verified', 'account_created')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('account_created', 'last_login')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email', 'first_name', 'last_name')
        }),
        ('Account Status', {
            'fields': ('is_social_account', 'social_provider', 'is_email_verified')
        }),
        ('Timestamps', {
            'fields': ('account_created', 'last_login')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface for UserSession."""
    list_display = ('user', 'created_at', 'expires_at', 'is_active', 'ip_address')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('id', 'created_at', 'session_token', 'refresh_token')
    
    fieldsets = (
        ('Session Info', {
            'fields': ('id', 'user', 'is_active')
        }),
        ('Tokens', {
            'fields': ('session_token', 'refresh_token'),
            'classes': ('collapse',)
        }),
        ('Device & Location', {
            'fields': ('device_info', 'ip_address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual session creation."""
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin interface for LoginAttempt."""
    list_display = ('email', 'ip_address', 'attempt_time', 'was_successful')
    list_filter = ('was_successful', 'attempt_time')
    search_fields = ('email', 'ip_address')
    readonly_fields = ('email', 'ip_address', 'attempt_time', 'was_successful')
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make read-only."""
        return False
