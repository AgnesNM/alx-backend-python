from .models import User, Conversation, Message
from rest_framework import serializers
from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'password', 
                 'first_name', 'last_name', 'phone_number', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'user_id': {'read_only': True},
            'date_joined': {'read_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', '')
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")



class MessageSerializer(serializers.Serializer):
    """
    Serializer for the Message model.
    Converts Message instances to and from JSON format.
    """

    message_id = serializers.UUIDField(read_only=True)
    message_body = serializers.CharField(required=True, allow_blank=False)
    sent_at = serializers.DateTimeField(read_only=True)
    sender = UserSerializer(read_only=True)


    def validate_message_body(self, value):
        """
        Validate that the message body is not empty.
        """
        if not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        return value
    class Meta:
        model = Message
        fields = ['message_id', 'message_body', 'sent_at', 'conversation', 'sender']
        read_only_fields = ['message_id', 'sent_at']
    
    
class ConversationSerializer(serializers.Serializer):
    """
    Serializer for the Chat model.
    Converts Chat instances to and from JSON format.
    """
    messages = MessageSerializer(many=True, read_only=True)
    conversation_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    participants = UserSerializer(many=True, read_only=True)
    total_messages = serializers.SerializerMethodField()
    def get_total_messages(self, obj):
        """
        Return the total number of messages in the conversation.
        """
        return obj.messages.count()
    
    class Meta:
        model = Conversation
        fields = ['conversation_id', 'name', 'participants']
        read_only_fields = ['conversation_id']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'participants': {'read_only': True}
        }
        depth = 1
    def validate_name(self, value):
        """
        Validate that the conversation name is not empty.
        """
        if not value.strip():
            raise serializers.ValidationError("Conversation name cannot be empty.")
        return value
    def validate_participants(self, value):
        """
        Validate that at least one participant is provided.
        """
        if not value:
            raise serializers.ValidationError("At least one participant is required.")
        return value
        
