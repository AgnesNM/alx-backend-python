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
            padding: 20px; 
            margin: 15px 0; 
            background: #ffffff;
            transition: box-shadow 0.2s;
        }
        .conversation-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .conversation-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 15px;
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 10px;
        }
        .conversation-participants { 
            font-weight: bold; 
            color: #495057;
        }
        .conversation-stats { 
            color: #6c757d; 
            font-size: 14px;
        }
        .conversation-preview { 
            margin: 10px 0; 
            color: #495057;
            line-height: 1.5;
        }
        .conversation-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            font-size: 12px;
            color: #6c757d;
        }
        .reply-badge { 
            background: #007bff; 
            color: white; 
            border-radius: 12px; 
            padding: 4px 8px; 
            font-size: 11px;
            font-weight: bold;
        }
        .unread-badge { 
            background: #dc3545; 
            color: white; 
            border-radius: 50%; 
            padding: 2px 6px; 
            font-size: 10px;
        }
        .btn { 
            padding: 8px 15px; 
            margin: 5px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .pagination { text-align: center; margin: 20px 0; }
        .pagination a { 
            padding: 8px 12px; 
            margin: 0 4px; 
            text-decoration: none; 
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .no-conversations {
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💬 Conversations</h1>
        
        <div style="margin-bottom: 20px;">
            <a href="{% url 'send_message' %}" class="btn btn-primary">Start New Conversation</a>
            <a href="{% url 'user_messages' %}" class="btn btn-secondary">All Messages</a>
        </div>

        {% if conversations %}
        {% for conversation in conversations %}
        <div class="conversation-card">
            <div class="conversation-header">
                <div class="conversation-participants">
                    {% if conversation.sender == request.user %}
                        To: {{ conversation.receiver.username }}
                    {% else %}
                        From: {{ conversation.sender.username }}
                    {% endif %}
                </div>
                <div class="conversation-stats">
                    <span class="reply-badge">{{ conversation.total_replies }} replies</span>
                    {% if conversation.thread_messages.0.is_read == False and conversation.thread_messages.0.receiver == request.user %}
                        <span class="unread-badge">New</span>
                    {% endif %}
                </div>
            </div>

            <div class="conversation-preview">
                <strong>Original:</strong> {{ conversation.content|truncatewords:15 }}
                
                {% if conversation.thread_messages %}
                <div style="margin-top: 10px; padding-left: 20px; border-left: 3px solid #e9ecef;">
                    <strong>Latest:</strong> 
                    {{ conversation.thread_messages.0.content|truncatewords:10 }}
                    <em>by {{ conversation.thread_messages.0.sender.username }}</em>
                </div>
                {% endif %}
            </div>

            <div class="conversation-meta">
                <div>
                    Started: {{ conversation.timestamp|date:"M d, Y H:i" }}
                    {% if conversation.thread_messages %}
                        | Last activity: {{ conversation.thread_messages.0.timestamp|date:"M d, Y H:i" }}
                    {% endif %}
                </div>
                <div>
                    <a href="{% url 'view_conversation' conversation.id %}" class="btn btn-primary">
                        View Thread
                    </a>
                </div>
            </div>
        </div>
        {% endfor %}

        <!-- Pagination -->
        {% if conversations.has_other_pages %}
        <div class="pagination">
            {% if conversations.has_previous %}
                <a href="?page=1">First</a>
                <a href="?page={{ conversations.previous_page_number }}">Previous</a>
            {% endif %}
            
            <span>Page {{ conversations.number }} of {{ conversations.paginator.num_pages }}</span>
            
            {% if conversations.has_next %}
                <a href="?page={{ conversations.next_page_number }}">Next</a>
                <a href="?page={{ conversations.paginator.num_pages }}">Last</a>
            {% endif %}
        </div>
        {% endif %}

        {% else %}
        <div class="no-conversations">
            <h3>📭 No conversations found</h3>
            <p>Start a new conversation to see it here.</p>
            <a href="{% url 'send_message' %}" class="btn btn-primary">Send First Message</a>
        </div>
        {% endif %}
    </div>
</body>
</html>

<!-- templates/messaging/conversation_thread.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Conversation Thread</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f8f9fa;
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .thread-header {
            background: #e7f3ff;
            border: 1px solid #b8daff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .participants {
            margin-top: 10px;
            font-size: 14px;
        }
        .message-item { 
            border: 1px solid #dee2e6; 
            border-radius: 8px; 
            padding: 15px; 
            margin: 10px 0; 
            background: #ffffff;
            position: relative;
        }
        .message-item.reply {
            margin-left: 20px;
            border-left: 4px solid #007bff;
            background: #f8f9fa;
        }
        .message-item.reply-level-2 { margin-left: 40px; }
        .message-item.reply-level-3 { margin-left: 60px; }
        .message-item.reply-level-4 { margin-left: 80px; }
        .message-item.reply-level-5 { margin-left: 100px; }
        
        .message-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 10px;
            font-size: 14px;
        }
        .message-sender { 
            font-weight: bold; 
            color: #495057;
        }
        .message-time { 
            color: #6c757d; 
            font-size: 12px;
        }
        .message-content { 
            margin: 10px 0; 
            line-height: 1.6;
            color: #495057;
        }
        .message-actions {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e9ecef;
        }
        .reply-form {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
            display: none;
        }
        .reply-form textarea {
            width: 100%;
            min-height: 80px;
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            resize: vertical;
        }
        .btn { 
            padding: 6px 12px; 
            margin: 3px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-sm { padding: 4px 8px; font-size: 12px; }
        .edit-indicator { 
            color: #fd7e14; 
            font-size: 11px; 
            font-style: italic;
        }
        .reply-indicator {
            color: #007bff;
            font-size: 11px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="thread-header">
            <h1>💬 Conversation Thread</h1>
            <div>
                <strong>Started by:</strong> {{ thread_root.sender.username }} 
                <strong>to:</strong> {{ thread_root.receiver.username }}
            </div>
            <div class="participants">
                <strong>Participants:</strong> 
                {% for participant in participants %}
                    {{ participant.username }}{% if not forloop.last %}, {% endif %}
                {% endfor %}
            </div>
        </div>

        {% for message_data in threaded_messages %}
            {% include 'messaging/message_thread_item.html' with message_data=message_data %}
        {% endfor %}

        <div style="margin-top: 30px; text-align: center;">
            <a href="{% url 'conversations_list' %}" class="btn btn-secondary">Back to Conversations</a>
        </div>
    </div>

    <script>
        function toggleReplyForm(messageId) {
            const form = document.getElementById(`reply-form-${messageId}`);
            if (form.style.display === 'none' || form.style.display === '') {
                form.style.display = 'block';
                document.getElementById(`reply-content-${messageId}`).focus();
            } else {
                form.style.display = 'none';
            }
        }

        async function submitReply(messageId) {
            const content = document.getElementById(`reply-content-${messageId}`).value.trim();
            
            if (!content) {
                alert('Please enter a reply message');
                return;
            }

            try {
                const response = await fetch(`/reply/${messageId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `content=${encodeURIComponent(content)}`
                });

                const data = await response.json();

                if (data.status === 'success') {
                    location.reload(); // Refresh to show new reply
                } else {
                    alert(data.message || 'Error sending reply');
                }
            } catch (error) {
                alert('Error sending reply');
                console.error(error);
            }
        }

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    </script>
</body>
</html>

<!-- templates/messaging/message_thread_item.html -->
<div class="message-item {% if message_data.message.parent_message %}reply reply-level-{{ message_data.message.depth_level }}{% endif %}" 
     id="message-{{ message_data.message.id }}">
    
    <div class="message-header">
        <div class="message-sender">
            {{ message_data.message.sender.username }}
            {% if message_data.message.parent_message %}
                <span class="reply-indicator">
                    replied to {{ message_data.message.parent_message.sender.username }}
                </span>
            {% endif %}
        </div>
        <div class="message-time">
            {{ message_data.message.timestamp|date:"M d, Y H:i" }}
            {% if message_data.message.edited %}
                <span class="edit-indicator">(edited)</span>
            {% endif %}
        </div>
    </div>

    <div class="message-content">
        {{ message_data.message.content|linebreaks }}
    </div>

    <div class="message-actions">
        {% if can_reply %}
        <button class="btn btn-primary btn-sm" onclick="toggleReplyForm({{ message_data.message.id }})">
            💬 Reply
        </button>
        {% endif %}
        
        {% if message_data.message.sender == request.user %}
        <a href="{% url 'edit_message' message_data.message.id %}" class="btn btn-secondary btn-sm">
            ✏️ Edit
        </a>
        {% endif %}
        
        <a href="{% url 'message_history' message_data.message.id %}" class="btn btn-secondary btn-sm">
            📋 History
        </a>

        {% if message_data.message.reply_count > 0 %}
        <span class="btn btn-sm" style="background: #e9ecef; color: #495057;">
            {{ message_data.message.reply_count }} repl{{ message_data.message.reply_count|pluralize:"y,ies" }}
        </span>
        {% endif %}
    </div>

    {% if can_reply %}
    <div class="reply-form" id="reply-form-{{ message_data.message.id }}">
        <textarea id="reply-content-{{ message_data.message.id }}" 
                  placeholder="Write your reply..."></textarea>
        <div style="margin-top: 10px;">
            <button class="btn btn-success" onclick="submitReply({{ message_data.message.id }})">
                Send Reply
            </button>
            <button class="btn btn-secondary" onclick="toggleReplyForm({{ message_data.message.id }})">
                Cancel
            </button>
        </div>
    </div>
    {% endif %}

    <!-- Render nested replies -->
    {% if message_data.replies %}
        {% for reply_data in message_data.replies %}
            {% include 'messaging/message_thread_item.html' with message_data=reply_data %}
        {% endfor %}
    {% endif %}
</div>
