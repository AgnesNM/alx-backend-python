# models.py - Complete models with threading support
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
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(null=True, blank=True)
    
    # ✅ THREADING FIELDS - These were missing!
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    thread_root = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='thread_messages'
    )
    
    depth_level = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['parent_message']),
            models.Index(fields=['thread_root']),
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        if self.parent_message:
            return f"Reply by {self.sender.username} to message {self.parent_message.id}"
        return f"Message from {self.sender.username} to {self.receiver.username}"

    def get_edit_count(self):
        """Return the number of times this message has been edited"""
        return self.history.count()

    def get_latest_history(self):
        """Return the most recent edit history"""
        return self.history.order_by('-edited_at').first()
    
    def is_thread_starter(self):
        """Check if this message is the start of a thread"""
        return self.parent_message is None
    
    def get_thread_root(self):
        """Get the root message of this thread"""
        if self.thread_root:
            return self.thread_root
        return self if self.is_thread_starter() else None
    
    def get_all_replies(self):
        """Get all replies to this message (direct replies only)"""
        return self.replies.all().order_by('timestamp')
    
    def get_thread_messages(self):
        """Get all messages in this thread"""
        root = self.get_thread_root()
        if root:
            return Message.objects.filter(
                models.Q(id=root.id) | models.Q(thread_root=root)
            ).order_by('timestamp')
        return Message.objects.filter(id=self.id)
    
    def update_reply_count(self):
        """Update the reply count for this message"""
        self.reply_count = self.replies.count()
        self.save(update_fields=['reply_count'])
    
    def get_conversation_participants(self):
        """Get all users who participated in this thread"""
        thread_messages = self.get_thread_messages()
        participants = set()
        for msg in thread_messages:
            participants.add(msg.sender)
            participants.add(msg.receiver)
        return list(participants)


class MessageHistory(models.Model):
    """Model to store message edit history"""
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE,
        related_name='history'
    )
    old_content = models.TextField()
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
        ('reply', 'New Reply'),  # ✅ NEW: Reply notification type
        ('mention', 'Mention'),
        ('system', 'System Notification'),
        ('edit', 'Message Edited'),
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


class UserDeletionLog(models.Model):
    """Model to log user deletions for audit purposes"""
    username = models.CharField(max_length=150)
    email = models.EmailField()
    deleted_at = models.DateTimeField(default=timezone.now)
    deleted_by = models.CharField(max_length=150)
    deletion_reason = models.TextField(blank=True)
    
    # Statistics about deleted data
    messages_sent_count = models.IntegerField(default=0)
    messages_received_count = models.IntegerField(default=0)
    notifications_count = models.IntegerField(default=0)
    message_edits_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-deleted_at']

    def __str__(self):
        return f"Deletion log for {self.username} at {self.deleted_at}"
