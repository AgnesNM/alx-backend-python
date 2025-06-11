# ===================
# models.py - Updated models with edit tracking
# ===================
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Message(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)  # New field to track edits
    last_edited = models.DateTimeField(null=True, blank=True)  # When last edited

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

    def get_edit_count(self):
        """Return the number of times this message has been edited"""
        return self.history.count()

    def get_latest_history(self):
        """Return the most recent edit history"""
        return self.history.order_by('-edited_at').first()


class MessageHistory(models.Model):
    """Model to store message edit history"""
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='history'
    )
    old_content = models.TextField()  # Content before the edit
    edited_at = models.DateTimeField(default=timezone.now)
    edited_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='message_edits'
    )

    class Meta:
        ordering = ['-edited_at']
        verbose_name = 'Message History'
        verbose_name_plural = 'Message Histories'

    def __str__(self):
        return f"Edit history for message {self.message.id} at {self.edited_at}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('mention', 'Mention'),
        ('system', 'System Notification'),
        ('edit', 'Message Edited'),  # New notification type for edits
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True, 
        blank=True
    )
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES, 
        default='message'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"


# ===================
# signals.py - Updated signals with edit tracking
# ===================
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Message, Notification, MessageHistory


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


# ===================
# views.py - Updated views with edit functionality
# ===================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from .models import Message, Notification, MessageHistory


@login_required
def send_message(request):
    """View to send a new message"""
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            
            # Create the message (this will trigger the signal)
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message sent successfully',
                'message_id': message.id
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def edit_message(request, message_id):
    """View to edit an existing message"""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        
        if new_content and new_content != message.content:
            # Update the message (pre_save signal will handle history)
            message.content = new_content
            message.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message updated successfully',
                'edited': True,
                'edit_count': message.get_edit_count()
            })
        elif new_content == message.content:
            return JsonResponse({
                'status': 'info',
                'message': 'No changes made to the message'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Message content cannot be empty'
            })
    
    # GET request - return current message content
    return JsonResponse({
        'status': 'success',
        'content': message.content,
        'edited': message.edited,
        'edit_count': message.get_edit_count()
    })


@login_required
def message_history(request, message_id):
    """View to display message edit history"""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user has permission to view history
    if request.user != message.sender and request.user != message.receiver:
        raise Http404("You don't have permission to view this message history")
    
    # Get all history entries for this message
    history_entries = MessageHistory.objects.filter(message=message).order_by('-edited_at')
    
    # Paginate history
    paginator = Paginator(history_entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'message': message,
        'history_entries': page_obj,
        'can_edit': request.user == message.sender
    }
    
    return render(request, 'messaging/message_history.html', context)


@login_required
def user_messages(request):
    """View to display user's messages with edit indicators"""
    # Get messages where user is sender or receiver
    messages_list = Message.objects.filter(
        models.Q(sender=request.user) | models.Q(receiver=request.user)
    ).order_by('-timestamp')
    
    # Paginate messages
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/messages_list.html', {
        'messages': page_obj
    })


@login_required
def notifications_list(request):
    """View to display user's notifications"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Paginate notifications
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/notifications.html', {
        'notifications': page_obj
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        user=request.user
    )
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'status': 'success'})


@login_required
def unread_notifications_count(request):
    """API endpoint to get count of unread notifications"""
    count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': count})


# ===================
# admin.py - Updated admin with history
# ===================
from django.contrib import admin
from .models import Message, Notification, MessageHistory


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'content', 'timestamp', 'is_read', 'edited', 'last_edited']
    list_filter = ['timestamp', 'is_read', 'edited']
    search_fields = ['sender__username', 'receiver__username', 'content']
    readonly_fields = ['timestamp', 'edited', 'last_edited']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'receiver')


@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ['message', 'edited_by', 'edited_at', 'old_content_preview']
    list_filter = ['edited_at', 'edited_by']
    search_fields = ['message__content', 'old_content', 'edited_by__username']
    readonly_fields = ['edited_at']
    
    def old_content_preview(self, obj):
        return obj.old_content[:50] + "..." if len(obj.old_content) > 50 else obj.old_content
    old_content_preview.short_description = 'Old Content Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'edited_by')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'content']
    readonly_fields = ['created_at']


# ===================
# urls.py - URL patterns
# ===================
from django.urls import path
from . import views

urlpatterns = [
    path('send-message/', views.send_message, name='send_message'),
    path('edit-message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('message-history/<int:message_id>/', views.message_history, name='message_history'),
    path('messages/', views.user_messages, name='user_messages'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/unread-count/', views.unread_notifications_count, name='unread_count'),
]


# ===================
# utils.py - Updated utility functions
# ===================
from django.contrib.auth.models import User
from .models import Notification, Message, MessageHistory


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


def get_message_edit_history(message_id, user):
    """
    Get edit history for a message if user has permission
    """
    try:
        message = Message.objects.get(id=message_id)
        if user == message.sender or user == message.receiver:
            return MessageHistory.objects.filter(message=message).order_by('-edited_at')
        return None
    except Message.DoesNotExist:
        return None


def can_edit_message(message, user):
    """
    Check if a user can edit a specific message
    """
    return user == message.sender


def get_user_message_stats(user):
    """
    Get statistics about user's messages
    """
    sent_messages = Message.objects.filter(sender=user)
    received_messages = Message.objects.filter(receiver=user)
    edited_messages = sent_messages.filter(edited=True)
    
    return {
        'sent_count': sent_messages.count(),
        'received_count': received_messages.count(),
        'edited_count': edited_messages.count(),
        'total_edits': MessageHistory.objects.filter(message__sender=user).count()
    }
