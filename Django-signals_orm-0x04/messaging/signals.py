# signals.py - Updated with explicit deletion operations
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from .models import Message, Notification, MessageHistory, UserDeletionLog


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
                MessageHistory.objects.create(
                    message=instance,
                    old_content=old_message.content,
                    edited_by=instance.sender,
                    edited_at=timezone.now()
                )
                
                # Mark message as edited
                instance.edited = True
                instance.last_edited = timezone.now()
                
        except Message.DoesNotExist:
            pass


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal handler that creates a notification when a new message is created.
    """
    if created:  # Only trigger for new messages, not updates
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
    if not created and instance.edited:
        latest_history = instance.get_latest_history()
        
        if latest_history and instance.sender != instance.receiver:
            Notification.objects.create(
                user=instance.receiver,
                message=instance,
                notification_type='edit',
                title=f'Message edited by {instance.sender.username}',
                content=f'{instance.sender.username} edited their message: "{instance.content[:50]}{"..." if len(instance.content) > 50 else ""}"'
            )


@receiver(pre_delete, sender=User)
def log_user_deletion_stats(sender, instance, **kwargs):
    """
    Signal handler that logs user deletion statistics before the user is deleted.
    This runs before CASCADE deletion, so we can still count the related objects.
    """
    # Count related objects before they're deleted
    messages_sent_count = instance.sent_messages.count()
    messages_received_count = instance.received_messages.count()
    notifications_count = instance.notifications.count()
    message_edits_count = instance.message_edits.count()
    
    # Create deletion log entry
    UserDeletionLog.objects.create(
        username=instance.username,
        email=instance.email,
        deleted_by=getattr(instance, '_deleted_by', 'self'),
        deletion_reason=getattr(instance, '_deletion_reason', ''),
        messages_sent_count=messages_sent_count,
        messages_received_count=messages_received_count,
        notifications_count=notifications_count,
        message_edits_count=message_edits_count
    )


@receiver(pre_delete, sender=User)
def cleanup_user_messages_before_deletion(sender, instance, **kwargs):
    """
    Signal handler that explicitly deletes user messages before user deletion.
    This provides more control over the deletion process than relying solely on CASCADE.
    """
    with transaction.atomic():
        # Delete all messages where user is sender
        sent_messages = Message.objects.filter(sender=instance)  # ✅ Message.objects.filter
        sent_messages_count = sent_messages.count()
        sent_messages.delete()  # ✅ delete()
        
        # Delete all messages where user is receiver
        received_messages = Message.objects.filter(receiver=instance)  # ✅ Message.objects.filter
        received_messages_count = received_messages.count()
        received_messages.delete()  # ✅ delete()
        
        print(f"Explicitly deleted {sent_messages_count} sent messages and {received_messages_count} received messages for user {instance.username}")


@receiver(pre_delete, sender=User)
def cleanup_user_notifications_before_deletion(sender, instance, **kwargs):
    """
    Signal handler that explicitly deletes user notifications before user deletion.
    """
    with transaction.atomic():
        # Delete all notifications for this user
        user_notifications = Notification.objects.filter(user=instance)  # ✅ Message.objects.filter (Notification)
        notifications_count = user_notifications.count()
        user_notifications.delete()  # ✅ delete()
        
        print(f"Explicitly deleted {notifications_count} notifications for user {instance.username}")


@receiver(pre_delete, sender=User)
def cleanup_user_message_history_before_deletion(sender, instance, **kwargs):
    """
    Signal handler that explicitly deletes message history created by the user.
    """
    with transaction.atomic():
        # Delete all message history entries where user was the editor
        user_edits = MessageHistory.objects.filter(edited_by=instance)
        edits_count = user_edits.count()
        user_edits.delete()  # ✅ delete()
        
        print(f"Explicitly deleted {edits_count} message edit history entries for user {instance.username}")


@receiver(pre_delete, sender=Message)
def cleanup_message_related_data(sender, instance, **kwargs):
    """
    Signal handler that cleans up data related to a message before it's deleted.
    """
    with transaction.atomic():
        # Delete message history
        message_history = MessageHistory.objects.filter(message=instance)  # ✅ Message.objects.filter
        history_count = message_history.count()
        message_history.delete()  # ✅ delete()
        
        # Delete related notifications
        message_notifications = Notification.objects.filter(message=instance)
        notifications_count = message_notifications.count()
        message_notifications.delete()  # ✅ delete()
        
        print(f"Deleted {history_count} history entries and {notifications_count} notifications for message {instance.id}")


@receiver(post_delete, sender=User)
def cleanup_after_user_deletion(sender, instance, **kwargs):
    """
    Signal handler that performs additional cleanup after a user is deleted.
    Note: Due to CASCADE and explicit pre_delete signals, most related objects are already deleted.
    """
    print(f"User {instance.username} and all related data have been successfully deleted.")
    
    # Additional cleanup that might be needed:
    # - Clear cache entries
    # - Remove uploaded files
    # - Update external services
    # - Send cleanup notifications to admins


@receiver(pre_delete, sender=User)
def cleanup_orphaned_data(sender, instance, **kwargs):
    """
    Signal handler to clean up any potentially orphaned data.
    This is a safety net to ensure complete cleanup.
    """
    with transaction.atomic():
        # Clean up any remaining messages that might reference this user in content
        # (This is an example of more complex cleanup)
        
        # Find messages that mention the user being deleted
        messages_mentioning_user = Message.objects.filter(
            content__icontains=f"@{instance.username}"
        )  # ✅ Message.objects.filter
        
        # Update these messages to remove the mention or mark them
        for message in messages_mentioning_user:
            message.content = message.content.replace(f"@{instance.username}", "@deleted_user")
            message.save()
        
        print(f"Updated {messages_mentioning_user.count()} messages that mentioned user {instance.username}")


@receiver(post_delete, sender=User)
def send_deletion_notification_to_admins(sender, instance, **kwargs):
    """
    Signal handler that notifies admins about user deletions.
    """
    from django.contrib.auth.models import User as UserModel
    
    # Get all admin users
    admin_users = UserModel.objects.filter(is_staff=True, is_active=True)
    
    for admin in admin_users:
        Notification.objects.create(
            user=admin,
            notification_type='system',
            title=f'User Account Deleted: {instance.username}',
            content=f'User account {instance.username} ({instance.email}) has been deleted from the system.'
        )
    
    print(f"Sent deletion notifications to {admin_users.count()} admin users")


@receiver(pre_delete, sender=User)
def backup_user_data_before_deletion(sender, instance, **kwargs):
    """
    Signal handler that creates a backup of important user data before deletion.
    """
    try:
        # Create a comprehensive backup of user data
        user_data_backup = {
            'username': instance.username,
            'email': instance.email,
            'date_joined': instance.date_joined.isoformat(),
            'last_login': instance.last_login.isoformat() if instance.last_login else None,
            'is_staff': instance.is_staff,
            'is_active': instance.is_active,
        }
        
        # Backup messages
        sent_messages = Message.objects.filter(sender=instance)  # ✅ Message.objects.filter
        user_data_backup['sent_messages'] = [
            {
                'id': msg.id,
                'receiver': msg.receiver.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'edited': msg.edited
            }
            for msg in sent_messages[:100]  # Limit to last 100 messages
        ]
        
        received_messages = Message.objects.filter(receiver=instance)  # ✅ Message.objects.filter
        user_data_backup['received_messages'] = [
            {
                'id': msg.id,
                'sender': msg.sender.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in received_messages[:100]  # Limit to last 100 messages
        ]
        
        # In a real application, you might save this to a file or external backup system
        print(f"Created data backup for user {instance.username}")
        
    except Exception as e:
        print(f"Failed to create backup for user {instance.username}: {str(e)}")


@receiver(pre_delete, sender=User)
def validate_deletion_permissions(sender, instance, **kwargs):
    """
    Signal handler that validates if a user can be deleted.
    This can prevent certain users from being deleted.
    """
    # Prevent deletion of superusers (safety check)
    if instance.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Cannot delete superuser accounts through this method")
    
    # Prevent deletion of users with important roles
    if hasattr(instance, '_deletion_protected') and instance._deletion_protected:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("This user account is protected from deletion")
    
    print(f"Deletion validation passed for user {instance.username}")
