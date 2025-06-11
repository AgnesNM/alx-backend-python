# admin.py (Optional: For Django admin interface)
from django.contrib import admin
from .models import Message, Notification


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'content', 'timestamp', 'is_read']
    list_filter = ['timestamp', 'is_read']
    search_fields = ['sender__username', 'receiver__username', 'content']
    readonly_fields = ['timestamp']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'content']
    readonly_fields = ['created_at']


# utils.py (Additional utility functions)
from django.contrib.auth.models import User
from .models import Notification


def create_custom_notification(user, title, content, notification_type='system'):
    """
    Utility function to create custom notifications programmatically
    """
    return Notification.objects.create(
        user=user,
        title=title,
        content=content,
        notification_type=notification_type
    )


def get_unread_notifications(user):
    """
    Get all unread notifications for a user
    """
    return Notification.objects.filter(user=user, is_read=False)


def mark_all_notifications_read(user):
    """
    Mark all notifications as read for a specific user
    """
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)
