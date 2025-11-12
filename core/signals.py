"""
Signals for the core application.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ResearchSession, Paper, Note
import logging

# Configure logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=ResearchSession)
def log_research_session_save(sender, instance, created, **kwargs):
    """Log when a research session is created or updated."""
    if created:
        print(f"Research session created: {instance.id}")
    else:
        print(f"Research session updated: {instance.id}, status: {instance.status}")

@receiver(post_save, sender=Paper)
def log_paper_save(sender, instance, created, **kwargs):
    """Log when a paper is created or updated."""
    if created:
        print(f"Paper created: {instance.id} for session {instance.session.id}")
    else:
        print(f"Paper updated: {instance.id}, status: {instance.status}")

@receiver(post_save, sender=Note)
def log_note_save(sender, instance, created, **kwargs):
    """Log when a note is created or updated."""
    if created:
        print(f"Note created: {instance.id} for paper {instance.paper.id}")
