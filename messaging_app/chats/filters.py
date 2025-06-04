# filters.py
import django_filters
from django_filters import rest_framework as filters
from django.contrib.auth.models import User
from django.db import models
from .models import Message, Conversation


class MessageFilter(django_filters.FilterSet):
    """
    Filter class for Message model with various filtering options.
    """
    
    # Time range filtering
    created_after = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='gte',
        help_text="Filter messages created after this datetime (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='lte',
        help_text="Filter messages created before this datetime (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    
    # Date range filtering (without time)
    date_after = django_filters.DateFilter(
        field_name='created_at', 
        lookup_expr='date__gte',
        help_text="Filter messages created after this date (YYYY-MM-DD)"
    )
    date_before = django_filters.DateFilter(
        field_name='created_at', 
        lookup_expr='date__lte',
        help_text="Filter messages created before this date (YYYY-MM-DD)"
    )
    
    # User filtering
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        help_text="Filter messages by specific user ID"
    )
    user_username = django_filters.CharFilter(
        field_name='user__username', 
        lookup_expr='icontains',
        help_text="Filter messages by username (case-insensitive partial match)"
    )
    
    # Conversation filtering
    conversation = django_filters.NumberFilter(
        field_name='conversation__id',
        help_text="Filter messages by conversation ID"
    )
    conversation_title = django_filters.CharFilter(
        field_name='conversation__title', 
        lookup_expr='icontains',
        help_text="Filter messages by conversation title (case-insensitive partial match)"
    )
    
    # Content filtering
    content = django_filters.CharFilter(
        field_name='content', 
        lookup_expr='icontains',
        help_text="Filter messages by content (case-insensitive partial match)"
    )
    content_exact = django_filters.CharFilter(
        field_name='content', 
        lookup_expr='iexact',
        help_text="Filter messages by exact content (case-insensitive)"
    )
    
    # Message type filtering
    message_type = django_filters.ChoiceFilter(
        choices=Message.MESSAGE_TYPES,
        help_text="Filter messages by type (text, image, file, system)"
    )
    
    # Boolean filters
    is_edited = django_filters.BooleanFilter(
        help_text="Filter messages that have been edited (true/false)"
    )
    is_deleted = django_filters.BooleanFilter(
        help_text="Filter messages that have been deleted (true/false)"
    )
    
    # Multiple users filter (conversations with specific users)
    participants = django_filters.ModelMultipleChoiceFilter(
        field_name='conversation__participants',
        queryset=User.objects.all(),
        help_text="Filter messages from conversations with specific participants (comma-separated user IDs)"
    )
    
    # Custom method filter for conversations with specific users
    conversation_with_users = django_filters.CharFilter(
        method='filter_conversation_with_users',
        help_text="Filter messages from conversations containing specific users (comma-separated usernames)"
    )
    
    # Time range shortcut filters
    last_hour = django_filters.BooleanFilter(
        method='filter_last_hour',
        help_text="Filter messages from the last hour (true/false)"
    )
    last_day = django_filters.BooleanFilter(
        method='filter_last_day',
        help_text="Filter messages from the last 24 hours (true/false)"
    )
    last_week = django_filters.BooleanFilter(
        method='filter_last_week',
        help_text="Filter messages from the last week (true/false)"
    )
    
    class Meta:
        model = Message
        fields = {
            'id': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
    
    def filter_conversation_with_users(self, queryset, name, value):
        """
        Filter messages from conversations that include specific users.
        Value should be comma-separated usernames.
        """
        if not value:
            return queryset
        
        usernames = [username.strip() for username in value.split(',')]
        
        # Find conversations that have ALL specified users as participants
        conversation_ids = []
        for conversation in Conversation.objects.all():
            conversation_usernames = set(
                conversation.participants.values_list('username', flat=True)
            )
            if all(username in conversation_usernames for username in usernames):
                conversation_ids.append(conversation.id)
        
        return queryset.filter(conversation__id__in=conversation_ids)
    
    def filter_last_hour(self, queryset, name, value):
        """Filter messages from the last hour."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            one_hour_ago = timezone.now() - timedelta(hours=1)
            return queryset.filter(created_at__gte=one_hour_ago)
        return queryset
    
    def filter_last_day(self, queryset, name, value):
        """Filter messages from the last 24 hours."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            one_day_ago = timezone.now() - timedelta(days=1)
            return queryset.filter(created_at__gte=one_day_ago)
        return queryset
    
    def filter_last_week(self, queryset, name, value):
        """Filter messages from the last week."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            one_week_ago = timezone.now() - timedelta(weeks=1)
            return queryset.filter(created_at__gte=one_week_ago)
        return queryset


class ConversationFilter(django_filters.FilterSet):
    """
    Filter class for Conversation model.
    """
    
    # Title filtering
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter conversations by title (case-insensitive partial match)"
    )
    
    # Participant filtering
    participants = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        help_text="Filter conversations with specific participants (comma-separated user IDs)"
    )
    
    participant_username = django_filters.CharFilter(
        field_name='participants__username',
        lookup_expr='icontains',
        help_text="Filter conversations by participant username"
    )
    
    # Date filtering
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    
    # Activity filtering
    is_active = django_filters.BooleanFilter()
    
    # Custom filter for conversations with specific users
    with_users = django_filters.CharFilter(
        method='filter_with_users',
        help_text="Filter conversations containing specific users (comma-separated usernames)"
    )
    
    class Meta:
        model = Conversation
        fields = {
            'id': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
    
    def filter_with_users(self, queryset, name, value):
        """
        Filter conversations that include specific users.
        """
        if not value:
            return queryset
        
        usernames = [username.strip() for username in value.split(',')]
        
        # Filter conversations that have all specified users
        for username in usernames:
            queryset = queryset.filter(participants__username=username)
        
        return queryset.distinct()
