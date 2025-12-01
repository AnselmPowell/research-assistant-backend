"""
Serializers for the core application.
"""

from rest_framework import serializers
from .models import ResearchSession, Paper, Note, Project, Section, Group

class NoteSerializer(serializers.ModelSerializer):
    """Serializer for Note model."""
    class Meta:
        model = Note
        fields = '__all__'
        
    def to_representation(self, instance):
        """Convert to the format expected by the frontend."""
        return instance.to_frontend_format()

class PaperSerializer(serializers.ModelSerializer):
    """Serializer for Paper model."""
    notes = NoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Paper
        fields = '__all__'

class ResearchSessionSerializer(serializers.ModelSerializer):
    """Serializer for ResearchSession model."""
    papers = PaperSerializer(many=True, read_only=True)
    
    class Meta:
        model = ResearchSession
        fields = '__all__'

class ResearchRequestSerializer(serializers.Serializer):
    """Serializer for research requests."""
    sessionId = serializers.UUIDField(required=False, allow_null=True)
    query = serializers.DictField(required=True)
    
    def validate_query(self, value):
        """Validate the query field."""
        required_fields = ['topics', 'infoQueries']
        for field in required_fields:
            if field not in value:
                value[field] = []
        
        if 'urls' not in value:
            value['urls'] = []
            
        if 'context' not in value:
            value['context'] = ""
            
        if 'settings' not in value:
            value['settings'] = {}
            
        return value
        
        
class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model."""
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_at', 'modified_at']
    
    def to_representation(self, instance):
        return instance.to_dict()


class SectionSerializer(serializers.ModelSerializer):
    """Serializer for Section model."""
    class Meta:
        model = Section
        fields = ['id', 'project', 'name', 'order', 'created_at']
    
    def to_representation(self, instance):
        return instance.to_dict()


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Group model."""
    class Meta:
        model = Group
        fields = ['id', 'name', 'section', 'project', 'order', 'created_at']
    
    def to_representation(self, instance):
        return instance.to_dict()


class NoteOrganizationSerializer(serializers.Serializer):
    """Serializer for updating note organization."""
    projects = serializers.ListField(
        child=serializers.CharField(allow_null=True),
        required=True,
        allow_empty=True
    )
    sections = serializers.ListField(
        child=serializers.CharField(allow_null=True),
        required=True,
        allow_empty=True
    )
    groups = serializers.ListField(
        child=serializers.CharField(allow_null=True),
        required=True,
        allow_empty=True
    )
    
    def validate_projects(self, value):
        """Ensure projects is always a list, even if empty."""
        return value if value is not None else []
        
    def validate_sections(self, value):
        """Ensure sections is always a list, even if empty."""
        return value if value is not None else []
        
    def validate_groups(self, value):
        """Ensure groups is always a list, even if empty."""
        return value if value is not None else []
