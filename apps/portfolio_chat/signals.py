from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Message, Notification

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    if created:
        conversation = instance.conversation
        for participant in conversation.participants.exclude(id=instance.sender.id):
            # Create in-app notification
            Notification.objects.create(
                recipient=participant,
                type='message',
                title=f'New message from {instance.sender.username}',
                content=instance.content[:100] + '...' if len(instance.content) > 100 else instance.content,
                related_conversation=conversation,
                related_message=instance
            )

            # Send email notification if enabled
            if hasattr(participant, 'profile') and participant.profile.email_notifications_enabled:
                send_mail(
                    f'New message from {instance.sender.username}',
                    f'You have a new message in your conversation.\n\n"{instance.content[:200]}..."',
                    settings.DEFAULT_FROM_EMAIL,
                    [participant.email],
                    fail_silently=True,
                )
