from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import get_user_model, authenticate
from .serializers import (
    UserSerializer,
    ProfileSerializer,
    UserActivitySerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
)
from .models import Profile, UserActivity
from .permissions import IsAdmin, IsRegisteredUser, IsOwnerOrAdmin
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

User = get_user_model()

# Create your views here.

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        print('Registration data received:', request.data)  # Debug print
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access = AccessToken.for_user(user)
            
            # Log the registration
            UserActivity.objects.create(
                user=user,
                activity_type=UserActivity.ActivityType.REGISTRATION,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'token': str(access),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        print('Validation errors:', serializer.errors)  # Debug print
        return Response({
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        print('Login data received:', request.data)  # Debug print
        
        # Get and validate email
        email = request.data.get('email')
        if not email:
            return Response({
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        password = request.data.get('password')
        if not password:
            return Response({
                'message': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
            if not user.check_password(password):
                return Response({
                    'message': 'Invalid password'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access = AccessToken.for_user(user)

            # Log the login activity
            UserActivity.objects.create(
                user=user,
                activity_type=UserActivity.ActivityType.LOGIN,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({
                'token': str(access),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })

        except User.DoesNotExist:
            print('Login error: No active account found with the given credentials')
            return Response({
                'message': 'No active account found with the given credentials'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Login error:', str(e))
            return Response({
                'message': 'An error occurred during login'
            }, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({
                    'message': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            # Add the token to the blacklist
            token.blacklist()
            
            # Log the logout activity if user is authenticated
            if request.user.is_authenticated:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type=UserActivity.ActivityType.LOGOUT,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            print('Logout error:', str(e))
            return Response({
                'message': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsOwnerOrAdmin,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            UserActivity.objects.create(
                user=request.user,
                activity_type=UserActivity.ActivityType.PROFILE_UPDATE,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        return response

class ChangePasswordView(APIView):
    permission_classes = (IsOwnerOrAdmin,)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get('old_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                UserActivity.objects.create(
                    user=user,
                    activity_type=UserActivity.ActivityType.PASSWORD_CHANGE,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
            return Response({'error': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
            # Generate password reset token
            token = default_token_generator.make_token(user)
            reset_url = f"http://localhost:5173/reset-password?token={token}&email={email}"

            # Send password reset email using Django's send_mail
            from django.core.mail import send_mail
            send_mail(
                'Password Reset - Your Portfolio',
                f'''Hello,

You have requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email.

Best regards,
Portfolio Admin''',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return Response({
                'message': 'Password reset email sent successfully'
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                'message': 'No account found with this email'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print('Password reset error:', str(e))
            return Response({
                'message': 'Error sending password reset email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([email, token, new_password]):
            return Response({
                'message': 'Email, token and new password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
            
            # Verify token
            if not default_token_generator.check_token(user, token):
                return Response({
                    'message': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(new_password)
            user.save()

            # Log the password reset
            UserActivity.objects.create(
                user=user,
                activity_type=UserActivity.ActivityType.PASSWORD_RESET,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({
                'message': 'Password reset successful'
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                'message': 'No account found with this email'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print('Password reset error:', str(e))
            return Response({
                'message': 'Error resetting password'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserListView(generics.ListAPIView):
    """
    View to list all users in the system.
    Only admin users can access this view.
    """
    permission_classes = (IsAdmin,)
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserActivityListView(generics.ListAPIView):
    """
    View to list all user activities.
    Only admin users can access this view.
    """
    permission_classes = (IsAdmin,)
    serializer_class = UserActivitySerializer

    def get_queryset(self):
        return UserActivity.objects.all().order_by('-created_at')

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View to retrieve, update or delete a user instance.
    Only admin users can access this view.
    """
    permission_classes = (IsAdmin,)
    queryset = User.objects.all()
    serializer_class = UserSerializer
