"""
URL patterns for the core application.
"""

from django.urls import path
from .views import (
    StartResearchView, 
    SessionDetailView, 
    SessionNotesView, 
    SessionStatusView,
    WebSocketTestView,
    SavedNotesView,
    UpdateNoteStatusView,
    UpdateNoteContentView,
    DeleteNoteView,
    CleanupSessionNotesView,
    BulkNoteStatusUpdateView,
    BulkNoteDeleteView,
    ValidatePdfUrlView,
    HealthCheckView,
    # Organization views
    ProjectListCreateView,
    ProjectDetailView,
    SectionCreateView,
    SectionDetailView,
    GroupCreateView,
    GroupDetailView,
    NoteOrganizationView
)

urlpatterns = [
    # Health check endpoint
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # Research session endpoints
    path('research/start/', StartResearchView.as_view(), name='start_research'),
    path('research/session/<str:session_id>/', SessionDetailView.as_view(), name='session_detail'),
    path('research/session/<str:session_id>/notes/', SessionNotesView.as_view(), name='session_notes'),
    path('research/session/<str:session_id>/status/', SessionStatusView.as_view(), name='session_status'),
    
    # WebSocket test endpoint
    path('websocket-test/', WebSocketTestView.as_view(), name='websocket_test'),
    
    # Note management endpoints
    path('notes/saved/', SavedNotesView.as_view(), name='saved_notes'),
    path('notes/cleanup/', CleanupSessionNotesView.as_view(), name='cleanup_notes'),
    path('notes/bulk/status/', BulkNoteStatusUpdateView.as_view(), name='bulk_note_status_update'),
    path('notes/bulk/delete/', BulkNoteDeleteView.as_view(), name='bulk_note_delete'),
    path('notes/<str:note_id>/status/', UpdateNoteStatusView.as_view(), name='update_note_status'),
    path('notes/<str:note_id>/update/', UpdateNoteContentView.as_view(), name='update_note_content'),
    path('notes/<str:note_id>/delete/', DeleteNoteView.as_view(), name='delete_note'),
    path('notes/<str:note_id>/organization/', NoteOrganizationView.as_view(), name='note_organization'),
    
    # Utility endpoints
    path('validate-pdf-url/', ValidatePdfUrlView.as_view(), name='validate_pdf_url'),
    
    # Organization endpoints
    path('projects/', ProjectListCreateView.as_view(), name='project_list'),
    path('projects/<str:project_id>/', ProjectDetailView.as_view(), name='project_detail'),
    path('sections/', SectionCreateView.as_view(), name='section_create'),
    path('sections/<str:section_id>/', SectionDetailView.as_view(), name='section_detail'),
    path('groups/', GroupCreateView.as_view(), name='group_create'),
    path('groups/<str:group_id>/', GroupDetailView.as_view(), name='group_detail'),
]
