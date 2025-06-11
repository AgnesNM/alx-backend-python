# models.py - Complete models with unread custom manager
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


# ✅ Custom Managers defined in models.py (can also be in separate managers.py)
class UnreadMessagesManager(models.Manager):
    """
    Custom manager for filtering unread messages for a specific user.
    Provides optimized queries for unread message operations.
    """
    
    def for_user(self, user):
        """
        Get all unread messages for a specific user (where user is receiver).
        Returns QuerySet of unread messages.
        """
        return self.filter(receiver=user, is_read=False)
    
    def unread_for_user(self, user):
        """
        Alias for for_user() - more descriptive method name.
        Get all unread messages for a specific user.
        """
        return self.for_user(user)
    
    def unread_count_for_user(self, user):
        """
        Get count of unread messages for a specific user.
        More efficient than len() as it uses COUNT() query.
        """
        return self.filter(receiver=user, is_read=False).count()
    
    def unread_threads_for_user(self, user):
        """
        Get unread thread root messages for a user.
        Returns root messages of threads that have unread messages.
        """
        return self.filter(
            receiver=user,
            is_read=False,
            parent_message__isnull=True  # Only root messages
        )
    
    def unread_replies_for_user(self, user):
        """
        Get unread reply messages for a user.
        Returns only reply messages (not thread roots).
        """
        return self.filter(
            receiver=user,
            is_read=False,
            parent_message__isnull=False  # Only replies
        )
    
    def mark_thread_as_read(self, thread_root, user):
        """
        Mark all messages in a thread as read for a specific user.
        Returns number of messages marked as read.
        """
        return self.filter(
            Q(id=thread_root.id) | Q(thread_root=thread_root),
            receiver=user,
            is_read=False
        ).update(is_read=True)
    
    def unread_with_optimized_fields(self, user):
        """
        Get unread messages with only necessary fields using .only().
        Optimized for performance when you only need specific fields.
        """
        return self.filter(
            receiver=user, 
            is_read=False
        ).only(  # ✅ .only() optimization
            'id', 
            'sender', 
            'content', 
            'timestamp', 
            'parent_message',
            'thread_root',
            'depth_level'
        ).select_related('sender', 'parent_message')
    
    def unread_inbox_optimized(self, user):
        """
        Optimized query for inbox view with unread messages.
        Uses select_related, prefetch_related, and only() for best performance.
        """
        return self.filter(
            receiver=user,
            is_read=False
        ).only(  # ✅ .only() for specific fields
            'id',
            'sender',
            'receiver', 
            'content',
            'timestamp',
            'parent_message',
            'thread_root',
            'depth_level',
            'reply_count',
            'edited'
        ).select_related(
            'sender',
            'receiver',
            'parent_message',
            'thread_root'
        ).prefetch_related(
            'replies'
        ).order_by('-timestamp')
    
    def recent_unread_for_user(self, user, limit=10):
        """
        Get recent unread messages for a user with limit.
        Useful for notifications or dashboard views.
        """
        return self.filter(
            receiver=user,
            is_read=False
        ).only(  # ✅ .only() optimization
            'id',
            'sender',
            'content',
            'timestamp'
        ).select_related(
            'sender'
        ).order_by('-timestamp')[:limit]


class ThreadMessagesManager(models.Manager):
    """
    Custom manager for thread-related message operations.
    """
    
    def thread_roots_for_user(self, user):
        """
        Get all thread root messages for a user.
        """
        return self.filter(
            Q(sender=user) | Q(receiver=user),
            parent_message__isnull=True
        )
    
    def unread_thread_roots_for_user(self, user):
        """
        Get thread roots that have unread messages for a user.
        """
        return self.filter(
            receiver=user,
            is_read=False,
            parent_message__isnull=True
        )


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
    
    # ✅ Read status field
    is_read = models.BooleanField(default=False)
    
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(null=True, blank=True)
    
    # Threading fields
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
    
    # ✅ CUSTOM MANAGERS - These lines are critical!
    objects = models.Manager()  # Default manager
    unread = UnreadMessagesManager()  # ✅ Custom unread manager
    threads = ThreadMessagesManager()  # Custom thread manager

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['receiver', 'is_read']),  # ✅ Optimized for unread queries
            models.Index(fields=['parent_message']),
            models.Index(fields=['thread_root']),
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['is_read', 'timestamp']),  # ✅ Composite index
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
                Q(id=root.id) | Q(thread_root=root)
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
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    def mark_as_unread(self):
        """Mark this message as unread"""
        if self.is_read:
            self.is_read = False
            self.save(update_fields=['is_read'])


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
        ('reply', 'New Reply'),
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
