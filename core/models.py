"""
Models for the core application.
"""

from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone

class ResearchSession(models.Model):
    """A research session initiated by a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='research_sessions',
        null=True,  # Allow null temporarily for migration
        blank=True
    )
    topics = models.JSONField(default=list)
    info_queries = models.JSONField(default=list)
    direct_urls = models.JSONField(default=list)
    status = models.CharField(
        max_length=50, 
        choices=[
            ('initiated', 'Initiated'),
            ('searching', 'Searching'),
            ('analyzing', 'Analyzing'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('error', 'Error')
        ],
        default="initiated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        user_info = f" (User: {self.user.email})" if self.user else " (Anonymous)"
        return f"Session {self.id}{user_info} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),  # Add user index for filtering
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class Paper(models.Model):
    """A paper processed during a research session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name="papers")
    url = models.URLField()
    title = models.CharField(max_length=500, blank=True)
    authors = models.JSONField(default=list)
    year = models.CharField(max_length=20, blank=True)  # Added year field
    summary = models.TextField(blank=True)              # Added summary field
    harvard_reference = models.TextField(blank=True)
    total_pages = models.IntegerField(default=0)        # Added total_pages field
    status = models.CharField(
        max_length=50, 
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('success', 'Success'),
            ('no_relevant_info', 'No Relevant Information'),
            ('error', 'Error')
        ],
        default="pending"
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Paper {self.title or self.url[:30]}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class Note(models.Model):
    """A research note extracted from a paper."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="notes")
    content = models.TextField()
    page_number = models.IntegerField(default=1)
    note_type = models.CharField(
        max_length=50, 
        choices=[
            ('quote', 'Quote'),
            ('statistic', 'Statistic'),
            ('methodology', 'Methodology')
        ],
        default="quote"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('kept', 'Kept'),
            ('discarded', 'Discarded')
        ],
        default="pending"
    )
    search_criteria = models.TextField(blank=True)
    matches_topic = models.TextField(blank=True)
    justification = models.TextField(blank=True)  # Added justification field
    inline_citations = models.JSONField(default=list)
    reference_list = models.JSONField(default=dict)
    # AI relevance scoring
    relevance_score = models.FloatField(null=True, blank=True, default=None)
    # User interaction fields
    flagged = models.BooleanField(default=False)  # For marking important notes
    favorite = models.BooleanField(default=False)  # For favorite notes
    user_annotations = models.TextField(blank=True)  # For user's notes about this note
    # Organization fields
    projects = models.ManyToManyField('Project', related_name='notes', blank=True)
    sections = models.ManyToManyField('Section', related_name='notes', blank=True)
    groups = models.ManyToManyField('Group', related_name='notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Note {self.id} - {self.content[:50]}..."
    
    def to_frontend_format(self):
        """Convert to the format expected by the frontend."""
        # Get IDs for organization
        project_ids = [str(project.id) for project in self.projects.all()]
        section_ids = [str(section.id) for section in self.sections.all()]
        group_ids = [str(group.id) for group in self.groups.all()]
        
        return {
            "id": str(self.id),
            "content": self.content,
            "sections": section_ids,
            "groups": group_ids, 
            "projects": project_ids,
            "type": self.note_type,
            "status": self.status,
            "source": self.paper.title,
            "sourceDetails": f"Page {self.page_number}",
            "sourceUrl": self.paper.url,
            "searchCriteria": self.search_criteria,
            "userAnnotations": self.user_annotations or "",
            "flagged": self.flagged,
            "favorite": self.favorite,
            "createdAt": self.created_at.isoformat(),
            "modifiedAt": self.created_at.isoformat(),
            "harvardReference": self.paper.harvard_reference,
            "pageNumber": self.page_number,
            "inlineCitations": self.inline_citations,
            "referenceList": self.reference_list,
            "matchesTopic": self.matches_topic,
            "justification": self.justification,  # Added justification field
            "relevanceScore": self.relevance_score,  # Added relevance score field
            # Additional paper fields
            "authors": self.paper.authors,
            "year": self.paper.year,
            "summary": self.paper.summary,
            "total_pages": self.paper.total_pages
        }
    
    class Meta:
        ordering = ['page_number', 'created_at']
        indexes = [
            models.Index(fields=['paper']),
            models.Index(fields=['note_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        

class Project(models.Model):
    """User-created project for organizing research notes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='projects',
        null=True,  # Allow null temporarily for migration
        blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        user_info = f" (User: {self.user.email})" if self.user else " (Anonymous)"
        return f"Project: {self.name}{user_info}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
    
    def to_dict(self):
        """Convert project to dictionary with sections and groups."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'createdAt': self.created_at.isoformat(),
            'modifiedAt': self.modified_at.isoformat(),
            'sections': [section.to_dict() for section in self.sections.all()],
            'groups': [group.to_dict() for group in self.project_groups.filter(section__isnull=True)]
        }


class Section(models.Model):
    """Section within a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sections',
        null=True,  # Allow null temporarily for migration
        blank=True
    )
    project = models.ForeignKey(Project, related_name='sections', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Section: {self.name} (in {self.project.name})"
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['project']),
        ]
    
    def to_dict(self):
        """Convert section to dictionary with groups."""
        return {
            'id': str(self.id),
            'projectId': str(self.project.id),
            'name': self.name,
            'order': self.order,
            'createdAt': self.created_at.isoformat(),
            'groups': [group.to_dict() for group in self.groups.all()]
        }


class Group(models.Model):
    """Group within a section or directly in a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='note_groups',  # Changed from 'groups' to avoid clash
        null=True,  # Allow null temporarily for migration
        blank=True
    )
    name = models.CharField(max_length=255)
    section = models.ForeignKey(Section, related_name='groups', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, related_name='project_groups', on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.section:
            return f"Group: {self.name} (in section {self.section.name})"
        return f"Group: {self.name} (in project {self.project.name})"

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['section']),
            models.Index(fields=['project']),
        ]

    def to_dict(self):
        """Convert group to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'sectionId': str(self.section.id) if self.section else None,
            'projectId': str(self.project.id),
            'order': self.order,
            'createdAt': self.created_at.isoformat()
        }
