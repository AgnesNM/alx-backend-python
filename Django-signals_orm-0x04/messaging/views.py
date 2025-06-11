# views.py - Complete views with query optimization for threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Prefetch, Count, Max
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password
from .models import Message, Notification, MessageHistory, UserDeletionLog


@login_required
def send_message(request):
    """View to send a new message or reply"""
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        parent_message_id = request.POST.get('parent_message_id')  # For replies
        
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            
            # Handle parent message for replies with optimization
            parent_message = None
            if parent_message_id:
                parent_message = get_object_or_404(
                    Message.objects.select_related('sender', 'receiver'),  # ✅ select_related
                    id=parent_message_id
                )
                # Ensure user has permission to reply to this message
                if request.user not in [parent_message.sender, parent_message.receiver]:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'You do not have permission to reply to this message'
                    })
            
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                parent_message=parent_message
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Reply sent successfully' if parent_message else 'Message sent successfully',
                'message_id': message.id,
                'is_reply': bool(parent_message)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def view_conversation(request, message_id):
    """View to display a threaded conversation with optimized queries"""
    # Get the root message with optimized queries
    root_message = get_object_or_404(
        Message.objects.select_related('sender', 'receiver', 'thread_root')  # ✅ select_related
                      .prefetch_related(  # ✅ prefetch_related
                          'replies__sender', 
                          'replies__receiver',
                          'replies__parent_message'
                      ),
        id=message_id
    )
    
    # Ensure user has permission to view this conversation
    if request.user not in [root_message.sender, root_message.receiver]:
        # Check if user is part of any message in the thread
        thread_root = root_message.get_thread_root()
        thread_participants = thread_root.get_conversation_participants()
        if request.user not in thread_participants:
            raise Http404("You don't have permission to view this conversation")
    
    # Get the actual root of the thread
    thread_root = root_message.get_thread_root()
    
    # Get all messages in the thread with optimized queries
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related(  # ✅ select_related for foreign keys
        'sender', 
        'receiver', 
        'parent_message',
        'parent_message__sender',
        'parent_message__receiver'
    ).prefetch_related(  # ✅ prefetch_related for reverse foreign keys
        'replies__sender', 
        'replies__receiver',
        'history__edited_by'
    ).order_by('timestamp')
    
    # Build threaded structure
    threaded_messages = build_threaded_structure(thread_messages)
    
    # Mark messages as read for the current user (optimized query)
    unread_message_ids = thread_messages.filter(
        receiver=request.user,
        is_read=False
    ).values_list('id', flat=True)
    
    if unread_message_ids:
        Message.objects.filter(id__in=unread_message_ids).update(is_read=True)
    
    context = {
        'thread_root': thread_root,
        'threaded_messages': threaded_messages,
        'can_reply': True,  # User is part of conversation
        'participants': thread_root.get_conversation_participants(),
    }
    
    return render(request, 'messaging/conversation_thread.html', context)


@login_required
def conversations_list(request):
    """View to display user's conversations with optimized queries"""
    # Get thread root messages where user is participant with optimization
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        parent_message__isnull=True  # Only root messages
    ).select_related(  # ✅ select_related for foreign keys
        'sender', 
        'receiver',
        'thread_root'
    ).prefetch_related(  # ✅ prefetch_related for related messages
        Prefetch(
            'thread_messages',
            queryset=Message.objects.select_related('sender', 'receiver')  # ✅ select_related in Prefetch
                                  .order_by('-timestamp')[:3]  # Last 3 messages
        ),
        Prefetch(
            'replies',
            queryset=Message.objects.select_related('sender', 'receiver')  # ✅ select_related in Prefetch
        )
    ).annotate(
        total_replies=Count('thread_messages'),
        latest_activity=Max('thread_messages__timestamp')
    ).order_by('-latest_activity')
    
    # Paginate conversations
    paginator = Paginator(conversations, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/conversations_list.html', {
        'conversations': page_obj
    })


@login_required
def reply_to_message(request, message_id):
    """View to reply to a specific message with optimization"""
    parent_message = get_object_or_404(
        Message.objects.select_related(  # ✅ select_related
            'sender', 
            'receiver', 
            'thread_root',
            'thread_root__sender',
            'thread_root__receiver'
        ),
        id=message_id
    )
    
    # Check permission
    if request.user not in [parent_message.sender, parent_message.receiver]:
        thread_root = parent_message.get_thread_root()
        thread_participants = thread_root.get_conversation_participants()
        if request.user not in thread_participants:
            raise Http404("You don't have permission to reply to this message")
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if content:
            # Determine receiver (reply to sender if we're the receiver, otherwise to receiver)
            if request.user == parent_message.receiver:
                receiver = parent_message.sender
            else:
                receiver = parent_message.receiver
            
            reply = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                parent_message=parent_message
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Reply sent successfully',
                'reply_id': reply.id
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Reply content cannot be empty'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def get_thread_messages(request, thread_root_id):
    """API endpoint to get all messages in a thread with optimization"""
    thread_root = get_object_or_404(
        Message.objects.select_related('sender', 'receiver'),  # ✅ select_related
        id=thread_root_id
    )
    
    # Check permission
    thread_participants = thread_root.get_conversation_participants()
    if request.user not in thread_participants:
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        })
    
    # Get all messages in thread with optimized queries
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related(  # ✅ select_related for foreign keys
        'sender', 
        'receiver', 
        'parent_message',
        'parent_message__sender'
    ).prefetch_related(  # ✅ prefetch_related for reverse relationships
        'replies',
        'history'
    ).order_by('timestamp')
    
    messages_data = []
    for msg in thread_messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'receiver': msg.receiver.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'parent_id': msg.parent_message.id if msg.parent_message else None,
            'depth_level': msg.depth_level,
            'reply_count': msg.reply_count,
            'edited': msg.edited,
            'is_read': msg.is_read
        })
    
    return JsonResponse({
        'status': 'success',
        'messages': messages_data,
        'total_count': len(messages_data)
    })


@login_required
def user_messages(request):
    """View to display user's messages with edit indicators and optimization"""
    messages_list = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related(  # ✅ select_related for foreign keys
        'sender', 
        'receiver',
        'parent_message',
        'thread_root'
    ).prefetch_related(  # ✅ prefetch_related for reverse relationships
        'replies__sender',
        'replies__receiver',
        'history__edited_by'
    ).order_by('-timestamp')
    
    # Paginate messages
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/messages_list.html', {
        'messages': page_obj
    })


@login_required
def edit_message(request, message_id):
    """View to edit an existing message with optimization"""
    message = get_object_or_404(
        Message.objects.select_related('sender', 'receiver')  # ✅ select_related
                      .prefetch_related('history'),  # ✅ prefetch_related
        id=message_id, 
        sender=request.user
    )
    
    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        
        if new_content and new_content != message.content:
            message.content = new_content
            message.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message updated successfully',
                'edited': True,
                'edit_count': message.get_edit_count()
            })
        elif new_content == message.content:
            return JsonResponse({
                'status': 'info',
                'message': 'No changes made to the message'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Message content cannot be empty'
            })
    
    return JsonResponse({
        'status': 'success',
        'content': message.content,
        'edited': message.edited,
        'edit_count': message.get_edit_count()
    })


@login_required
def message_history(request, message_id):
    """View to display message edit history with optimization"""
    message = get_object_or_404(
        Message.objects.select_related(  # ✅ select_related
            'sender', 
            'receiver',
            'parent_message',
            'thread_root'
        ),
        id=message_id
    )
    
    if request.user != message.sender and request.user != message.receiver:
        raise Http404("You don't have permission to view this message history")
    
    # Get all history entries for this message with optimization
    history_entries = MessageHistory.objects.filter(
        message=message
    ).select_related(  # ✅ select_related
        'edited_by',
        'message__sender',
        'message__receiver'
    ).order_by('-edited_at')
    
    # Paginate history
    paginator = Paginator(history_entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'message': message,
        'history_entries': page_obj,
        'can_edit': request.user == message.sender
    }
    
    return render(request, 'messaging/message_history.html', context)


@login_required
def notifications_list(request):
    """View to display user's notifications with optimization"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related(  # ✅ select_related
        'message__sender',
        'message__receiver',
        'message__parent_message'
    ).prefetch_related(  # ✅ prefetch_related
        'message__replies'
    )
    
    # Paginate notifications
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/notifications.html', {
        'notifications': page_obj
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(
        Notification.objects.select_related('user'),  # ✅ select_related
        id=notification_id, 
        user=request.user
    )
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'status': 'success'})


@login_required
def unread_notifications_count(request):
    """API endpoint to get count of unread notifications"""
    count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': count})


@login_required
def delete_user_account(request):
    """View to handle user account deletion"""
    if request.method == 'GET':
        # Show deletion confirmation page with optimized queries
        user_stats = {
            'messages_sent': request.user.sent_messages.count(),
            'messages_received': request.user.received_messages.count(),
            'notifications': request.user.notifications.count(),
            'message_edits': request.user.message_edits.count(),
        }
        
        return render(request, 'messaging/delete_account.html', {
            'user_stats': user_stats
        })
    
    elif request.method == 'POST':
        # Process deletion request
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')
        deletion_reason = request.POST.get('reason', '')
        
        # Validate password
        if not check_password(password, request.user.password):
            messages.error(request, 'Invalid password. Please try again.')
            return redirect('delete_user_account')
        
        # Validate confirmation
        if confirmation.lower() != 'delete my account':
            messages.error(request, 'Please type "delete my account" to confirm.')
            return redirect('delete_user_account')
        
        # Set custom attributes for the deletion signal
        request.user._deleted_by = 'self'
        request.user._deletion_reason = deletion_reason
        
        # Get user info before deletion
        username = request.user.username
        
        try:
            with transaction.atomic():
                # Logout the user first
                logout(request)
                
                # Delete the user (this will trigger CASCADE deletion of related objects)
                User.objects.filter(username=username).delete()
                
                messages.success(request, 'Your account has been successfully deleted.')
                return redirect('account_deleted_success')
                
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your account: {str(e)}')
            return redirect('delete_user_account')


def account_deleted_success(request):
    """View to show successful account deletion"""
    return render(request, 'messaging/account_deleted.html')


@login_required
def admin_delete_user(request, user_id):
    """Admin view to delete a user account with optimization"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    target_user = get_object_or_404(
        User.objects.select_related()  # ✅ select_related
                   .prefetch_related(  # ✅ prefetch_related
                       'sent_messages',
                       'received_messages',
                       'notifications',
                       'message_edits'
                   ),
        id=user_id
    )
    
    if request.method == 'POST':
        deletion_reason = request.POST.get('reason', 'Deleted by admin')
        
        # Set custom attributes for the deletion signal
        target_user._deleted_by = request.user.username
        target_user._deletion_reason = deletion_reason
        
        username = target_user.username
        
        try:
            with transaction.atomic():
                target_user.delete()
                
                messages.success(request, f'User {username} has been successfully deleted.')
                return redirect('admin_user_list')
                
        except Exception as e:
            messages.error(request, f'An error occurred while deleting user {username}: {str(e)}')
    
    user_stats = {
        'messages_sent': target_user.sent_messages.count(),
        'messages_received': target_user.received_messages.count(),
        'notifications': target_user.notifications.count(),
        'message_edits': target_user.message_edits.count(),
    }
    
    return render(request, 'messaging/admin_delete_user.html', {
        'target_user': target_user,
        'user_stats': user_stats
    })


@login_required
def deletion_logs(request):
    """View to show user deletion logs (admin only)"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    logs = UserDeletionLog.objects.all().order_by('-deleted_at')
    
    # Paginate logs
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/deletion_logs.html', {
        'logs': page_obj
    })


def build_threaded_structure(messages):
    """
    Build a nested structure for threaded messages using optimized queries.
    Returns a list of message dictionaries with nested replies.
    """
    message_dict = {}
    root_messages = []
    
    # First pass: create message objects and index them
    for message in messages:
        message_data = {
            'message': message,
            'replies': []
        }
        message_dict[message.id] = message_data
        
        if message.parent_message is None:
            root_messages.append(message_data)
    
    # Second pass: build the tree structure
    for message in messages:
        if message.parent_message:
            parent_data = message_dict.get(message.parent_message.id)
            if parent_data:
                parent_data['replies'].append(message_dict[message.id])
    
    return root_messages


@login_required
def search_conversations(request):
    """Search through conversations with optimization"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'messaging/search_results.html', {
            'query': query,
            'results': [],
            'total_count': 0
        })
    
    # Search in messages with optimization
    results = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        content__icontains=query
    ).select_related(  # ✅ select_related
        'sender',
        'receiver', 
        'parent_message',
        'thread_root'
    ).prefetch_related(  # ✅ prefetch_related
        'replies__sender',
        'thread_messages__sender'
    ).order_by('-timestamp')
    
    # Paginate results
    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/search_results.html', {
        'query': query,
        'results': page_obj,
        'total_count': results.count()
    })
