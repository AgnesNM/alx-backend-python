from django.urls import path, include
from django_filters import rest_framework as filter

from django_filters.rest_framework import filters
from rest_framework import viewsets, status, permissions

from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .permissions import IsParticipantOfConversation, IsOwnerOrParticipant

from .models import User, Conversation, Message
from .serializers import LoginSerializer, UserSerializer, ConversationSerializer, MessageSerializer, ConversationSerializer, MessageSerializer

from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend

from django.contrib.auth import authenticate
from .pagination import MessagePagination, ConversationPagination

class UserFilter(filter.FilterSet):
    class Meta:
        model = User
        fields = {
            'username': ['iexact', 'icontains'],
            'email': ['iexact', 'icontains'],
            'date_joined': ['exact', 'gte', 'lte'],
        }

class ConversationFilter(filter.FilterSet):
    class Meta:
        model = Conversation
        fields = {
            'name': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
            'participants': ['exact'],
        }

class MessageFilter(filter.FilterSet):
    class Meta:
        model = Message
        fields = {
            'message_body': ['exact', 'icontains'],
            'sent_at': ['exact', 'gte', 'lte'],
            'sender': ['exact'],
            'conversation': ['exact'],
        }

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users in the messaging application.
    Provides CRUD operations for User model with authentication and filtering.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    # filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined']
    ordering = ['username']

    def get_permissions(self):
        """
        Custom permission handling:
        - Allow anyone to create a user (register)
        - Require authentication for updates/deletes
        - Allow read-only access for listing/retrieval
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def create(self, request, *args, **kwargs):
        """
        Create a new user account (registration).
        Automatically generates an auth token for the new user.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create token for the new user
        token, created = Token.objects.get_or_create(user=user)
        
        headers = self.get_success_headers(serializer.data)
        return Response({
            'user': serializer.data,
            'token': token.key
        }, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Update user information.
        Only allows users to update their own profile unless staff/superuser.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Ensure users can only edit their own profile unless they're staff
        if not request.user.is_staff and instance != request.user:
            return Response(
                {'detail': 'You can only edit your own profile.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(UserSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a user account.
        Only allows users to delete their own account unless staff/superuser.
        """
        instance = self.get_object()
        
        # Ensure users can only delete their own account unless they're staff
        if not request.user.is_staff and instance != request.user:
            return Response(
                {'detail': 'You can only delete your own account.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """
        Custom delete handling - also deletes the auth token.
        """
        # Delete the user's token if it exists
        Token.objects.filter(user=instance).delete()
        instance.delete()

    def get_queryset(self):
        """
        Custom queryset handling:
        - Staff can see all users
        - Regular users can only see themselves in detail view
        - Everyone can see all users in list view (if permissions allow)
        """
        queryset = super().get_queryset()
        
        # For detail views, non-staff can only see themselves
        if self.action == 'retrieve' and not self.request.user.is_staff:
            return queryset.filter(pk=self.request.user.pk)
            
        return queryset

class AuthViewSet(viewsets.ViewSet):  # Changed from ModelViewSet to ViewSet
    """
    Custom authentication endpoints that return user data along with tokens.
    """
    serializer_class = LoginSerializer
    permission_classes = []  # No permissions required for login
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Custom login that returns both token and user data.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            request=request,
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return Response(
                {'error': 'Invalid Credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        })
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Custom logout that clears the token.
        """
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({'status': 'logged out'})

class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations in the messaging application.
    Provides CRUD operations for Conversation model.
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    filter_backends = [filter.DjangoFilterBackend]
    filterset_class = ConversationFilter

    def get_queryset(self):
        """
        Override the default queryset to filter conversations based on the authenticated user.
        """
        user = self.request.user
        if user.is_authenticated:
            return Conversation.objects.filter(participants=user)
        return Conversation.objects.none()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        return Response(ConversationSerializer(conversation).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """
        Delete the conversation instance.
        """
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        """
        List all conversations in the messaging application.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific conversation by ID.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_permissions(self):
        """
        Get the permissions for the ConversationViewSet.
        """
        if self.action in ['create', 'update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        """
        Get the serializer class for the ConversationViewSet.
        """
        if self.action in ['create', 'update']:
            return ConversationSerializer
        return ConversationSerializer

class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages in the messaging application.
    Provides CRUD operations for Message model.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filter_backends = [filter.DjangoFilterBackend]
    filterset_class = MessageFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(MessageSerializer(message).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """
        Delete the message instance.
        """
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        """
        List all messages in the messaging application.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific message by ID.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_permissions(self):
        """
        Get the permissions for the MessageViewSet.
        """
        if self.action in ['create', 'update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        """
        Get the serializer class for the MessageViewSet.
        """
        if self.action in ['create', 'update']:
            return MessageSerializer
        return MessageSerializer

# Router configuration
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'conversations', ConversationViewSet)
router.register(r'messages', MessageViewSet)

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]

class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations with custom permissions.
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsParticipantOfConversation]
    
    def get_queryset(self):
        """
        Filter conversations to only show those where the user is a participant.
        """
        if self.request.user.is_authenticated:
            return Conversation.objects.filter(participants=self.request.user)
        return Conversation.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically add the creator as a participant when creating a conversation.
        """
        conversation = serializer.save()
        conversation.participants.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Custom action to add a participant to the conversation.
        Only existing participants can add new ones.
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
                conversation.participants.add(user)
                return Response({'status': 'participant added'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        
        return Response({'error': 'user_id required'}, status=400)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages with custom permissions.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsParticipantOfConversation]
    
    def get_queryset(self):
        """
        Filter messages to only show those from conversations where the user is a participant.
        """
        if self.request.user.is_authenticated:
            return Message.objects.filter(
                conversation__participants=self.request.user
            ).distinct()
        return Message.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically set the user as the sender when creating a message.
        """
        serializer.save(user=self.request.user)
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        You can customize permissions based on the action.
        """
        if self.action == 'create':
            # For creating messages, only check if user is participant
            permission_classes = [IsParticipantOfConversation]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # For editing/deleting, check if user is owner or participant
            permission_classes = [IsOwnerOrParticipant]
        else:
            # For other actions (list, retrieve), use default
            permission_classes = [IsParticipantOfConversation]
        
        return [permission() for permission in permission_classes]


# Alternative approach using function-based views with decorators
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET', 'POST'])
@permission_classes([IsParticipantOfConversation])
def conversation_messages(request, conversation_id):
    """
    Function-based view example with custom permissions.
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Check permission manually (since we're using function-based view)
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Permission denied'}, status=403)
        
        if request.method == 'GET':
            messages = conversation.messages.all()
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = MessageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, conversation=conversation)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
    
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)
        
class MessageViewSet(viewsets.ModelViewSet):
    # Override global pagination for this specific ViewSet
    pagination_class = MessagePagination
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    pagination_class = ConversationPagination
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations with pagination and filtering.
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsParticipantOfConversation]
    pagination_class = ConversationPagination
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['title', 'participants__username']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']  # Default ordering
    
    def get_queryset(self):
        """
        Filter conversations to only show those where the user is a participant.
        """
        if self.request.user.is_authenticated:
            return Conversation.objects.filter(
                participants=self.request.user
            ).prefetch_related('participants', 'messages')
        return Conversation.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically add the creator as a participant when creating a conversation.
        """
        conversation = serializer.save()
        conversation.participants.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Custom action to add a participant to the conversation.
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
                conversation.participants.add(user)
                return Response({'status': 'participant added'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        
        return Response({'error': 'user_id required'}, status=400)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get paginated messages for a specific conversation.
        """
        conversation = self.get_object()
        messages = conversation.messages.all().order_by('created_at')
        
        # Apply filtering to messages
        message_filter = MessageFilter(request.GET, queryset=messages)
        filtered_messages = message_filter.qs
        
        # Paginate the results
        paginator = MessagePagination()
        page = paginator.paginate_queryset(filtered_messages, request)
        
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(filtered_messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_conversations(self, request):
        """
        Get current user's conversations with enhanced filtering.
        """
        queryset = self.get_queryset()
        
        # Apply filters
        filtered_queryset = self.filter_queryset(queryset)
        
        # Paginate
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages with comprehensive pagination and filtering.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsParticipantOfConversation]
    pagination_class = MessagePagination
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'user__username', 'conversation__title']
    ordering_fields = ['created_at', 'updated_at', 'user__username']
    ordering = ['-created_at']  # Default ordering (newest first)
    
    def get_queryset(self):
        """
        Filter messages to only show those from conversations where the user is a participant.
        Optimized with select_related and prefetch_related for better performance.
        """
        if self.request.user.is_authenticated:
            return Message.objects.filter(
                conversation__participants=self.request.user
            ).select_related(
                'user', 'conversation'
            ).prefetch_related(
                'conversation__participants'
            ).distinct()
        return Message.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically set the user as the sender when creating a message.
        """
        serializer.save(user=self.request.user)
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action == 'create':
            permission_classes = [IsParticipantOfConversation]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrParticipant]
        else:
            permission_classes = [IsParticipantOfConversation]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        """
        Get current user's messages (messages they sent).
        """
        queryset = self.get_queryset().filter(user=request.user)
        
        # Apply filters
        filtered_queryset = self.filter_queryset(queryset)
        
        # Paginate
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent messages from the last 24 hours.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        yesterday = timezone.now() - timedelta(days=1)
        queryset = self.get_queryset().filter(created_at__gte=yesterday)
        
        # Apply additional filters
        filtered_queryset = self.filter_queryset(queryset)
        
        # Paginate
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_by_content(self, request):
        """
        Search messages by content with enhanced filtering.
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=400)
        
        queryset = self.get_queryset().filter(content__icontains=query)
        
        # Apply additional filters
        filtered_queryset = self.filter_queryset(queryset)
        
        # Paginate
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)


# Alternative function-based view with pagination and filtering
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_messages_filtered(request, conversation_id):
    """
    Function-based view example with manual pagination and filtering.
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Check permission
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Permission denied'}, status=403)
        
        # Get messages
        messages = conversation.messages.all()
        
        # Apply filtering
        message_filter = MessageFilter(request.GET, queryset=messages)
        filtered_messages = message_filter.qs
        
        # Apply ordering
        ordering = request.GET.get('ordering', '-created_at')
        if ordering:
            filtered_messages = filtered_messages.order_by(ordering)
        
        # Paginate
        paginator = MessagePagination()
        page = paginator.paginate_queryset(filtered_messages, request)
        
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(filtered_messages, many=True)
        return Response(serializer.data)
    
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)
