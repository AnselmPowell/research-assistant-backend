"""
Authentication models for user profiles and sessions.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class UserProfile(models.Model):
    """Extended user profile with additional fields."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    
    # Social authentication fields
    is_social_account = models.BooleanField(default=False)
    social_provider = models.CharField(max_length=50, blank=True, null=True)
    
    # Account status
    is_email_verified = models.BooleanField(default=False)
    
    # Timestamps
    account_created = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user']),
        ]


class UserSession(models.Model):
    """User session management for tracking active sessions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    device_info = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username}'s session"
    
    def is_valid(self):
        """Check if session is still valid."""
        return self.is_active and self.expires_at > timezone.now()
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active']),
        ]


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created."""
    if created:
        UserProfile.objects.create(
            user=instance,
            email=instance.email,
            first_name=instance.first_name,
            last_name=instance.last_name
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class LoginAttempt(models.Model):
    """Track login attempts for rate limiting and security."""
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    attempt_time = models.DateTimeField(auto_now_add=True)
    was_successful = models.BooleanField(default=False)
    
    def __str__(self):
        status = "Success" if self.was_successful else "Failed"
        return f"{self.email} - {status} - {self.attempt_time}"
    
    class Meta:
        db_table = 'login_attempts'
        indexes = [
            models.Index(fields=['email', 'ip_address']),
            models.Index(fields=['attempt_time']),
        ]
        ordering = ['-attempt_time']
