"""
Admin configuration for the core application.
"""

from django.contrib import admin
from .models import ResearchSession, Paper, Note


class NoteInline(admin.TabularInline):
    """Inline admin for notes."""
    model = Note
    extra = 0
    fields = ('content', 'page_number', 'note_type', 'matches_topic')
    readonly_fields = ('created_at',)


class PaperInline(admin.TabularInline):
    """Inline admin for papers."""
    model = Paper
    extra = 0
    fields = ('title', 'url', 'status', 'harvard_reference')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    """Admin for research sessions."""
    list_display = ('id', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PaperInline]


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    """Admin for papers."""
    list_display = ('id', 'title', 'session', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'url')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [NoteInline]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin for notes."""
    list_display = ('id', 'paper', 'note_type', 'page_number', 'created_at')
    list_filter = ('note_type', 'created_at')
    search_fields = ('content', 'matches_topic')
    readonly_fields = ('created_at',)
