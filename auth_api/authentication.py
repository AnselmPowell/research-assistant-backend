# auth_api/authentication.py

import jwt as PyJWT
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication, exceptions
from .models import UserSession


class TokenManager:
    """
    Handles JWT token generation and validation.
    Manages both access tokens and refresh tokens.
    """
    
    @staticmethod
    def generate_tokens(user_id: int) -> tuple[str, str]:
        """
        Generate access and refresh tokens for a user.
        
        Args:
            user_id: The ID of the user to generate tokens for
            
        Returns:
            tuple: (access_token, refresh_token)
        """
        print(f"\n[TokenManager] Generating tokens for user ID: {user_id}")
        
        # Access token - short lived
        access_payload = {
            'user_id': user_id,
            'type': 'access',
            'exp': datetime.utcnow() + settings.JWT_SETTINGS['ACCESS_TOKEN_LIFETIME'],
            'iat': datetime.utcnow()
        }
        print(f"[TokenManager] Access token payload: user_id={user_id}, type=access")
        
        access_token = PyJWT.encode(
            access_payload,
            settings.JWT_SETTINGS['SIGNING_KEY'],
            algorithm=settings.JWT_SETTINGS['ALGORITHM']
        )
        print(f"[TokenManager] Access token generated - Length: {len(access_token)}")

        # Refresh token - long lived
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': datetime.utcnow() + settings.JWT_SETTINGS['REFRESH_TOKEN_LIFETIME'],
            'iat': datetime.utcnow()
        }
        print(f"[TokenManager] Refresh token payload: user_id={user_id}, type=refresh")
        
        refresh_token = PyJWT.encode(
            refresh_payload,
            settings.JWT_SETTINGS['SIGNING_KEY'],
            algorithm=settings.JWT_SETTINGS['ALGORITHM']
        )
        print(f"[TokenManager] Refresh token generated - Length: {len(refresh_token)}\n")

        return access_token, refresh_token

    @staticmethod
    def validate_token(token: str, token_type: str = 'access') -> dict:
        """
        Validate JWT token and return payload.
        
        Args:
            token: The JWT token to validate
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            dict: Token payload if valid
            
        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        try:
            payload = PyJWT.decode(
                token,
                settings.JWT_SETTINGS['SIGNING_KEY'],
                algorithms=[settings.JWT_SETTINGS['ALGORITHM']]
            )

            # Verify token type matches expected type
            if payload.get('type') != token_type:
                raise exceptions.AuthenticationFailed('Invalid token type')

            return payload
            
        except PyJWT.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except PyJWT.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication for Django REST Framework.
    Validates JWT tokens and checks session validity.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using JWT token.
        
        Args:
            request: The HTTP request
            
        Returns:
            tuple: (user, token) if authentication successful, None otherwise
        """
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        try:
            # Parse header: "Bearer <token>"
            header_parts = auth_header.split()
            if len(header_parts) != 2 or header_parts[0].lower() != 'bearer':
                raise exceptions.AuthenticationFailed('Invalid token header format')

            token = header_parts[1]

            # Validate token and extract payload
            payload = TokenManager.validate_token(token)
            
            # Get user from token payload
            try:
                user = User.objects.get(id=payload['user_id'])
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')

            # Check if user is active
            if not user.is_active:
                raise exceptions.AuthenticationFailed('User account is disabled')

            # Check if session is valid
            session = UserSession.objects.filter(
                user=user,
                session_token=token,
                is_active=True,
                expires_at__gt=datetime.now()
            ).first()

            if not session:
                raise exceptions.AuthenticationFailed('Invalid or expired session')

            return (user, token)

        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentication failed: {str(e)}')

    def authenticate_header(self, request):
        """
        Return string to be used as the value of the WWW-Authenticate header.
        """
        return 'Bearer realm="api"'
