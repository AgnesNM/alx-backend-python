# ===================
# urls.py - Updated URL patterns for threading
# ===================
from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs
    path('send-message/', views.send_message, name='send_message'),
    path('edit-message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('message-history/<int:message_id>/', views.message_history, name='message_history'),
    path('messages/', views.user_messages, name='user_messages'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/unread-count/', views.unread_notifications_count, name='unread_count'),
    
    # User deletion URLs
    path('delete-account/', views.delete_user_account, name='delete_user_account'),
    path('account-deleted/', views.account_deleted_success, name='account_deleted_success'),
    path('admin/delete-user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/deletion-logs/', views.deletion_logs, name='deletion_logs'),
    
    # NEW: Threading URLs
    path('conversations/', views.conversations_list, name='conversations_list'),
    path('conversation/<int:message_id>/', views.view_conversation, name='view_conversation'),
    path('reply/<int:message_id>/', views.reply_to_message, name='reply_to_message'),
    path('api/thread/<int:thread_root_id>/', views.get_thread_messages, name='get_thread_messages'),
]


# ===================
# Templates for Threaded Conversations
# ===================

# templates/messaging/conversations_list.html
<!DOCTYPE html>
<html>
<head>
    <title>Conversations</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f8f9fa;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .conversation-card { 
            border: 1px solid #dee2e6; 
            border-radius: 8px; 
            padding
