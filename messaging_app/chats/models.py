
# chats/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Extended User model with additional fields for messaging functionality
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Conversation(models.Model):
    """
    Model to track conversations between users
    """
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    conversation_type = models.CharField(
        max_length=10, 
        choices=CONVERSATION_TYPES, 
        default='direct'
    )
    participants = models.ManyToManyField(
        User, 
        through='ConversationParticipant',
        related_name='conversations'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
    
    def __str__(self):
        if self.title:
            return self.title
        elif self.conversation_type == 'direct':
            participants = list(self.participants.all()[:2])
            if len(participants) == 2:
                return f"Chat between {participants[0].username} and {participants[1].username}"
            return f"Direct message"
        else:
            return f"Group chat {self.id}"
    
    @property
    def participant_count(self):
        return self.participants.count()
    
    def get_last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()


class ConversationParticipant(models.Model):
    """
    Through model for Conversation participants with additional metadata
    """
    PARTICIPANT_ROLES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
        ('owner', 'Owner'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='conversation_participants'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='user_conversations'
    )
    role = models.CharField(max_length=10, choices=PARTICIPANT_ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'conversation_participants'
        unique_together = ['conversation', 'user']
        verbose_name = 'Conversation Participant'
        verbose_name_plural = 'Conversation Participants'
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"
    
    def mark_as_read(self):
        """Mark all messages in this conversation as read for this user"""
        self.last_read_at = timezone.now()
        self.save()
    
    def get_unread_count(self):
        """Get count of unread messages for this participant"""
        if not self.last_read_at:
            return self.conversation.messages.filter(is_deleted=False).count()
        
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at,
            is_deleted=False
        ).exclude(sender=self.user).count()


class Message(models.Model):
    """
    Model for individual messages within conversations
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('system', 'System Message'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    
    # File attachments
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.PositiveIntegerField(null=True, blank=True)  # Size in bytes
    
    # Message metadata
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Reply functionality
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.sender.username}: {content_preview}"
    
    def soft_delete(self):
        """Soft delete the message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def edit_message(self, new_content):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()
    
    @property
    def is_reply(self):
        return self.reply_to is not None
    
    def get_attachment_url(self):
        """Get URL for attachment if exists"""
        if self.attachment:
            return self.attachment.url
        return None


class MessageReadStatus(models.Model):
    """
    Track read status of messages by users
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE,
        related_name='read_status'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='message_reads'
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_read_status'
        unique_together = ['message', 'user']
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'
    
    def __str__(self):
        return f"{self.user.username} read {self.message.id}"
