# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Message, Notification


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal handler that creates a notification when a new message is created.
    """
    if created:  # Only trigger for new messages, not updates
        # Don't create notification if sender and receiver are the same
        if instance.sender != instance.receiver:
            Notification.objects.create(
                user=instance.receiver,
                message=instance,
                notification_type='message',
                title=f'New message from {instance.sender.username}',
                content=f'{instance.sender.username} sent you a message: "{instance.content[:50]}{"..." if len(instance.content) > 50 else ""}"'
            )

