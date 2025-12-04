"""
Serializers for authentication API.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'first_name', 'last_name')
    
    def validate(self, attrs):
        """Validate registration data."""
        # Check password match
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError({
                "password": "Password fields do not match."
            })
        
        # Check email uniqueness
        email = attrs.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": "User with this email already exists."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create user with email as username."""
        email = validated_data['email']
        print("[UserRegistrationSerializer] Creating user:", email)
        
        # Create user with email as username
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        print(f"[UserRegistrationSerializer] User created - ID: {user.id}")
        
        # Profile is automatically created via signal
        # Update profile fields
        print("[UserRegistrationSerializer] Updating profile...")
        user.profile.email = email
        user.profile.first_name = validated_data['first_name']
        user.profile.last_name = validated_data['last_name']
        user.profile.save()
        print("[UserRegistrationSerializer] Profile updated\n")
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('email', 'first_name', 'last_name', 'last_login', 'account_created')
        read_only_fields = ('last_login', 'account_created')
    
    def to_representation(self, instance):
        """Customize output format."""
        data = super().to_representation(instance)
        return data


class SocialAuthSerializer(serializers.Serializer):
    """Serializer for social authentication."""
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    provider = serializers.ChoiceField(choices=['google', 'microsoft'], required=True)
    
    def validate_email(self, value):
        """Validate email format."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value.lower()


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh."""
    refresh_token = serializers.CharField(required=True)


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    user = UserProfileSerializer()


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate password match."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate password match."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        return attrs



