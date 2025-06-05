# permissions.py
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from django.core.exceptions import ObjectDoesNotExist


class IsParticipantOfConversation(BasePermission):
    """
    Custom permission to only allow participants of a conversation to access messages.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated before checking object-level permissions.
        """
        # Only authenticated users can access the API
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission to only allow participants of a conversation
        to view, create, update or delete messages.
        """
        # Ensure user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Assuming your model has a conversation field and 
        # conversation has participants (many-to-many relationship)
        try:
            # If obj is a Message, get its conversation
            if hasattr(obj, 'conversation'):
                conversation = obj.conversation
            # If obj is a Conversation itself
            elif hasattr(obj, 'participants'):
                conversation = obj
            else:
                return False
            
            # Check if the authenticated user is a participant in the conversation
            return conversation.participants.filter(id=request.user.id).exists()
            
        except (AttributeError, ObjectDoesNotExist):
            return False


class IsParticipantOfConversationOrReadOnly(BasePermission):
    """
    Custom permission that allows read permissions to any authenticated user,
    but only allows write permissions to participants of the conversation.
    """
    
    def has_permission(self, request, view):
        # Only authenticated users can access the API
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for participants
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            if hasattr(obj, 'conversation'):
                conversation = obj.conversation
            elif hasattr(obj, 'participants'):
                conversation = obj
            else:
                return False
            
            return conversation.participants.filter(id=request.user.id).exists()
            
        except (AttributeError, ObjectDoesNotExist):
            return False


class IsOwnerOrParticipant(BasePermission):
    """
    Custom permission to only allow owners of an object or conversation participants to edit it.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is the owner of the object
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check if user is a participant in the conversation
        try:
            if hasattr(obj, 'conversation'):
                conversation = obj.conversation
                return conversation.participants.filter(id=request.user.id).exists()
        except (AttributeError, ObjectDoesNotExist):
            pass
        
        return False
