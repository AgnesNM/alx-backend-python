# managers.py - Create this file in your messaging/ directory
from django.db import models
from django.db.models import Q


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
