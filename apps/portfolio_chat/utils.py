import resend
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_message_notification(recipient_email, sender_name, message_preview):
    """
    Send an email notification when a new message is received using Resend
    """
    try:
        resend.api_key = settings.RESEND_API_KEY
        
        html_message = render_to_string('chat/email/new_message.html', {
            'sender_name': sender_name,
            'message_preview': message_preview,
            'site_url': settings.SITE_URL,  # Add your site URL in settings
        })
        
        response = resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": recipient_email,
            "subject": f"New Message from {sender_name}",
            "html": html_message,
            "tags": [{"name": "message_type", "value": "chat_notification"}]
        })
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False
