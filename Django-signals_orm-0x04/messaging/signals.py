# signals.py - Corrected with proper imports
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Message, Notification, MessageHistory  # ✅ Added MessageHistory import


@receiver(pre_save, sender=Message)
def save_message_history(sender, instance, **kwargs):
    """
    Signal handler that saves the old content before a message is updated.
    """
    if instance.pk:  # Only for existing messages (updates, not new creations)
        try:
            # Get the current version from database
            old_message = Message.objects.get(pk=instance.pk)
            
            # Check if content has actually changed
            if old_message.content != instance.content:
                # Save the old content to history
                MessageHistory.objects.create(  # ✅ Now properly imported
                    message=instance,
                    old_content=old_message.content,
                    edited_by=instance.sender,  # Assuming sender is the editor
                    edited_at=timezone.now()
                )
                
                # Mark message as edited
                instance.edited = True
                instance.last_edited = timezone.now()
                
        except Message.DoesNotExist:
            # This shouldn't happen, but just in case
            pass


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


@receiver(post_save, sender=Message)
def create_edit_notification(sender, instance, created, **kwargs):
    """
    Signal handler that creates a notification when a message is edited.
    """
    if not created and instance.edited:  # Only for updates where message was edited
        # Get the latest history entry to confirm this is a new edit
        latest_history = instance.get_latest_history()
        
        if latest_history and instance.sender != instance.receiver:
            # Create notification for the receiver about the edit
            Notification.objects.create(
                user=instance.receiver,
                message=instance,
                notification_type='edit',
                title=f'Message edited by {instance.sender.username}',
                content=f'{instance.sender.username} edited their message: "{instance.content[:50]}{"..." if len(instance.content) > 50 else ""}"'
            )
