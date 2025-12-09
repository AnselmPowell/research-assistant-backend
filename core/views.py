"""
Views for the core application.
"""
import io
import uuid
import re
import logging
import signal
import traceback
import PyPDF2
from urllib.parse import urlparse
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import ResearchSession, Paper, Note, Project, Section, Group
from .serializers import (
    ResearchRequestSerializer, 
    ResearchSessionSerializer,
    ProjectSerializer,
    SectionSerializer,
    GroupSerializer,
    NoteOrganizationSerializer
)
from .tasks import process_research_session
import PyPDF2
from .utils.debug import debug_print

# Remove CSRF exemption - we now use proper CSRF for all API endpoints
class StartResearchView(APIView):
    """View for starting a research session."""
    # Allow anyone to start research (unauthenticated or authenticated)
    permission_classes = []  # Override default authentication requirement
    
    def post(self, request, format=None):
        """
        Start a new research session.
        
        Expected payload:
        {
            "sessionId": "optional-uuid-if-resuming",
            "query": {
                "topics": ["topic1", "topic2"],
                "infoQueries": ["specific question 1", "specific question 2"],
                "urls": ["https://example.com/paper.pdf"]
            }
        }
        
        Returns:
        {
            "status": "initiated",
            "sessionId": "uuid-of-session"
        }
        """
        serializer = ResearchRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            # Extract data
            validated_data = serializer.validated_data
            session_id = validated_data.get('sessionId')
            query = validated_data.get('query')
            
            # Get user if authenticated, None otherwise
            user = request.user if request.user.is_authenticated else None
            
            # Create or get session
            if session_id:
                session, created = ResearchSession.objects.get_or_create(
                    id=session_id,
                    defaults={
                        'user': user,  # Assign user
                        'topics': query.get('topics', []),
                        'info_queries': query.get('infoQueries', []),
                        'direct_urls': query.get('urls', []),
                        'status': 'initiated'
                    }
                )
                
                if not created:
                    # Update existing session
                    session.user = user  # Update user
                    session.topics = query.get('topics', [])
                    session.info_queries = query.get('infoQueries', [])
                    session.direct_urls = query.get('urls', [])
                    session.status = 'initiated'
                    session.save()
            else:
                # Create new session
                session_id = str(uuid.uuid4())
                session = ResearchSession.objects.create(
                    id=session_id,
                    user=user,  # Assign user
                    topics=query.get('topics', []),
                    info_queries=query.get('infoQueries', []),
                    direct_urls=query.get('urls', []),
                    status='initiated'
                )
            
            # Extract settings data if present
            settings_data = query.get('settings', {})
            
            # Start background task with settings
            process_research_session(str(session.id), settings_data)
            
            return Response({
                'status': 'initiated',
                'sessionId': str(session.id)
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SessionDetailView(APIView):
    """View for retrieving session details."""
    
    def get(self, request, session_id, format=None):
        """
        Get detailed information about a research session.
        
        Returns all session data including papers and their notes.
        """
        session = get_object_or_404(ResearchSession, id=session_id)
        serializer = ResearchSessionSerializer(session)
        return Response(serializer.data)

class SessionNotesView(APIView):
    """View for retrieving all notes for a session."""
    
    def get(self, request, session_id, format=None):
        """
        Get all notes for a session formatted for the frontend.
        
        Returns a flat list of notes with full details including Harvard references
        and citation information.
        """
        session = get_object_or_404(ResearchSession, id=session_id)
        
        # DEBUG: Check what we actually have in the database
        total_notes = Note.objects.filter(paper__session=session).count()
        debug_print(f"DEBUG SESSION {session_id}: TOTAL NOTES IN DATABASE: {total_notes}")
        
        total_papers = session.papers.count()
        debug_print(f"DEBUG SESSION {session_id}: TOTAL PAPERS IN SESSION: {total_papers}")
        
        # Check for orphaned notes (notes that exist but aren't linked properly)
        orphaned_notes = Note.objects.filter(paper__session_id=session_id)
        debug_print(f"DEBUG SESSION {session_id}: DIRECT QUERY FOUND {orphaned_notes.count()} NOTES")
        
        notes = []
        
        for paper in session.papers.all():
            paper_note_count = paper.notes.count()
            debug_print(f"DEBUG SESSION {session_id}: Paper {paper.id} ({paper.title[:50]}...) has {paper_note_count} notes")
            
            for note in paper.notes.all():
                notes.append(note.to_frontend_format())
        
        debug_print(f"DEBUG SESSION {session_id}: RETURNING {len(notes)} NOTES TO FRONTEND")
        
        # If we found no notes through relationships but direct query found notes, use direct query
        if len(notes) == 0 and orphaned_notes.count() > 0:
            debug_print(f"DEBUG SESSION {session_id}: RELATIONSHIP BROKEN - Using direct query as fallback")
            notes = [note.to_frontend_format() for note in orphaned_notes]
            debug_print(f"DEBUG SESSION {session_id}: FALLBACK RETURNED {len(notes)} NOTES")
        
        return Response(notes)

class SessionStatusView(APIView):
    """View for checking the status of a session."""
    
    def get(self, request, session_id, format=None):
        """
        Get session status and progress information.
        
        Returns:
        {
            "status": "searching|processing|completed|error",
            "totalPapers": 5,
            "completedPapers": 3,
            "progress": 0.6,
            "isComplete": false
        }
        """
        session = get_object_or_404(ResearchSession, id=session_id)
        
        # Count papers and completed papers
        total_papers = session.papers.count()
        completed_papers = session.papers.filter(
            status__in=['success', 'no_relevant_info', 'error']
        ).count()
        
        return Response({
            'status': session.status,
            'totalPapers': total_papers,
            'completedPapers': completed_papers,
            'progress': completed_papers / total_papers if total_papers > 0 else 0,
            'isComplete': session.status == 'completed'
        })

class WebSocketTestView(APIView):
    """View for testing WebSocket connectivity."""
    
    def get(self, request, format=None):
        """
        Test WebSocket connectivity.
        
        Returns information about WebSocket availability and configuration.
        """
        host = request.get_host()
        secure = request.is_secure()
        ws_protocol = "wss" if secure else "ws"
        
        return Response({
            "status": "available",
            "websocket_url": f"{ws_protocol}://{host}/ws/test/",
            "connection_instructions": "Connect to this WebSocket URL to test real-time communication"
        })

class SavedNotesView(APIView):
    """View for retrieving saved notes."""
    # Allow anyone to access (will filter by user if authenticated)
    permission_classes = []  # Override default authentication requirement
    
    def get(self, request, format=None):
        """
        Get all saved (kept) notes.
        
        Optional query parameters:
        - status: Filter by note status (kept, discarded, pending)
        
        Returns a list of notes formatted for the frontend.
        If user is authenticated, only returns their notes.
        If user is not authenticated, returns all notes (for backward compatibility).
        """
        status_filter = request.query_params.get('status', 'kept')
        
        # Start with base query
        note_query = Note.objects.filter(status=status_filter)
        
        # If user is authenticated, filter by user
        if request.user.is_authenticated:
            note_query = note_query.filter(paper__session__user=request.user)
        
        notes = []
        for note in note_query:
            notes.append(note.to_frontend_format())
        
        return Response(notes)

class UpdateNoteStatusView(APIView):
    """View for updating note status (kept/discarded)."""
    
    def post(self, request, note_id, format=None):
        """
        Update note status.
        
        Expected payload:
        {
            "status": "kept|discarded|pending"
        }
        
        Returns:
        {
            "status": "success",
            "note_id": "uuid-of-note",
            "new_status": "kept|discarded|pending"
        }
        """
        note = get_object_or_404(Note, id=note_id)
        new_status = request.data.get('status')
        
        if new_status not in ['kept', 'discarded', 'pending']:
            return Response(
                {"error": "Invalid status. Must be 'kept', 'discarded', or 'pending'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note.status = new_status
        note.save()
        
        return Response({
            "status": "success",
            "note_id": str(note.id),
            "new_status": note.status
        })

class UpdateNoteContentView(APIView):
    """View for updating note content and metadata."""
    
    def post(self, request, note_id, format=None):
        """
        Update a note's content and metadata.
        
        Expected payload: Object with fields to update
        {
            "content": "Updated content text",
            "type": "quote|statistic|methodology",
            "userAnnotations": "User's notes about this note",
            "flagged": true|false,
            "favorite": true|false
        }
        
        Returns:
        {
            "status": "success",
            "note_id": "uuid-of-note",
            "note": {note object with updated fields}
        }
        """
        note = get_object_or_404(Note, id=note_id)
        changes = request.data
        
        # Map frontend field names to model field names
        field_mapping = {
            'type': 'note_type',
            'content': 'content',
            'userAnnotations': 'user_annotations',
            'flagged': 'flagged',
            'favorite': 'favorite'
        }
        
        # Apply changes to allowed fields
        for field, model_field in field_mapping.items():
            if field in changes:
                # Check if field exists on model
                if hasattr(note, model_field):
                    setattr(note, model_field, changes[field])
                else:
                    # Handle the case where the model doesn't have the field yet
                    # This provides flexibility as we enhance the Note model
                    debug_print(f"Field {model_field} not found on Note model - skipping")
        
        note.save()
        
        return Response({
            "status": "success",
            "note_id": str(note.id),
            "note": note.to_frontend_format()
        })


class DeleteNoteView(APIView):
    """View for permanently deleting a note."""
    
    def delete(self, request, note_id, format=None):
        """
        Permanently delete a note from the database.
        
        Returns:
        {
            "status": "success",
            "note_id": "uuid-of-deleted-note"
        }
        """
        try:
            note = get_object_or_404(Note, id=note_id)
            note_id_str = str(note.id)
            
            # Delete the note, which automatically handles M2M relationships
            note.delete()
            
            return Response({
                "status": "success",
                "note_id": note_id_str
            })
        except Exception as e:
            return Response({
                "status": "error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CleanupSessionNotesView(APIView):
    """View for cleaning up notes from previous sessions."""
    
    def post(self, request, format=None):
        """
        Delete all notes with status 'pending' or 'discarded'.
        
        Returns:
        {
            "status": "success",
            "deleted_count": number of deleted notes
        }
        """
        try:
            # Count before deleting
            pending_count = Note.objects.filter(status='pending').count()
            discarded_count = Note.objects.filter(status='discarded').count()
            
            # Delete the notes
            Note.objects.filter(status__in=['pending', 'discarded']).delete()
            
            return Response({
                "status": "success",
                "deleted_count": pending_count + discarded_count
            })
        except Exception as e:
            return Response({
                "status": "error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectListCreateView(APIView):
    """View for listing and creating projects."""
    
    def get(self, request, format=None):
        """
        Get all projects with their sections and groups.
        If user is authenticated, only returns their projects.
        If user is not authenticated, returns all projects (backward compatible).
        
        Returns a list of projects, each containing their sections and groups.
        """
        # Filter by user if authenticated
        if request.user.is_authenticated:
            projects = Project.objects.filter(user=request.user)
        else:
            projects = Project.objects.all()
        
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Create a new project.
        
        Expected payload:
        {
            "name": "Project Name",
            "description": "Project Description"
        }
        
        Returns the created project.
        """
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            # Assign user if authenticated
            user = request.user if request.user.is_authenticated else None
            project = serializer.save(user=user)
            return Response(project.to_dict(), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectDetailView(APIView):
    """View for retrieving, updating, and deleting a project."""
    
    def get(self, request, project_id, format=None):
        """
        Get a project with its sections and groups.
        If user is authenticated, verifies ownership.
        
        Returns the project with all its sections and groups.
        """
        # Verify ownership if authenticated
        if request.user.is_authenticated:
            project = get_object_or_404(Project, id=project_id, user=request.user)
        else:
            project = get_object_or_404(Project, id=project_id)
        return Response(project.to_dict())
    
    def put(self, request, project_id, format=None):
        """
        Update a project.
        
        Expected payload:
        {
            "name": "Updated Project Name",
            "description": "Updated Project Description"
        }
        
        Returns the updated project.
        """
        # Verify ownership if authenticated
        if request.user.is_authenticated:
            project = get_object_or_404(Project, id=project_id, user=request.user)
        else:
            project = get_object_or_404(Project, id=project_id)
        
        serializer = ProjectSerializer(project, data=request.data)
        if serializer.is_valid():
            project = serializer.save()
            return Response(project.to_dict())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, project_id, format=None):
        """
        Delete a project.
        
        Deletes the project and all its sections and groups.
        """
        # Verify ownership if authenticated
        if request.user.is_authenticated:
            project = get_object_or_404(Project, id=project_id, user=request.user)
        else:
            project = get_object_or_404(Project, id=project_id)
        
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SectionCreateView(APIView):
    """View for creating sections."""
    
    def post(self, request, format=None):
        """
        Create a new section within a project.
        
        Expected payload:
        {
            "project": "project-uuid",
            "name": "Section Name",
            "order": 1
        }
        
        Returns the created section.
        """
        serializer = SectionSerializer(data=request.data)
        if serializer.is_valid():
            # Assign user if authenticated
            user = request.user if request.user.is_authenticated else None
            section = serializer.save(user=user)
            return Response(section.to_dict(), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SectionDetailView(APIView):
    """View for retrieving, updating, and deleting a section."""
    
    def get(self, request, section_id, format=None):
        """
        Get a section with its groups.
        
        Returns the section with all its groups.
        """
        section = get_object_or_404(Section, id=section_id)
        return Response(section.to_dict())
    
    def put(self, request, section_id, format=None):
        """
        Update a section.
        
        Expected payload:
        {
            "name": "Updated Section Name",
            "order": 2
        }
        
        Returns the updated section.
        """
        section = get_object_or_404(Section, id=section_id)
        serializer = SectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            section = serializer.save()
            return Response(section.to_dict())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, section_id, format=None):
        """
        Delete a section.
        
        Deletes the section and all its groups.
        """
        section = get_object_or_404(Section, id=section_id)
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupCreateView(APIView):
    """View for creating groups."""
    
    def post(self, request, format=None):
        """
        Create a new group within a section or project.
        
        Expected payload:
        {
            "name": "Group Name",
            "section": "section-uuid" (optional),
            "project": "project-uuid",
            "order": 1
        }
        
        Returns the created group.
        """
        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get user if authenticated
                user = request.user if request.user.is_authenticated else None
                
                # Get the ID from the request data or generate a new one
                group_id = request.data.get('id') or uuid.uuid4()
                
                # Try to convert string ID to UUID if necessary
                if isinstance(group_id, str):
                    try:
                        # If it's already a UUID string, this will work
                        group_id = uuid.UUID(group_id)
                    except ValueError:
                        # If it's not a valid UUID string, generate a new one
                        debug_print(f"Invalid UUID format: {group_id}, generating new UUID")
                        group_id = uuid.uuid4()
                
                # Create the group with the specified ID and user
                group = serializer.save(id=group_id, user=user)
                debug_print(f"Group created with ID: {group.id}, Name: {group.name}")
                return Response(group.to_dict(), status=status.HTTP_201_CREATED)
            except Exception as e:
                debug_print(f"Error creating group: {e}")
                # If there was an error with the custom ID, fall back to default behavior
                group = serializer.save(user=user)
                debug_print(f"Group created with generated ID: {group.id}")
                return Response(group.to_dict(), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    """View for retrieving, updating, and deleting a group."""
    
    def get(self, request, group_id, format=None):
        """
        Get a group.
        
        Returns the group.
        """
        group = get_object_or_404(Group, id=group_id)
        return Response(group.to_dict())
    
    def put(self, request, group_id, format=None):
        """
        Update a group.
        
        Expected payload:
        {
            "name": "Updated Group Name",
            "order": 2
        }
        
        Returns the updated group.
        """
        group = get_object_or_404(Group, id=group_id)
        serializer = GroupSerializer(group, data=request.data, partial=True)
        if serializer.is_valid():
            group = serializer.save()
            return Response(group.to_dict())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, group_id, format=None):
        """
        Delete a group.
        """
        group = get_object_or_404(Group, id=group_id)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteOrganizationView(APIView):
    """View for updating a note's organization."""
    
    def post(self, request, note_id, format=None):
        """
        Update a note's organization (projects, sections, groups).
        
        Expected payload:
        {
            "projects": ["project-uuid-1", "project-uuid-2"],
            "sections": ["section-uuid-1", "section-uuid-2"],
            "groups": ["group-uuid-1", "group-uuid-2"]
        }
        
        Returns the updated note.
        """
        note = get_object_or_404(Note, id=note_id)
        serializer = NoteOrganizationSerializer(data=request.data)
        
        if serializer.is_valid():
            debug_print(f"Note organization update for note {note_id}")
            debug_print(f"Full request data: {request.data}")
            
            # Always check all organization types
            # Even if not in the request data, we should clear the relationships
            
            # Projects
            project_ids = serializer.validated_data.get('projects', [])
            debug_print(f"Updating note projects: {project_ids}")
            note.projects.clear()
            for project_id in project_ids:
                try:
                    project = Project.objects.get(id=project_id)
                    note.projects.add(project)
                    debug_print(f"Added note to project: {project.id} - {project.name}")
                except Project.DoesNotExist:
                    debug_print(f"Project not found: {project_id}")
                    pass  # Skip invalid IDs
            
            # Sections
            section_ids = serializer.validated_data.get('sections', [])
            debug_print(f"Updating note sections: {section_ids}")
            note.sections.clear()
            
            # Normal section assignment - even if empty
            for section_id in section_ids:
                # Skip virtual 'uncategorized' section - it's not a real DB entity
                if section_id == 'uncategorized':
                    debug_print("Skipping virtual 'uncategorized' section")
                    continue
                    
                try:
                    section = Section.objects.get(id=section_id)
                    note.sections.add(section)
                    debug_print(f"Added note to section: {section.id} - {section.name}")
                except Section.DoesNotExist:
                    debug_print(f"Section not found: {section_id}")
                    pass  # Skip invalid IDs
            
            # Groups
            group_ids = serializer.validated_data.get('groups', [])
            debug_print(f"Updating note groups: {group_ids}")
            note.groups.clear()
            for group_id in group_ids:
                try:
                    group = Group.objects.get(id=group_id)
                    note.groups.add(group)
                    debug_print(f"Added note to group: {group.id} - {group.name}")
                except Group.DoesNotExist:
                    debug_print(f"Group not found: {group_id}")
                    pass  # Skip invalid IDs
            
            return Response(note.to_frontend_format())
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkNoteStatusUpdateView(APIView):
    """View for updating multiple notes' status at once."""
    
    def post(self, request, format=None):
        """
        Update status for multiple notes in one operation.
        
        Expected payload:
        {
            "note_ids": ["uuid1", "uuid2", "uuid3", ...],
            "status": "kept|discarded|pending"
        }
        
        Returns:
        {
            "status": "success",
            "updated_count": number of notes updated,
            "notes": [list of updated notes ids]
        }
        """
        try:
            # Validate input
            note_ids = request.data.get('note_ids', [])
            new_status = request.data.get('status')
            
            if not note_ids or not isinstance(note_ids, list):
                return Response(
                    {"error": "note_ids must be a non-empty list"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if new_status not in ['kept', 'discarded', 'pending']:
                return Response(
                    {"error": "Invalid status. Must be 'kept', 'discarded', or 'pending'."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update all notes at once - much more efficient
            updated_notes = Note.objects.filter(id__in=note_ids)
            updated_count = updated_notes.count()
            
            # Get IDs before update for response
            updated_ids = list(updated_notes.values_list('id', flat=True))
            
            # Bulk update
            updated_notes.update(status=new_status)
            
            return Response({
                "status": "success",
                "updated_count": updated_count,
                "notes": [str(note_id) for note_id in updated_ids]
            })
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BulkNoteDeleteView(APIView):
    """View for permanently deleting multiple notes at once."""
    
    def post(self, request, format=None):
        """
        Permanently delete multiple notes from the database.
        
        Expected payload:
        {
            "note_ids": ["uuid1", "uuid2", "uuid3", ...]
        }
        
        Returns:
        {
            "status": "success",
            "deleted_count": number of notes deleted,
            "notes": [list of deleted note ids]
        }
        """
        try:
            # Validate input
            note_ids = request.data.get('note_ids', [])
            
            if not note_ids or not isinstance(note_ids, list):
                return Response(
                    {"error": "note_ids must be a non-empty list"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get notes to delete
            notes_to_delete = Note.objects.filter(id__in=note_ids)
            delete_count = notes_to_delete.count()
            
            # Get IDs before deletion for response
            deleted_ids = list(notes_to_delete.values_list('id', flat=True))
            
            # Perform bulk deletion
            notes_to_delete.delete()
            
            return Response({
                "status": "success",
                "deleted_count": delete_count,
                "notes": [str(note_id) for note_id in deleted_ids]
            })
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidatePdfUrlView(APIView):
    """View for validating PDF URLs with content verification and title extraction."""
    
    def post(self, request, format=None):
        """Validate if a URL points to a downloadable PDF and extract title if possible."""
        debug_print("ValidatePdfUrlView.post called")
        
        url = request.data.get('url')
        debug_print(f"Request data: {request.data}")
        debug_print(f"URL to validate: {url}")
        
        if not url:
            debug_print("Error: URL is required")
            return Response({'isValid': False, 'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate URL format
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return Response({'isValid': False, 'error': 'Invalid URL format'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Debug specific arXiv paper issue
            if '1802.04406' in url:
                debug_print(f"*** SPECIAL DEBUG FOR SPECIFIC ARXIV PAPER: {url} ***")
                # Try direct API call
                debug_arxiv_id = '1802.04406'
                debug_api_url = f"https://export.arxiv.org/api/query?id_list={debug_arxiv_id}"
                try:
                    debug_response = requests.get(debug_api_url, timeout=15)
                    debug_print(f"Direct arXiv API call status: {debug_response.status_code}")
                    debug_print(f"Direct arXiv API response first 500 chars: {debug_response.text[:500]}")
                    
                    # Try title extraction
                    debug_title_match = re.search(r'<title>(.*?)</title>', debug_response.text)
                    if debug_title_match:
                        debug_title = debug_title_match.group(1)
                        debug_print(f"Debug title match: {debug_title}")
                    else:
                        debug_print("No title match found in direct API call")
                        
                    # See if we need to look for a different title tag format
                    alternative_tags = ['<dc:title>', '<arxiv:title>']
                    for tag in alternative_tags:
                        open_tag = tag
                        close_tag = tag.replace('<', '</')
                        if open_tag in debug_response.text:
                            debug_print(f"Found alternative tag: {open_tag}")
                            alt_match = re.search(f"{re.escape(open_tag)}(.*?){re.escape(close_tag)}", debug_response.text)
                            if alt_match:
                                debug_print(f"Alternative title match: {alt_match.group(1)}")
                except Exception as debug_e:
                    debug_print(f"Error in direct API debug: {debug_e}")
            
            # Normalize URL (e.g., convert arXiv abstract URLs to PDF URLs)
            url = self._normalize_url(url)
            
            # Special handling for arXiv URLs
            if 'arxiv.org' in url:
                arxiv_match = re.search(r'arxiv\.org\/(?:pdf|abs)\/(\d+\.\d+)', url, re.IGNORECASE)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
                    debug_print(f"Found arXiv ID: {arxiv_id}, validating via arXiv API")
                    return self._validate_arxiv_paper(arxiv_id)
            
            # Set up headers for requests
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool)',
                'Accept': 'application/pdf'
            }
            
            try:
                # Step 1: HEAD request to check accessibility, content-type and size
                debug_print(f"Making HEAD request to {url}")
                head_response = requests.head(url, headers=headers, timeout=10)
                
                if not head_response.ok:
                    return Response({
                        'isValid': False, 
                        'error': f'URL is not accessible (Status: {head_response.status_code})'
                    })
                
                # Check content type (but be lenient)
                content_type = head_response.headers.get('Content-Type', '')
                is_pdf = 'application/pdf' in content_type.lower()
                url_ends_with_pdf = url.lower().endswith('.pdf')
                
                # Check file size
                content_length = head_response.headers.get('Content-Length')
                max_size = 50 * 1024 * 1024  # 50 MB
                if content_length and int(content_length) > max_size:
                    return Response({
                        'isValid': False,
                        'error': f'File too large: {int(content_length) / (1024*1024):.2f} MB (max 50 MB)'
                    })
                
                # If neither content type nor URL suggests PDF but URL contains "pdf"
                if not is_pdf and not url_ends_with_pdf and 'pdf' not in url.lower():
                    debug_print(f"URL does not appear to be a PDF: {url} (Content-Type: {content_type})")
                    return Response({
                        'isValid': False,
                        'error': f'URL does not appear to be a PDF (Content-Type: {content_type})'
                    })
                
                # Step 2: Verify PDF is downloadable by checking signature
                is_downloadable, error_msg = self._verify_pdf_downloadable(url, headers)
                
                if not is_downloadable:
                    return Response({
                        'isValid': False,
                        'error': error_msg or 'PDF content could not be downloaded'
                    })
                
                # Step 3: Try to extract title from PDF content (if possible)
                title = None
                pdf_title_extraction_failed = False
                
                try:
                    title = self._extract_title_from_pdf(url, headers)
                except Exception as e:
                    debug_print(f"Error extracting title from PDF: {str(e)}")
                    pdf_title_extraction_failed = True
                
                # Step 4: Fall back to URL-based title extraction if PDF extraction failed
                if not title or pdf_title_extraction_failed:
                    debug_print("Falling back to URL-based title extraction")
                    title = self._extract_title_from_url(url)
                
                result = {
                    'isValid': True,
                    'url': url,
                    'title': title or url[:200],  # Ensure we always have a title, fallback to URL
                    'contentType': content_type,
                    'contentLength': content_length
                }
                debug_print(f"Validation successful, returning: {result}")
                return Response(result)
                    
            except requests.exceptions.Timeout:
                return Response({
                    'isValid': False,
                    'error': 'Timeout when validating URL'
                })
            except requests.exceptions.RequestException as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error validating URL {url}: {str(e)}")
                return Response({
                    'isValid': False,
                    'error': 'Network error when validating URL'
                })
                
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in validate_pdf_url: {str(e)}")
            return Response({
                'isValid': False,
                'error': 'Server error when validating URL'
            })
    
    def _verify_pdf_downloadable(self, url, headers):
        """Verify PDF is downloadable by fetching a small portion of content."""
        debug_print(f"Verifying PDF is downloadable: {url}")
        try:
            # Add Range header to request only the first 1KB of the file
            range_headers = headers.copy()
            range_headers['Range'] = 'bytes=0-1023'
            
            # Try partial content request first
            response = requests.get(url, headers=range_headers, timeout=10)
            
            # Check if server supports partial content requests
            if response.status_code == 206:
                debug_print("Server supports range requests - checking PDF signature in partial content")
                # Successful partial content response
                # Check for PDF signature at the beginning of content
                if response.content.startswith(b'%PDF-'):
                    return True, None
                else:
                    debug_print("Content does not have PDF signature")
                    return False, 'Content does not appear to be a PDF'
            
            # If server doesn't support range requests, we got full response
            # Just check the beginning of the content
            elif response.status_code == 200:
                debug_print("Server doesn't support range requests - checking first bytes of full response")
                # Only check the first few bytes
                if len(response.content) > 0 and response.content[:10].startswith(b'%PDF-'):
                    return True, None
                else:
                    debug_print("Content does not have PDF signature")
                    return False, 'Content does not appear to be a PDF'
            
            # Other error status codes
            else:
                debug_print(f"Download verification failed with status: {response.status_code}")
                return False, f'Failed to download content (Status: {response.status_code})'
                
        except requests.exceptions.Timeout:
            debug_print("Timeout during download verification")
            return False, 'Timeout when downloading PDF content'
        except requests.exceptions.RequestException as e:
            debug_print(f"Network error during download verification: {str(e)}")
            return False, f'Network error: {str(e)}'
        except Exception as e:
            debug_print(f"Unexpected error during download verification: {str(e)}")
            return False, f'Error verifying PDF content: {str(e)}'
    
    def _extract_title_from_pdf(self, url, headers):
        """Extract title from PDF content."""
        debug_print(f"Attempting to extract title from PDF content: {url}")
        
        try:
            # Get first 5KB of the PDF - enough for metadata and usually first page header
            # Reduced from 10KB to 5KB for better performance and memory usage
            range_headers = headers.copy()
            range_headers['Range'] = 'bytes=0-4999'  # First 5KB
            
            response = requests.get(url, headers=range_headers, timeout=15)
            
            # If range request succeeded or we got a full response
            if response.status_code in [200, 206] and len(response.content) > 0:
                # Create a file-like object from the content
                pdf_bytes = io.BytesIO(response.content)
                
                try:
                    # Try to open as a PDF with a processing timeout
                    import signal
                    
                    class PDFProcessingTimeout(Exception):
                        pass
                    
                    def timeout_handler(signum, frame):
                        raise PDFProcessingTimeout("PDF processing timed out")
                    
                    # Set a 5-second timeout for PDF processing
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(5)
                    
                    try:
                        pdf_reader = PyPDF2.PdfReader(pdf_bytes)
                        
                        # Try to get title from document info
                        if pdf_reader.metadata:
                            # First try the standard title field
                            if hasattr(pdf_reader.metadata, 'title') and pdf_reader.metadata.title:
                                title = pdf_reader.metadata.title
                                if title and len(title.strip()) > 0:
                                    debug_print(f"Extracted title from PDF metadata: {title}")
                                    # Cancel the alarm
                                    signal.alarm(0)
                                    return title.strip()
                            
                            # Try a few other common title fields
                            for field in ['Title', 'Subject', 'dc:title']:
                                try:
                                    if hasattr(pdf_reader.metadata, field) and getattr(pdf_reader.metadata, field):
                                        title = getattr(pdf_reader.metadata, field)
                                        if title and len(str(title).strip()) > 0:
                                            debug_print(f"Extracted title from PDF metadata field '{field}': {title}")
                                            # Cancel the alarm
                                            signal.alarm(0)
                                            return str(title).strip()
                                except:
                                    # Skip if field access fails
                                    pass
                        
                        # If no title in metadata, try to extract from first page text
                        if len(pdf_reader.pages) > 0:
                            first_page_text = pdf_reader.pages[0].extract_text()
                            if first_page_text:
                                # Take first non-empty line as title
                                lines = first_page_text.split('\n')
                                for line in lines:
                                    if line.strip():
                                        # Limit title length
                                        title = line.strip()[:100]
                                        debug_print(f"Extracted title from first page text: {title}")
                                        # Cancel the alarm
                                        signal.alarm(0)
                                        return title
                    finally:
                        # Cancel the alarm in case we're exiting normally
                        signal.alarm(0)
                except PDFProcessingTimeout as e:
                    debug_print(f"PDF processing timed out: {str(e)}")
                    debug_print("Falling back to URL-based title extraction")
                    return None
                except Exception as e:
                    debug_print(f"Error processing PDF content: {str(e)}")
                    raise
        except Exception as e:
            debug_print(f"Error extracting title from PDF: {str(e)}")
            raise
        
        # If we got here, we couldn't extract a title
        return None
    
    def _normalize_url(self, url):
        """Normalize URL for better validation."""
        # Convert arXiv abstract URLs to PDF URLs
        if "/abs/" in url and "arxiv.org" in url:
            url = url.replace("/abs/", "/pdf/")
            if not url.endswith('.pdf'):
                url = url + '.pdf'
        return url
    
    def _validate_arxiv_paper(self, arxiv_id):
        """Validate arXiv paper existence using the arXiv API."""
        debug_print(f"Validating arXiv paper: {arxiv_id}")
        try:
            # First verify the paper exists in ArXiv database
            url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
            debug_print(f"Making arXiv API request to: {url}")
            response = requests.get(url, timeout=10)
            
            debug_print(f"arXiv API response status: {response.status_code}")
            
            if response.status_code != 200:
                debug_print(f"arXiv API error: {response.status_code}")
                return Response({
                    'isValid': False,
                    'error': f'ArXiv API error: {response.status_code}'
                })
            
            content = response.text
            debug_print(f"arXiv API response length: {len(content)} chars")
            
            # Check if paper exists
            if '<entry>' not in content:
                debug_print("arXiv API response missing <entry> tag")
                return Response({
                    'isValid': False,
                    'error': 'ArXiv paper not found'
                })
            
            # Extract title - print the relevant portion of XML to debug
            title_tag_position = content.find('<title>')
            if title_tag_position >= 0:
                snippet = content[title_tag_position:title_tag_position+200]
                debug_print(f"Title tag found, snippet: {snippet}")
            else:
                debug_print("No <title> tag found in arXiv API response")
                
            # Try different title tag patterns - focusing on title INSIDE the entry tag
            title = None
            
            # Extract entry content first - this is critical
            entry_match = re.search(r'<entry>([\s\S]*?)</entry>', content)
            if entry_match:
                entry_content = entry_match.group(1)
                debug_print(f"Found entry content, now looking for title inside entry")
                
                # Look for title inside the entry content
                title_match = re.search(r'<title>(.*?)</title>', entry_content)
                if title_match:
                    raw_title = title_match.group(1)
                    debug_print(f"Title found inside entry: {raw_title}")
                    
                    # Clean up title
                    title = raw_title.strip()
                    debug_print(f"Cleaned title: {title}")
            else:
                debug_print("No <entry> tag content could be extracted")
            
            # Verify that the PDF is actually downloadable
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool)',
                'Accept': 'application/pdf'
            }
            
            # Verify PDF is downloadable
            is_downloadable, error_msg = self._verify_pdf_downloadable(pdf_url, headers)
            
            if not is_downloadable:
                debug_print(f"arXiv PDF is not downloadable: {error_msg}")
                return Response({
                    'isValid': False,
                    'error': error_msg or 'ArXiv PDF is not downloadable'
                })
            
            # Special handling for problematic arXiv paper
            if arxiv_id == '1802.04406':
                debug_print("Detected problematic arXiv ID, adding extra debugging")
                # Try direct access to arXiv.org website as alternative
                try:
                    debug_print("Trying to scrape arXiv abstract page as fallback")
                    abstract_url = f"https://arxiv.org/abs/{arxiv_id}"
                    abs_response = requests.get(abstract_url, timeout=15)
                    debug_print(f"Abstract page status: {abs_response.status_code}")
                    if abs_response.ok:
                        # Look for title in HTML
                        html_title_match = re.search(r'<h1 class="title[^"]*">[^<]*<span class="descriptor">Title:</span>\s*(.*?)\s*</h1>', 
                                                   abs_response.text)
                        if html_title_match:
                            title = html_title_match.group(1).strip()
                            debug_print(f"Title extracted from HTML: {title}")
                        else:
                            debug_print("No title found in HTML")
                            # Just print a chunk of the HTML to see what we're dealing with
                            title_section = abs_response.text.find('class="title')
                            if title_section > -1:
                                debug_print(f"Title section in HTML (300 chars): {abs_response.text[title_section:title_section+300]}")
                except Exception as scrape_e:
                    debug_print(f"Error scraping abstract page: {scrape_e}")
            
            # Determine final title with fallbacks
            final_title = title or f'ArXiv: {arxiv_id}' or pdf_url[:200]
            debug_print(f"Final title being returned: '{final_title}'")
            
            # Prepare response
            response_data = {
                'isValid': True,
                'title': final_title,
                'url': pdf_url
            }
            debug_print(f"Final response data: {response_data}")
            
            return Response(response_data)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error validating ArXiv paper {arxiv_id}: {str(e)}")
            debug_print(f"Exception in arXiv validation: {str(e)}")
            traceback_info = traceback.format_exc()
            debug_print(f"Traceback: {traceback_info}")
            return Response({
                'isValid': False,
                'error': f'Error validating ArXiv paper: {str(e)}'
            })
    
    def _extract_title_from_url(self, url):
        """Extract a human-readable title from a URL."""
        debug_print(f"Extracting title from URL: {url}")
        try:
            # Get the last part of the path
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            filename = path_parts[-1] if path_parts else ''
            
            if filename:
                # Clean up filename
                title = (
                    filename
                    .replace('.pdf', '')
                    .replace('-', ' ')
                    .replace('_', ' ')
                    .strip()
                )
                if title:
                    debug_print(f"Extracted title from URL filename: {title}")
                    return title
            
            # Fallback to domain
            title = f"PDF from {parsed.netloc}"
            debug_print(f"Using domain fallback for title: {title}")
            return title
        except:
            # Ultimate fallback - truncate full URL to 200 chars
            truncated_url = url[:200]
            debug_print(f"Using full URL as title (truncated): {truncated_url}")
            return truncated_url




class HealthCheckView(View):
    """Health check endpoint for Railway monitoring."""
    
    def get(self, request):
        """Return health status of the application."""
        return JsonResponse({
            'status': 'healthy',
            'message': 'Research Assistant Backend is running',
            'timestamp': str(timezone.now()) if 'timezone' in globals() else 'N/A'
        })
