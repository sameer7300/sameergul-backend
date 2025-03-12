from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.utils import timezone
from .models import Conversation, Message, Notification
from .serializers import ConversationSerializer, MessageSerializer, NotificationSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.http import FileResponse
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from .utils import send_message_notification
import logging

class UserListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        User = get_user_model()
        users = User.objects.exclude(id=request.user.id)
        return Response([{
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        } for user in users])

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)
        participant_id = self.request.data.get('participant_id')
        if participant_id:
            conversation.participants.add(participant_id)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not a participant in this conversation"},
                status=status.HTTP_403_FORBIDDEN
            )
        messages = conversation.messages.order_by('created_at')  # Order by oldest first
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not a participant in this conversation"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create message with file if present
        message_data = {
            'conversation': conversation,
            'sender': request.user,
            'content': request.data.get('content', '')
        }

        if 'file' in request.FILES:
            message_data['file'] = request.FILES['file']

        message = Message.objects.create(**message_data)

        # Create notifications for other participants
        notification_type = 'file' if 'file' in request.FILES else 'message'
        notification_title = (
            f'New file from {request.user.get_full_name() or request.user.email}'
            if 'file' in request.FILES
            else f'New message from {request.user.get_full_name() or request.user.email}'
        )

        for participant in conversation.participants.exclude(id=request.user.id):
            notification = Notification.objects.create(
                recipient=participant,
                type=notification_type,
                title=notification_title,
                content=message.content[:100] + '...' if len(message.content) > 100 else message.content,
                related_conversation=conversation,
                related_message=message,
                extra_data={'file_name': message.file_name} if message.file else None
            )

            # Send email notification if user has email notifications enabled
            profile = getattr(participant, 'profile', None)
            if profile and getattr(profile, 'email_notifications_enabled', False):
                try:
                    send_mail(
                        notification_title,
                        f'You have a new {notification_type} in your conversation.\n\n'
                        f'{"File: " + message.file_name if message.file else ""}\n'
                        f'Message: {message.content[:200]}...',
                        settings.DEFAULT_FROM_EMAIL,
                        [participant.email],
                        fail_silently=True,
                    )
                    logging.info(f"Email notification sent to {participant.email}")
                except Exception as e:
                    logging.error(f"Failed to send email to {participant.email}: {str(e)}")

        return Response(MessageSerializer(message, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def available_users(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.exclude(id=request.user.id)
        return Response([{
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        } for user in users])

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        return Message.objects.filter(conversation_id=conversation_id)

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_pk')
        conversation = Conversation.objects.get(id=conversation_id)
        message = serializer.save(
            sender=self.request.user,
            conversation=conversation
        )
        
        # Send email notification to other participants
        for participant in conversation.participants.all():
            if participant != self.request.user:
                try:
                    # Create message preview
                    message_preview = message.content[:100] + '...' if len(message.content) > 100 else message.content
                    if message.file:
                        message_preview = f" {message.file_name}" + (f" - {message_preview}" if message.content else "")
                    
                    # Send notification
                    send_message_notification(
                        recipient_email=participant.email,
                        sender_name=f"{self.request.user.get_full_name() or self.request.user.email}",
                        message_preview=message_preview
                    )
                    logging.info(f"Email notification sent to {participant.email}")
                except Exception as e:
                    logging.error(f"Failed to send email to {participant.email}: {str(e)}")

        return message

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        message.mark_as_read()
        return Response(MessageSerializer(message, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def download_file(self, request, pk=None):
        message = self.get_object()
        if not message.file:
            return Response({'error': 'No file attached'}, status=400)
        
        file_path = message.file.path
        content_type = message.file_type or 'application/octet-stream'
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{message.file_name}"'
        return response

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        notifications = self.get_queryset().filter(is_read=False)
        notifications.update(is_read=True, read_at=timezone.now())
        return Response({"status": "success"})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data)
