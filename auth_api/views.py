# src/auth_api/views.py

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model
User = get_user_model()




from .models import UserProfile, UserSession
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    SocialAuthSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TokenRefreshSerializer,
    TokenResponseSerializer
)
from .authentication import TokenManager
from .utils import check_login_attempts, log_login_attempt, get_client_ip


class CSRFTokenView(APIView):
    """Get CSRF token"""
    permission_classes = [AllowAny]

    def get(self, request):
        print("\n=== [CSRFTokenView] START ===")
        print("[CSRFTokenView] Method: GET")
        token = get_token(request)
        print(f"[CSRFTokenView] Token generated: {'YES' if token else 'NO'}")
        print("=== [CSRFTokenView] END ===\n")
        return JsonResponse({'csrfToken': token})


class RegistrationView(APIView):
    """Handle user registration"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("\n" + "="*60)
        print("=== [RegistrationView] START ===")
        print("="*60)
        print(f"[RegistrationView] Request method: {request.method}")
        print(f"[RegistrationView] Request data keys: {list(request.data.keys())}")
        print(f"[RegistrationView] Email: {request.data.get('email', 'N/A')}")
        print(f"[RegistrationView] First name: {request.data.get('first_name', 'N/A')}")
        print(f"[RegistrationView] Last name: {request.data.get('last_name', 'N/A')}")
        
        print("\n[RegistrationView] Validating with serializer...")
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            print("[RegistrationView] Serializer validation FAILED")
            print(f"[RegistrationView] Errors: {serializer.errors}")
            print("="*60 + "\n")
            return Response({
                'status': 'error',
                'message': 'Invalid registration details',
                'detail': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print("[RegistrationView] Serializer validation SUCCESS")
       
        print("\n[RegistrationView] Creating user...")
        user = serializer.save()
        print(f"[RegistrationView] User created - ID: {user.id}, Email: {user.email}")
        
        print("\n[RegistrationView] Generating tokens...")
        access_token, refresh_token = TokenManager.generate_tokens(user.id)
        print(f"[RegistrationView] Access token length: {len(access_token)}")
        print(f"[RegistrationView] Refresh token length: {len(refresh_token)}")
        
        print("\n[RegistrationView] Creating user session...")
        ip_address = get_client_ip(request)
        print(f"[RegistrationView] Client IP: {ip_address}")
        UserSession.objects.create(
            user=user,
            session_token=access_token,
            refresh_token=refresh_token,
            device_info=request.META.get('HTTP_USER_AGENT'),
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(days=7)
        )
        print("[RegistrationView] User session created")
        
        # Create the profile data first
        profile_data = UserProfileSerializer(user.profile).data
        print("[RegistrationView] Profile data prepared:", profile_data.get('email'))
        
        # Then create the response data
        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': profile_data
        }
        
        print("\n" + "="*60)
        print("=== [RegistrationView] END - SUCCESS ===")
        print("="*60 + "\n")
        return Response(response_data, status=status.HTTP_201_CREATED)
        
        # except Exception as e:
        #     print("=== Error During Registration ===")
        #     print("Error:", str(e))
        #     return Response(
        #         {'error': 'Registration failed', 'detail': str(e)},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )


class LoginView(APIView):
    """Handle user login"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("\n" + "="*60)
        print("=== [LoginView] START ===")
        print("="*60)
        print(f"[LoginView] Request method: {request.method}")
        print(f"[LoginView] Email: {request.data.get('email', 'N/A')}")
        
        print("\n[LoginView] Validating credentials...")
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            print("[LoginView] Serializer validation FAILED")
            print(f"[LoginView] Errors: {serializer.errors}")
            print("="*60 + "\n")
            return Response({
                'status': 'error',
                'message': 'Invalid credentials',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        ip_address = get_client_ip(request)
        
        print(f"[LoginView] Client IP: {ip_address}")

        # CHECK RATE LIMITING FIRST (before any authentication attempts)
        print("\n[LoginView] Checking rate limiting...")
        if not check_login_attempts(email, ip_address):
            print("[LoginView] Rate limit EXCEEDED")
            print("="*60 + "\n")
            return Response({
                'status': 'error',
                'message': 'Too many login attempts',
                'detail': 'Please wait 15 minutes before trying again'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        print("[LoginView] Rate limit OK")

        # Check if user exists
        print("\n[LoginView] Looking up user by email...")
        try:
            user = User.objects.get(email=email)
            print(f"[LoginView] User found - ID: {user.id}, Email: {user.email}")
            
            # If user exists but is a social account
            if hasattr(user, 'profile') and user.profile.is_social_account:
                print(f"[LoginView] User is social account: {user.profile.social_provider}")
                log_login_attempt(email, ip_address, False)
                print("="*60 + "\n")
                return Response({
                    'status': 'error',
                    'code': 'social_account',
                    'message': f'Please use {user.profile.social_provider} login for this account'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Attempt authentication
            print("\n[LoginView] Authenticating password...")
            authenticated_user = authenticate(username=email, password=password)
            if not authenticated_user:
                # User exists but password is wrong
                print("[LoginView] Password authentication FAILED")
                log_login_attempt(email, ip_address, False)
                print("="*60 + "\n")
                return Response({
                    'status': 'error',
                    'code': 'invalid_password',
                    'message': 'Password is incorrect, please try again'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            print("[LoginView] Password authentication SUCCESS")
            # Authentication successful
            user = authenticated_user

        except User.DoesNotExist:
            # No user found with this email
            print("[LoginView] User NOT FOUND")
            log_login_attempt(email, ip_address, False)
            print("="*60 + "\n")
            return Response({
                'status': 'error',
                'code': 'user_not_found',
                'message': 'No account found with this email'
            }, status=status.HTTP_404_NOT_FOUND)

        # Log successful attempt
        print("\n[LoginView] Logging successful attempt...")
        log_login_attempt(email, ip_address, True)
        
        # Generate tokens
        print("[LoginView] Generating tokens...")
        access_token, refresh_token = TokenManager.generate_tokens(user.id)
        print(f"[LoginView] Access token length: {len(access_token)}")
        print(f"[LoginView] Refresh token length: {len(refresh_token)}")
        
        # Create or update session
        print("[LoginView] Creating user session...")
        UserSession.objects.create(
            user=user,
            session_token=access_token,
            refresh_token=refresh_token,
            device_info=request.META.get('HTTP_USER_AGENT'),
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(days=7)
        )
        print("[LoginView] User session created")
        
        # Update user profile
        print("\n[LoginView] Updating user profile...")
        profile = user.profile
        profile.last_login = timezone.now()
        profile.last_login_ip = ip_address
        profile.login_count += 1
        profile.save()
        print(f"[LoginView] Profile updated - Login count: {profile.login_count}")

        profile_data = UserProfileSerializer(profile).data
        print(f"[LoginView] Profile data prepared: {profile_data.get('email')}")
        
        print("\n" + "="*60)
        print("=== [LoginView] END - SUCCESS ===")
        print("="*60 + "\n")
        
        # Return response directly without TokenResponseSerializer
        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': profile_data
        })

        # return Response(TokenResponseSerializer(response_data).data)


class SocialAuthView(APIView):
    """Handle social authentication"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("\n" + "="*60)
        print("=== [SocialAuthView] START ===")
        print("="*60)
        print(f"[SocialAuthView] Request method: {request.method}")
        print(f"[SocialAuthView] Request data keys: {list(request.data.keys())}")
        print(f"[SocialAuthView] Email: {request.data.get('email', 'N/A')}")
        print(f"[SocialAuthView] Provider: {request.data.get('provider', 'N/A')}")
        print(f"[SocialAuthView] Name: {request.data.get('first_name', 'N/A')} {request.data.get('last_name', 'N/A')}")
        
        print("\n[SocialAuthView] Validating with serializer...")
        serializer = SocialAuthSerializer(data=request.data)
        if not serializer.is_valid():
            print("[SocialAuthView] Serializer validation FAILED")
            print(f"[SocialAuthView] Errors: {serializer.errors}")
            print("="*60 + "\n")
            return Response({
                'status': 'error',
                'message': 'Invalid social auth details',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        print("[SocialAuthView] Serializer validation SUCCESS")
        
        try:
            # Try to find existing user
            print("\n[SocialAuthView] Looking up existing user...")
            user = User.objects.filter(email=data['email']).first()
            
            if not user:
                # Create new user for social login
                print(f"[SocialAuthView] User NOT FOUND - Creating new user...")
                user = User.objects.create(
                    username=data['email'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    is_active=True
                )
                print(f"[SocialAuthView] User created - ID: {user.id}")

                print("[SocialAuthView] Setting unusable password for social account...")
                user.set_unusable_password()
                user.save()
                
                # Create/update profile
                print("[SocialAuthView] Creating/updating profile...")
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.is_social_account = True
                profile.social_provider = data['provider']
                profile.first_name = data['first_name']
                profile.last_name = data['last_name']
                profile.email = data['email']
                profile.is_email_verified = True
                profile.save()
                print(f"[SocialAuthView] Profile {'created' if created else 'updated'}")
            else:
                print(f"[SocialAuthView] User FOUND - ID: {user.id}, Email: {user.email}")
            
            # Generate tokens
            print("\n[SocialAuthView] Generating tokens...")
            access_token, refresh_token = TokenManager.generate_tokens(user.id)
            print(f"[SocialAuthView] Tokens generated - Access: {len(access_token)}, Refresh: {len(refresh_token)}")
            
            # Create session
            print("[SocialAuthView] Creating user session...")
            ip_address = get_client_ip(request)
            UserSession.objects.create(
                user=user,
                session_token=access_token,
                refresh_token=refresh_token,
                device_info=request.META.get('HTTP_USER_AGENT'),
                ip_address=ip_address,
                expires_at=timezone.now() + timedelta(days=7)
            )
            print(f"[SocialAuthView] Session created - IP: {ip_address}")
            
            # Get profile data
            print("\n[SocialAuthView] Preparing profile data...")
            profile_data = UserProfileSerializer(user.profile).data
            print(f"[SocialAuthView] Profile data prepared: {profile_data.get('email')}")
            
            response_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user': profile_data
            }
            
            print("\n" + "="*60)
            print("=== [SocialAuthView] END - SUCCESS ===")
            print("="*60 + "\n")
            
            return Response(response_data)
            
        except Exception as e:
            print("\n" + "="*60)
            print("=== [SocialAuthView] ERROR ===")
            print(f"[SocialAuthView] Exception: {str(e)}")
            print(f"[SocialAuthView] Exception type: {type(e).__name__}")
            print("="*60 + "\n")
            
            return Response({
                'status': 'error',
                'message': 'Authentication failed',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# auth_api/views.py
class LogoutView(APIView):
    """Handle user logout"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("\n=== LOGOUT VIEW ===")
        print("Request User:", request.user)
        print("Request Auth:", request.auth)
        
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                print("ERROR: No Authorization header provided")
                return Response(
                    {'error': 'Authorization header required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print("Auth Header:", auth_header)

            # Extract token
            parts = auth_header.split()
            if len(parts) != 2:
                print("ERROR: Malformed Authorization header")
                return Response(
                    {'error': 'Malformed Authorization header'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token_type, token = parts
            print("Token Type:", token_type)
            print("Token:", token[:20] + "..." if len(token) > 20 else token)

            # Find and invalidate sessions
            sessions = UserSession.objects.filter(
                user=request.user,
                session_token=token,
                is_active=True
            )
            print("Found Active Sessions:", sessions.count())
            
            # Update sessions
            updated_count = sessions.update(is_active=False)
            print("Updated Sessions Count:", updated_count)
            
            print("=== LOGOUT COMPLETE ===\n")
            
            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            print(f"ERROR during logout: {str(e)}")
            return Response(
                {'error': 'Logout failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TokenRefreshView(APIView):
    """Handle token refresh"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        refresh_token = serializer.validated_data['refresh_token']

        try:
            # Validate refresh token
            payload = TokenManager.validate_token(refresh_token, 'refresh')
            user_id = payload['user_id']

            # Generate new tokens
            access_token, new_refresh_token = TokenManager.generate_tokens(user_id)

            # Update session
            session = UserSession.objects.get(
                user_id=user_id,
                refresh_token=refresh_token,
                is_active=True
            )
            session.refresh_token = new_refresh_token
            session.save()

            return Response({
                'access_token': access_token,
                'refresh_token': new_refresh_token,
                'token_type': 'Bearer',
                'expires_in': 3600
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

class UserProfileView(APIView):
    """Get user profile information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        print(f"[UserProfileView] Fetching profile for user: {request.user.email}")
        
        try:
            # Import ResearchSession and Note models
            from core.models import ResearchSession, Note
            
            # Get counts of user's data
            session_count = ResearchSession.objects.filter(user=request.user).count()
            # Count notes through the relationship: Note -> Paper -> Session -> User
            note_count = Note.objects.filter(paper__session__user=request.user, status='kept').count()
            
            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'stats': {
                    'session_count': session_count,
                    'note_count': note_count,
                    'last_login': request.user.profile.last_login.isoformat() if request.user.profile.last_login else None,
                    'account_created': request.user.profile.account_created.isoformat(),
                    'login_count': request.user.profile.login_count,
                }
            }
            
            print(f"[UserProfileView] Profile data: {user_data}")
            return Response(user_data)
            
        except Exception as e:
            print(f"[UserProfileView] Error: {str(e)}")
            return Response(
                {'error': 'Failed to fetch user profile', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordChangeView(APIView):
    """Handle password change"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Verify old password
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({'message': 'Password updated successfully'})