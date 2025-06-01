# chats/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, ConversationParticipant, MessageReadStatus

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'phone_number', 'profile_picture', 'bio', 
            'is_online', 'last_seen'
        ]
        read_only_fields = ['id', 'last_seen']


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer for ConversationParticipant"""
    user = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'role', 'joined_at', 'last_read_at', 
            'is_muted', 'unread_count'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def get_unread_count(self, obj):
        return obj.get_unread_count()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    sender = UserSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'message_type',
            'attachment', 'attachment_name', 'attachment_size', 'attachment_url',
            'is_edited', 'edited_at', 'is_deleted', 'reply_to', 'is_reply',
            'is_read', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'is_edited', 'edited_at', 'is_deleted', 
            'created_at', 'updated_at'
        ]
    
    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:100],
                'sender': obj.reply_to.sender.username,
                'created_at': obj.reply_to.created_at
            }
        return None
    
    def get_attachment_url(self, obj):
        return obj.get_attachment_url()
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MessageReadStatus.objects.filter(
                message=obj, user=request.user
            ).exists()
        return False


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model"""
    participants = ConversationParticipantSerializer(
        source='conversation_participants', many=True, read_only=True
    )
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    last_message = MessageSerializer(read_only=True)
    participant_count = serializers.ReadOnlyField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'conversation_type', 'participants', 'participant_ids',
            'created_by', 'last_message', 'participant_count', 'unread_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.conversation_participants.filter(
                user=request.user
            ).first()
            return participant.get_unread_count() if participant else 0
        return 0
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        request = self.context['request']
        
        # Create conversation
        conversation = Conversation.objects.create(
            created_by=request.user,
            **validated_data
        )
        
        # Add creator as owner
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=request.user,
            role='owner'
        )
        
        # Add other participants
        for user_id in participant_ids:
            try:
                user = User.objects.get(id=user_id)
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=user,
                    role='member'
                )
            except User.DoesNotExist:
                continue
        
        return conversation


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = [
            'conversation', 'content', 'message_type', 'attachment', 
            'attachment_name', 'reply_to'
        ]
    
    def validate_conversation(self, value):
        """Ensure user is participant in the conversation"""
        request = self.context['request']
        if not value.participants.filter(id=request.user.id).exists():
            raise serializers.ValidationError(
                "You are not a participant in this conversation."
            )
        return value
    
    def validate(self, data):
        """Ensure message has content or attachment"""
        if not data.get('content') and not data.get('attachment'):
            raise serializers.ValidationError(
                "Message must have either content or attachment."
            )
        return data
    
    def create(self, validated_data):
        request = self.context['request']
        
        # Set attachment metadata if file is uploaded
        if validated_data.get('attachment'):
            attachment = validated_data['attachment']
            if not validated_data.get('attachment_name'):
                validated_data['attachment_name'] = attachment.name
            validated_data['attachment_size'] = attachment.size
        
        # Create message
        message = Message.objects.create(
            sender=request.user,
            **validated_data
        )
        
        # Update conversation timestamp
        message.conversation.save()
        
        return message


# chats/filters.py

import django_filters
from django.db.models import Q
from .models import Conversation, Message


class ConversationFilter(django_filters.FilterSet):
    """
    Filter class for Conversation model
    """
    conversation_type = django_filters.ChoiceFilter(
        choices=Conversation.CONVERSATION_TYPES,
        field_name='conversation_type'
    )
    
    participant = django_filters.UUIDFilter(
        field_name='participants__id',
        lookup_expr='exact'
    )
    
    participant_username = django_filters.CharFilter(
        field_name='participants__username',
        lookup_expr='icontains'
    )
    
    has_unread = django_filters.BooleanFilter(
        method='filter_has_unread'
    )
    
    is_active = django_filters.BooleanFilter(
        field_name='is_active'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    
    updated_after = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='gte'
    )
    
    updated_before = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='lte'
    )
    
    title = django_filters.CharFilter(
        field_name='title',
        lookup_expr='icontains'
    )
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_type', 'participant', 'participant_username',
            'has_unread', 'is_active', 'created_after', 'created_before',
            'updated_after', 'updated_before', 'title'
        ]
    
    def filter_has_unread(self, queryset, name, value):
        """Filter conversations that have unread messages for the current user"""
        if not value or not self.request or not self.request.user.is_authenticated:
            return queryset
        
        user = self.request.user
        conversations_with_unread = []
        
        for conversation in queryset:
            participant = conversation.conversation_participants.filter(user=user).first()
            if participant and participant.get_unread_count() > 0:
                conversations_with_unread.append(conversation.id)
        
        return queryset.filter(id__in=conversations_with_unread)


class MessageFilter(django_filters.FilterSet):
    """
    Filter class for Message model
    """
    conversation = django_filters.UUIDFilter(
        field_name='conversation__id',
        lookup_expr='exact'
    )
    
    sender = django_filters.UUIDFilter(
        field_name='sender__id',
        lookup_expr='exact'
    )
    
    sender_username = django_filters.CharFilter(
        field_name='sender__username',
        lookup_expr='icontains'
    )
    
    message_type = django_filters.ChoiceFilter(
        choices=Message.MESSAGE_TYPES,
        field_name='message_type'
    )
    
    has_attachment = django_filters.BooleanFilter(
        method='filter_has_attachment'
    )
    
    is_reply = django_filters.BooleanFilter(
        method='filter_is_reply'
    )
    
    is_edited = django_filters.BooleanFilter(
        field_name='is_edited'
    )
    
    is_deleted = django_filters.BooleanFilter(
        field_name='is_deleted'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    
    content = django_filters.CharFilter(
        field_name='content',
        lookup_expr='icontains'
    )
    
    # Date range filters
    today = django_filters.BooleanFilter(
        method='filter_today'
    )
    
    this_week = django_filters.BooleanFilter(
        method='filter_this_week'
    )
    
    this_month = django_filters.BooleanFilter(
        method='filter_this_month'
    )
    
    class Meta:
        model = Message
        fields = [
            'conversation', 'sender', 'sender_username', 'message_type',
            'has_attachment', 'is_reply', 'is_edited', 'is_deleted',
            'created_after', 'created_before', 'content', 'today',
            'this_week', 'this_month'
        ]
    
    def filter_has_attachment(self, queryset, name, value):
        """Filter messages that have attachments"""
        if value:
            return queryset.exclude(attachment='')
        return queryset.filter(attachment='')
    
    def filter_is_reply(self, queryset, name, value):
        """Filter messages that are replies"""
        if value:
            return queryset.exclude(reply_to__isnull=True)
        return queryset.filter(reply_to__isnull=True)
    
    def filter_today(self, queryset, name, value):
        """Filter messages from today"""
        if not value:
            return queryset
        
        from django.utils import timezone
        today = timezone.now().date()
        return queryset.filter(created_at__date=today)
    
    def filter_this_week(self, queryset, name, value):
        """Filter messages from this week"""
        if not value:
            return queryset
        
        from django.utils import timezone
        import datetime
        
        today = timezone.now().date()
        start_week = today - datetime.timedelta(days=today.weekday())
        return queryset.filter(created_at__date__gte=start_week)
    
    def filter_this_month(self, queryset, name, value):
        """Filter messages from this month"""
        if not value:
            return queryset
        
        from django.utils import timezone
        today = timezone.now().date()
        start_month = today.replace(day=1)
        return queryset.filter(created_at__date__gte=start_month)


# chats/views.py

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Conversation, Message, ConversationParticipant, MessageReadStatus
from .serializers import (
    ConversationSerializer, MessageSerializer, MessageCreateSerializer,
    UserSerializer
)
from .filters import ConversationFilter, MessageFilter

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['title', 'participants__username', 'participants__first_name', 'participants__last_name']
    ordering_fields = ['created_at', 'updated_at', 'participant_count']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """Return conversations where user is a participant"""
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True
        ).prefetch_related(
            Prefetch(
                'conversation_participants',
                queryset=ConversationParticipant.objects.select_related('user')
            )
        ).select_related('created_by').distinct().order_by('-updated_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # For direct messages, check if conversation already exists
        if serializer.validated_data.get('conversation_type') == 'direct':
            participant_ids = request.data.get('participant_ids', [])
            if len(participant_ids) == 1:
                # Check for existing direct conversation
                other_user_id = participant_ids[0]
                existing_conversation = Conversation.objects.filter(
                    conversation_type='direct',
                    participants=request.user
                ).filter(
                    participants__id=other_user_id
                ).first()
                
                if existing_conversation:
                    return Response(
                        ConversationSerializer(existing_conversation, context={'request': request}).data,
                        status=status.HTTP_200_OK
                    )
        
        conversation = serializer.save()
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the conversation"""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'member')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is already a participant
        if conversation.participants.filter(id=user_id).exists():
            return Response(
                {'error': 'User is already a participant'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions (only admins/owners can add participants)
        current_participant = conversation.conversation_participants.filter(
            user=request.user
        ).first()
        
        if not current_participant or current_participant.role not in ['admin', 'owner']:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add participant
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=user,
            role=role
        )
        
        return Response({'message': 'Participant added successfully'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a conversation"""
        conversation = self.get_object()
        
        participant = conversation.conversation_participants.filter(
            user=request.user
        ).first()
        
        if not participant:
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.is_active = False
        participant.save()
        
        return Response({'message': 'Left conversation successfully'})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in conversation as read"""
        conversation = self.get_object()
        
        participant = conversation.conversation_participants.filter(
            user=request.user
        ).first()
        
        if participant:
            participant.mark_as_read()
            return Response({'message': 'Conversation marked as read'})
        
        return Response(
            {'error': 'You are not a participant in this conversation'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__username', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """Return messages from conversations where user is a participant"""
        conversation_id = self.request.query_params.get('conversation')
        
        queryset = Message.objects.filter(
            conversation__participants=self.request.user,
            is_deleted=False
        ).select_related('sender', 'conversation', 'reply_to__sender').order_by('created_at')
        
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Send a new message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        # Mark message as read for sender
        MessageReadStatus.objects.create(
            message=message,
            user=request.user
        )
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['patch'])
    def edit(self, request, pk=None):
        """Edit a message"""
        message = self.get_object()
        
        # Only sender can edit their message
        if message.sender != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_content = request.data.get('content')
        if not new_content:
            return Response(
                {'error': 'Content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.edit_message(new_content)
        
        return Response(
            MessageSerializer(message, context={'request': request}).data
        )
    
    @action(detail=True, methods=['delete'])
    def soft_delete(self, request, pk=None):
        """Soft delete a message"""
        message = self.get_object()
        
        # Only sender can delete their message
        if message.sender != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.soft_delete()
        return Response({'message': 'Message deleted successfully'})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        # Create read status if it doesn't exist
        MessageReadStatus.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        return Response({'message': 'Message marked as read'})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages by content"""
        query = request.query_params.get('q', '')
        conversation_id = request.query_params.get('conversation')
        
        if not query:
            return Response(
                {'error': 'Search query is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            content__icontains=query
        )
        
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        # Limit results
        queryset = queryset[:50]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# chats/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet

# Create a router instance
router = DefaultRouter()

# Register our viewsets with the router
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

# Define URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]

app_name = 'chats'


# messaging_app/urls.py (Main project URLs)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chats.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
