# tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
import json

from .models import Message, Notification


class MessageModelTest(TestCase):
    """Test cases for the Message model"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='receiver',
            email='receiver@test.com',
            password='testpass123'
        )
    
    def test_message_creation(self):
        """Test that a message can be created successfully"""
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Hello, this is a test message!"
        )
        
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.receiver, self.user2)
        self.assertEqual(message.content, "Hello, this is a test message!")
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.timestamp)
    
    def test_message_str_representation(self):
        """Test the string representation of a message"""
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Test message"
        )
        
        expected_str = f"Message from {self.user1.username} to {self.user2.username}"
        self.assertEqual(str(message), expected_str)
    
    def test_message_ordering(self):
        """Test that messages are ordered by timestamp (newest first)"""
        # Create messages with different timestamps
        message1 = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="First message"
        )
        
        message2 = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Second message"
        )
        
        messages = Message.objects.all()
        self.assertEqual(messages[0], message2)  # Newest first
        self.assertEqual(messages[1], message1)


class NotificationModelTest(TestCase):
    """Test cases for the Notification model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        
        self.message = Message.objects.create(
            sender=self.sender,
            receiver=self.user,
            content="Test message for notification"
        )
    
    def test_notification_creation(self):
        """Test that a notification can be created successfully"""
        notification = Notification.objects.create(
            user=self.user,
            message=self.message,
            title="New Message",
            content="You have a new message",
            notification_type='message'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, self.message)
        self.assertEqual(notification.title, "New Message")
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.notification_type, 'message')
    
    def test_notification_str_representation(self):
        """Test the string representation of a notification"""
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            content="Test content"
        )
        
        expected_str = f"Notification for {self.user.username}: Test Notification"
        self.assertEqual(str(notification), expected_str)
    
    def test_notification_without_message(self):
        """Test creating a notification without a linked message"""
        notification = Notification.objects.create(
            user=self.user,
            title="System Notification",
            content="System maintenance scheduled",
            notification_type='system'
        )
        
        self.assertIsNone(notification.message)
        self.assertEqual(notification.notification_type, 'system')


class MessageSignalTest(TestCase):
    """Test cases for message signals that create notifications"""
    
    def setUp(self):
        """Set up test data"""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            email='receiver@test.com',
            password='testpass123'
        )
    
    def test_notification_created_on_message_creation(self):
        """Test that a notification is automatically created when a message is sent"""
        # Initially no notifications
        self.assertEqual(Notification.objects.count(), 0)
        
        # Create a message
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Hello, this should trigger a notification!"
        )
        
        # Check that a notification was created
        self.assertEqual(Notification.objects.count(), 1)
        
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.receiver)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.sender.username, notification.title)
        self.assertIn(message.content[:50], notification.content)
    
    def test_no_notification_for_self_message(self):
        """Test that no notification is created when user sends message to themselves"""
        # Create a message to self
        Message.objects.create(
            sender=self.sender,
            receiver=self.sender,  # Same user
            content="Message to myself"
        )
        
        # No notification should be created
        self.assertEqual(Notification.objects.count(), 0)
    
    def test_notification_content_truncation(self):
        """Test that long message content is truncated in notifications"""
        long_content = "This is a very long message content that should be truncated in the notification because it exceeds the 50 character limit that we have set for the preview."
        
        Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content=long_content
        )
        
        notification = Notification.objects.first()
        self.assertIn("...", notification.content)
        self.assertLess(len(notification.content.split('"')[1]), len(long_content))
    
    def test_notification_not_created_on_message_update(self):
        """Test that notifications are not created when existing messages are updated"""
        # Create initial message (this will create 1 notification)
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Original content"
        )
        
        self.assertEqual(Notification.objects.count(), 1)
        
        # Update the message
        message.content = "Updated content"
        message.save()
        
        # Should still be only 1 notification
        self.assertEqual(Notification.objects.count(), 1)


class MessageViewTest(TestCase):
    """Test cases for message-related views"""
    
    def setUp(self):
        """Set up test data and client"""
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
    
    def test_send_message_view_authenticated(self):
        """Test sending a message when authenticated"""
        self.client.login(username='user1', password='testpass123')
        
        response = self.client.post('/send-message/', {
            'receiver_id': self.user2.id,
            'content': 'Test message via view'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Check that message was created
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.receiver, self.user2)
    
    def test_send_message_view_unauthenticated(self):
        """Test that unauthenticated users cannot send messages"""
        response = self.client.post('/send-message/', {
            'receiver_id': self.user2.id,
            'content': 'Test message'
        })
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_notifications_list_view(self):
        """Test the notifications list view"""
        self.client.login(username='user2', password='testpass123')
        
        # Create some notifications
        Notification.objects.create(
            user=self.user2,
            title="Test Notification 1",
            content="Content 1"
        )
        Notification.objects.create(
            user=self.user2,
            title="Test Notification 2",
            content="Content 2"
        )
        
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Notification 1")
        self.assertContains(response, "Test Notification 2")
    
    def test_mark_notification_read(self):
        """Test marking a notification as read"""
        self.client.login(username='user2', password='testpass123')
        
        notification = Notification.objects.create(
            user=self.user2,
            title="Test Notification",
            content="Test content"
        )
        
        self.assertFalse(notification.is_read)
        
        response = self.client.post(f'/notification/{notification.id}/read/')
        self.assertEqual(response.status_code, 200)
        
        # Check that notification is marked as read
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
    
    def test_unread_notifications_count(self):
        """Test the unread notifications count API"""
        self.client.login(username='user2', password='testpass123')
        
        # Create notifications (some read, some unread)
        Notification.objects.create(
            user=self.user2,
            title="Unread 1",
            content="Content",
            is_read=False
        )
        Notification.objects.create(
            user=self.user2,
            title="Unread 2", 
            content="Content",
            is_read=False
        )
        Notification.objects.create(
            user=self.user2,
            title="Read 1",
            content="Content",
            is_read=True
        )
        
        response = self.client.get('/api/unread-count/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['unread_count'], 2)


class UtilityFunctionTest(TestCase):
    """Test cases for utility functions"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_create_custom_notification(self):
        """Test creating custom notifications via utility function"""
        from .utils import create_custom_notification
        
        notification = create_custom_notification(
            user=self.user,
            title="Custom Notification",
            content="This is a custom notification",
            notification_type='system'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, "Custom Notification")
        self.assertEqual(notification.notification_type, 'system')
        self.assertIsNone(notification.message)
    
    def test_get_unread_notifications(self):
        """Test getting unread notifications for a user"""
        from .utils import get_unread_notifications
        
        # Create mixed read/unread notifications
        Notification.objects.create(
            user=self.user,
            title="Unread",
            content="Content",
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title="Read",
            content="Content", 
            is_read=True
        )
        
        unread = get_unread_notifications(self.user)
        self.assertEqual(unread.count(), 1)
        self.assertEqual(unread.first().title, "Unread")
    
    def test_mark_all_notifications_read(self):
        """Test marking all notifications as read for a user"""
        from .utils import mark_all_notifications_read
        
        # Create unread notifications
        Notification.objects.create(
            user=self.user,
            title="Unread 1",
            content="Content",
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title="Unread 2",
            content="Content",
            is_read=False
        )
        
        # Mark all as read
        updated_count = mark_all_notifications_read(self.user)
        self.assertEqual(updated_count, 2)
        
        # Verify all are read
        unread_count = Notification.objects.filter(
            user=self.user, 
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)


class IntegrationTest(TestCase):
    """Integration tests for the complete notification system"""
    
    def setUp(self):
        """Set up test data"""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            email='receiver@test.com',
            password='testpass123'
        )
        self.client = Client()
    
    def test_complete_message_notification_flow(self):
        """Test the complete flow from message creation to notification handling"""
        self.client.login(username='sender', password='testpass123')
        
        # Step 1: Send a message
        response = self.client.post('/send-message/', {
            'receiver_id': self.receiver.id,
            'content': 'Hello, this is an integration test message!'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Verify message was created
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        
        # Step 3: Verify notification was automatically created
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        
        self.assertEqual(notification.user, self.receiver)
        self.assertEqual(notification.message, message)
        self.assertFalse(notification.is_read)
        
        # Step 4: Login as receiver and check notifications
        self.client.login(username='receiver', password='testpass123')
        
        # Check unread count
        response = self.client.get('/api/unread-count/')
        data = json.loads(response.content)
        self.assertEqual(data['unread_count'], 1)
        
        # Step 5: Mark notification as read
        response = self.client.post(f'/notification/{notification.id}/read/')
        self.assertEqual(response.status_code, 200)
        
        # Step 6: Verify notification is now read
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        
        # Check unread count is now 0
        response = self.client.get('/api/unread-count/')
        data = json.loads(response.content)
        self.assertEqual(data['unread_count'], 0)
