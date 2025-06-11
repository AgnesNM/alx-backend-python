# views.py - Complete views using custom managers with cache_page
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
from django.views.decorators.cache import cache_page  # ✅ Import cache_page
from django.core.cache import cache  # ✅ Import cache for manual caching
from django.views.decorators.vary import vary_on_headers
from .models import Message, Notification, MessageHistory, UserDeletionLog


# ✅ Using @cache_page(60) decorator - 60 seconds cache timeout
@cache_page(60)  # Cache for 60 seconds
@login_required
def conversations_list_cached(request):
    """
    Cached view to display user's conversations with 60 second cache timeout.
    This view demonstrates basic page-level caching using @cache_page decorator.
    """
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        parent_message__isnull=True
    ).select_related(
        'sender', 'receiver', 'thread_root'
    ).prefetch_related(
        Prefetch(
            'thread_messages',
            queryset=Message.objects.select_related('sender', 'receiver')
                                  .order_by('-timestamp')[:3]
        )
    ).annotate(
        total_replies=Count('thread_messages')
    ).order_by('-timestamp')
    
    # Add unread count to each conversation using custom manager
    for conversation in conversations:
        conversation.unread_count = Message.unread.for_user(request.user).filter(
            Q(id=conversation.id) | Q(thread_root=conversation)
        ).count()
    
    # Paginate conversations
    paginator = Paginator(conversations, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get total unread count using custom manager
    total_unread = Message.unread.unread_count_for_user(request.user)
    
    context = {
        'conversations': page_obj,
        'total_unread': total_unread,
        'is_cached': True,  # Indicator for template
        'cache_timeout': 60,
    }
    
    return render(request, 'messaging/conversations_list_cached.html', context)


# ✅ Another view with @cache_page(60) decorator
@cache_page(60)  # Cache for 60 seconds
@vary_on_headers('User-Agent')  # Vary cache by User-Agent
@login_required
def view_conversation_cached(request, message_id):
    """
    Cached view to display a threaded conversation with 60 second cache timeout.
    Uses @cache_page decorator for automatic caching.
    """
    root_message = get_object_or_404(
        Message.objects.select_related('sender', 'receiver', 'thread_root')
                      .prefetch_related('replies__sender', 'replies__receiver'),
        id=message_id
    )
    
    # Permission check
    if request.user not in [root_message.sender, root_message.receiver]:
        thread_root = root_message.get_thread_root()
        thread_participants = thread_root.get_conversation_participants()
        if request.user not in thread_participants:
            raise Http404("You don't have permission to view this conversation")
    
    thread_root = root_message.get_thread_root()
    
    # Get all messages in the thread
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related('sender', 'receiver', 'parent_message')
    
    # Build threaded structure
    threaded_messages = build_threaded_structure(thread_messages)
    
    context = {
        'thread_root': thread_root,
        'threaded_messages': threaded_messages,
        'can_reply': True,
        'participants': thread_root.get_conversation_participants(),
        'is_cached': True,
        'cache_timeout': 60,
    }
    
    return render(request, 'messaging/conversation_thread_cached.html', context)


# ✅ Dashboard view with @cache_page(60)
@cache_page(60)  # Cache for 60 seconds
@login_required
def dashboard_view_cached(request):
    """
    Dashboard view with @cache_page caching for 60 seconds.
    """
    # Using custom managers with optimization
    unread_count = Message.unread.unread_count_for_user(request.user)
    recent_unread = Message.unread.recent_unread_for_user(request.user, limit=5)
    unread_threads = Message.unread.unread_threads_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp'
    ).select_related('sender')[:3]
    
    context = {
        'unread_count': unread_count,
        'recent_unread': recent_unread,
        'unread_threads': unread_threads,
        'is_cached': True,
        'cache_timeout': 60,
        'cached_at': timezone.now(),
        'from_cache': False  # Will be True if served from cache
    }
    
    return render(request, 'messaging/dashboard_cached.html', context)


@login_required
def unread_inbox(request):
    """
    View to display only unread messages using custom manager and .only() optimization.
    """
    # ✅ Using custom manager with .only() optimization
    unread_messages = Message.unread.unread_inbox_optimized(request.user)
    
    # Paginate unread messages
    paginator = Paginator(unread_messages, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count for badge using custom manager
    unread_count = Message.unread.unread_count_for_user(request.user)
    
    context = {
        'unread_messages': page_obj,
        'unread_count': unread_count,
        'page_title': 'Unread Messages'
    }
    
    return render(request, 'messaging/unread_inbox.html', context)


@login_required
def unread_inbox_simple(request):
    """
    Simple unread inbox view using Message.unread.unread_for_user
    """
    # ✅ Using Message.unread.unread_for_user method
    unread_messages = Message.unread.unread_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'parent_message'
    ).select_related('sender', 'parent_message')
    
    # Paginate unread messages
    paginator = Paginator(unread_messages, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_messages': page_obj,
        'page_title': 'Simple Unread Inbox'
    }
    
    return render(request, 'messaging/unread_inbox.html', context)


@login_required
def unread_threads_inbox(request):
    """
    View to display unread thread root messages using custom manager.
    """
    # ✅ Using custom manager for unread threads
    unread_threads = Message.unread.unread_threads_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'reply_count'
    ).select_related('sender')
    
    # Paginate threads
    paginator = Paginator(unread_threads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_threads': page_obj,
        'page_title': 'Unread Conversations'
    }
    
    return render(request, 'messaging/unread_threads.html', context)


@login_required
def unread_replies_inbox(request):
    """
    View to display only unread reply messages using custom manager.
    """
    # ✅ Using custom manager for unread replies
    unread_replies = Message.unread.unread_replies_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'parent_message', 'depth_level'
    ).select_related('sender', 'parent_message', 'parent_message__sender')
    
    # Paginate replies
    paginator = Paginator(unread_replies, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_replies': page_obj,
        'page_title': 'Unread Replies'
    }
    
    return render(request, 'messaging/unread_replies.html', context)


@login_required
def mark_message_as_read(request, message_id):
    """
    Mark a specific message as read.
    """
    message = get_object_or_404(
        Message.objects.only('id', 'receiver', 'is_read'),
        id=message_id,
        receiver=request.user
    )
    
    if request.method == 'POST':
        message.mark_as_read()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Message marked as read'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def mark_thread_as_read(request, thread_root_id):
    """
    Mark all messages in a thread as read using custom manager.
    """
    thread_root = get_object_or_404(
        Message.objects.only('id'),
        id=thread_root_id
    )
    
    if request.method == 'POST':
        # ✅ Using custom manager method
        marked_count = Message.unread.mark_thread_as_read(thread_root, request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Marked {marked_count} messages as read',
            'marked_count': marked_count
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def mark_all_unread_as_read(request):
    """
    Mark all unread messages for a user as read using custom manager.
    """
    if request.method == 'POST':
        # ✅ Using custom manager
        marked_count = Message.unread.for_user(request.user).update(is_read=True)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Marked {marked_count} messages as read',
            'marked_count': marked_count
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def unread_count_api(request):
    """
    API endpoint to get unread message count using custom manager.
    """
    # ✅ Using custom manager for counts
    unread_count = Message.unread.unread_count_for_user(request.user)
    unread_threads_count = Message.unread.unread_threads_for_user(request.user).count()
    unread_replies_count = Message.unread.unread_replies_for_user(request.user).count()
    
    return JsonResponse({
        'unread_count': unread_count,
        'unread_threads_count': unread_threads_count,
        'unread_replies_count': unread_replies_count
    })


@login_required
def recent_unread_messages_api(request):
    """
    API endpoint to get recent unread messages using custom manager with .only().
    """
    limit = int(request.GET.get('limit', 5))
    
    # ✅ Using custom manager with .only() optimization
    recent_unread = Message.unread.recent_unread_for_user(request.user, limit=limit)
    
    messages_data = []
    for msg in recent_unread:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
            'timestamp': msg.timestamp.isoformat()
        })
    
    return JsonResponse({
        'status': 'success',
        'messages': messages_data,
        'total_count': len(messages_data)
    })


@login_required
def dashboard_view(request):
    """
    Dashboard view showing unread message summary using custom managers.
    """
    # ✅ Using custom managers with .only() optimization
    unread_count = Message.unread.unread_count_for_user(request.user)
    recent_unread = Message.unread.recent_unread_for_user(request.user, limit=5)
    unread_threads = Message.unread.unread_threads_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp'
    ).select_related('sender')[:3]
    
    context = {
        'unread_count': unread_count,
        'recent_unread': recent_unread,
        'unread_threads': unread_threads,
    }
    
    return render(request, 'messaging/dashboard.html', context)


@login_required
def send_message(request):
    """View to send a new message or reply"""
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        parent_message_id = request.POST.get('parent_message_id')
        
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            
            parent_message = None
            if parent_message_id:
                parent_message = get_object_or_404(
                    Message.objects.select_related('sender', 'receiver'),
                    id=parent_message_id
                )
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
    """Updated conversation view that marks messages as read"""
    root_message = get_object_or_404(
        Message.objects.select_related('sender', 'receiver', 'thread_root')
                      .prefetch_related('replies__sender', 'replies__receiver'),
        id=message_id
    )
    
    # Permission check
    if request.user not in [root_message.sender, root_message.receiver]:
        thread_root = root_message.get_thread_root()
        thread_participants = thread_root.get_conversation_participants()
        if request.user not in thread_participants:
            raise Http404("You don't have permission to view this conversation")
    
    thread_root = root_message.get_thread_root()
    
    # Get all messages in the thread
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related('sender', 'receiver', 'parent_message')
    
    # ✅ Mark unread messages as read using custom manager
    Message.unread.mark_thread_as_read(thread_root, request.user)
    
    # Build threaded structure
    threaded_messages = build_threaded_structure(thread_messages)
    
    context = {
        'thread_root': thread_root,
        'threaded_messages': threaded_messages,
        'can_reply': True,
        'participants': thread_root.get_conversation_participants(),
    }
    
    return render(request, 'messaging/conversation_thread.html', context)


@login_required
def conversations_list(request):
    """View to display user's conversations with unread indicators"""
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        parent_message__isnull=True
    ).select_related(
        'sender', 'receiver', 'thread_root'
    ).prefetch_related(
        Prefetch(
            'thread_messages',
            queryset=Message.objects.select_related('sender', 'receiver')
                                  .order_by('-timestamp')[:3]
        )
    ).annotate(
        total_replies=Count('thread_messages')
    ).order_by('-timestamp')
    
    # Add unread count to each conversation using custom manager
    for conversation in conversations:
        conversation.unread_count = Message.unread.for_user(request.user).filter(
            Q(id=conversation.id) | Q(thread_root=conversation)
        ).count()
    
    # Paginate conversations
    paginator = Paginator(conversations, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get total unread count
    total_unread = Message.unread.unread_count_for_user(request.user)
    
    return render(request, 'messaging/conversations_list.html', {
        'conversations': page_obj,
        'total_unread': total_unread,
    })


def build_threaded_structure(messages):
    """Build nested structure for threaded messages"""
    message_dict = {}
    root_messages = []
    
    for message in messages:
        message_data = {
            'message': message,
            'replies': []
        }
        message_dict[message.id] = message_data
        
        if message.parent_message is None:
            root_messages.append(message_data)
    
    for message in messages:
        if message.parent_message:
            parent_data = message_dict.get(message.parent_message.id)
            if parent_data:
                parent_data['replies'].append(message_dict[message.id])
    
    return root_messages


# Keep existing user deletion views
@login_required
def delete_user_account(request):
    """View to handle user account deletion"""
    if request.method == 'GET':
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
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')
        deletion_reason = request.POST.get('reason', '')
        
        if not check_password(password, request.user.password):
            messages.error(request, 'Invalid password. Please try again.')
            return redirect('delete_user_account')
        
        if confirmation.lower() != 'delete my account':
            messages.error(request, 'Please type "delete my account" to confirm.')
            return redirect('delete_user_account')
        
        request.user._deleted_by = 'self'
        request.user._deletion_reason = deletion_reason
        
        username = request.user.username
        
        try:
            with transaction.atomic():
                logout(request)
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
def unread_inbox(request):
    """
    View to display only unread messages using custom manager and .only() optimization.
    """
    # ✅ Using custom manager with .only() optimization
    unread_messages = Message.unread.unread_inbox_optimized(request.user)
    
    # Paginate unread messages
    paginator = Paginator(unread_messages, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count for badge using custom manager
    unread_count = Message.unread.unread_count_for_user(request.user)
    
    context = {
        'unread_messages': page_obj,
        'unread_count': unread_count,
        'page_title': 'Unread Messages'
    }
    
    return render(request, 'messaging/unread_inbox.html', context)


@login_required
def unread_inbox_simple(request):
    """
    Simple unread inbox view using Message.unread.unread_for_user
    """
    # ✅ Using Message.unread.unread_for_user method
    unread_messages = Message.unread.unread_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'parent_message'
    ).select_related('sender', 'parent_message')
    
    # Paginate unread messages
    paginator = Paginator(unread_messages, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_messages': page_obj,
        'page_title': 'Simple Unread Inbox'
    }
    
    return render(request, 'messaging/unread_inbox.html', context)


@login_required
def unread_threads_inbox(request):
    """
    View to display unread thread root messages using custom manager.
    """
    # ✅ Using custom manager for unread threads
    unread_threads = Message.unread.unread_threads_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'reply_count'
    ).select_related('sender')
    
    # Paginate threads
    paginator = Paginator(unread_threads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_threads': page_obj,
        'page_title': 'Unread Conversations'
    }
    
    return render(request, 'messaging/unread_threads.html', context)


@login_required
def unread_replies_inbox(request):
    """
    View to display only unread reply messages using custom manager.
    """
    # ✅ Using custom manager for unread replies
    unread_replies = Message.unread.unread_replies_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp', 'parent_message', 'depth_level'
    ).select_related('sender', 'parent_message', 'parent_message__sender')
    
    # Paginate replies
    paginator = Paginator(unread_replies, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_replies': page_obj,
        'page_title': 'Unread Replies'
    }
    
    return render(request, 'messaging/unread_replies.html', context)


@login_required
def mark_message_as_read(request, message_id):
    """
    Mark a specific message as read.
    """
    message = get_object_or_404(
        Message.objects.only('id', 'receiver', 'is_read'),
        id=message_id,
        receiver=request.user
    )
    
    if request.method == 'POST':
        message.mark_as_read()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Message marked as read'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def mark_thread_as_read(request, thread_root_id):
    """
    Mark all messages in a thread as read using custom manager.
    """
    thread_root = get_object_or_404(
        Message.objects.only('id'),
        id=thread_root_id
    )
    
    if request.method == 'POST':
        # ✅ Using custom manager method
        marked_count = Message.unread.mark_thread_as_read(thread_root, request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Marked {marked_count} messages as read',
            'marked_count': marked_count
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def mark_all_unread_as_read(request):
    """
    Mark all unread messages for a user as read using custom manager.
    """
    if request.method == 'POST':
        # ✅ Using custom manager
        marked_count = Message.unread.for_user(request.user).update(is_read=True)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Marked {marked_count} messages as read',
            'marked_count': marked_count
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@login_required
def unread_count_api(request):
    """
    API endpoint to get unread message count using custom manager.
    """
    # ✅ Using custom manager for counts
    unread_count = Message.unread.unread_count_for_user(request.user)
    unread_threads_count = Message.unread.unread_threads_for_user(request.user).count()
    unread_replies_count = Message.unread.unread_replies_for_user(request.user).count()
    
    return JsonResponse({
        'unread_count': unread_count,
        'unread_threads_count': unread_threads_count,
        'unread_replies_count': unread_replies_count
    })


@login_required
def recent_unread_messages_api(request):
    """
    API endpoint to get recent unread messages using custom manager with .only().
    """
    limit = int(request.GET.get('limit', 5))
    
    # ✅ Using custom manager with .only() optimization
    recent_unread = Message.unread.recent_unread_for_user(request.user, limit=limit)
    
    messages_data = []
    for msg in recent_unread:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
            'timestamp': msg.timestamp.isoformat()
        })
    
    return JsonResponse({
        'status': 'success',
        'messages': messages_data,
        'total_count': len(messages_data)
    })


@login_required
def dashboard_view(request):
    """
    Dashboard view showing unread message summary using custom managers.
    """
    # ✅ Using custom managers with .only() optimization
    unread_count = Message.unread.unread_count_for_user(request.user)
    recent_unread = Message.unread.recent_unread_for_user(request.user, limit=5)
    unread_threads = Message.unread.unread_threads_for_user(request.user).only(
        'id', 'sender', 'content', 'timestamp'
    ).select_related('sender')[:3]
    
    context = {
        'unread_count': unread_count,
        'recent_unread': recent_unread,
        'unread_threads': unread_threads,
    }
    
    return render(request, 'messaging/dashboard.html', context)


@login_required
def user_inbox_with_unread_filter(request):
    """
    Enhanced inbox view that can filter by read/unread status using custom managers.
    """
    filter_type = request.GET.get('filter', 'all')  # all, unread, read
    
    if filter_type == 'unread':
        # ✅ Using Message.unread.unread_for_user
        messages_list = Message.unread.unread_for_user(request.user).select_related(
            'sender', 'receiver', 'parent_message', 'thread_root'
        ).prefetch_related(
            'replies__sender', 'replies__receiver'
        )
    elif filter_type == 'read':
        messages_list = Message.objects.filter(
            receiver=request.user,
            is_read=True
        ).select_related(
            'sender', 'receiver', 'parent_message', 'thread_root'
        )
    else:  # all messages
        messages_list = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).select_related(
            'sender', 'receiver', 'parent_message', 'thread_root'
        )
    
    messages_list = messages_list.order_by('-timestamp')
    
    # Paginate messages
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count for navigation
    unread_count = Message.unread.unread_count_for_user(request.user)
    
    context = {
        'messages': page_obj,
        'filter_type': filter_type,
        'unread_count': unread_count,
    }
    
    return render(request, 'messaging/enhanced_inbox.html', context)


@login_required
def send_message(request):
    """View to send a new message or reply"""
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        parent_message_id = request.POST.get('parent_message_id')
        
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            
            parent_message = None
            if parent_message_id:
                parent_message = get_object_or_404(
                    Message.objects.select_related('sender', 'receiver'),
                    id=parent_message_id
                )
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
    """Updated conversation view that marks messages as read"""
    root_message = get_object_or_404(
        Message.objects.select_related('sender', 'receiver', 'thread_root')
                      .prefetch_related('replies__sender', 'replies__receiver'),
        id=message_id
    )
    
    # Permission check
    if request.user not in [root_message.sender, root_message.receiver]:
        thread_root = root_message.get_thread_root()
        thread_participants = thread_root.get_conversation_participants()
        if request.user not in thread_participants:
            raise Http404("You don't have permission to view this conversation")
    
    thread_root = root_message.get_thread_root()
    
    # Get all messages in the thread
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related('sender', 'receiver', 'parent_message')
    
    # ✅ Mark unread messages as read using custom manager
    Message.unread.mark_thread_as_read(thread_root, request.user)
    
    # Build threaded structure
    threaded_messages = build_threaded_structure(thread_messages)
    
    context = {
        'thread_root': thread_root,
        'threaded_messages': threaded_messages,
        'can_reply': True,
        'participants': thread_root.get_conversation_participants(),
    }
    
    return render(request, 'messaging/conversation_thread.html', context)


@login_required
def conversations_list(request):
    """View to display user's conversations with unread indicators"""
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        parent_message__isnull=True
    ).select_related(
        'sender', 'receiver', 'thread_root'
    ).prefetch_related(
        Prefetch(
            'thread_messages',
            queryset=Message.objects.select_related('sender', 'receiver')
                                  .order_by('-timestamp')[:3]
        )
    ).annotate(
        total_replies=Count('thread_messages')
    ).order_by('-timestamp')
    
    # Add unread count to each conversation using custom manager
    for conversation in conversations:
        conversation.unread_count = Message.unread.for_user(request.user).filter(
            Q(id=conversation.id) | Q(thread_root=conversation)
        ).count()
    
    # Paginate conversations
    paginator = Paginator(conversations, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get total unread count
    total_unread = Message.unread.unread_count_for_user(request.user)
    
    return render(request, 'messaging/conversations_list.html', {
        'conversations': page_obj,
        'total_unread': total_unread,
    })


@login_required
def reply_to_message(request, message_id):
    """View to reply to a specific message"""
    parent_message = get_object_or_404(
        Message.objects.select_related(
            'sender', 'receiver', 'thread_root'
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
    """API endpoint to get all messages in a thread"""
    thread_root = get_object_or_404(
        Message.objects.select_related('sender', 'receiver'),
        id=thread_root_id
    )
    
    # Check permission
    thread_participants = thread_root.get_conversation_participants()
    if request.user not in thread_participants:
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        })
    
    thread_messages = Message.objects.filter(
        Q(id=thread_root.id) | Q(thread_root=thread_root)
    ).select_related(
        'sender', 'receiver', 'parent_message'
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


def build_threaded_structure(messages):
    """Build nested structure for threaded messages"""
    message_dict = {}
    root_messages = []
    
    for message in messages:
        message_data = {
            'message': message,
            'replies': []
        }
        message_dict[message.id] = message_data
        
        if message.parent_message is None:
            root_messages.append(message_data)
    
    for message in messages:
        if message.parent_message:
            parent_data = message_dict.get(message.parent_message.id)
            if parent_data:
                parent_data['replies'].append(message_dict[message.id])
    
    return root_messages


# Keep existing user deletion views
@login_required
def delete_user_account(request):
    """View to handle user account deletion"""
    if request.method == 'GET':
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
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')
        deletion_reason = request.POST.get('reason', '')
        
        if not check_password(password, request.user.password):
            messages.error(request, 'Invalid password. Please try again.')
            return redirect('delete_user_account')
        
        if confirmation.lower() != 'delete my account':
            messages.error(request, 'Please type "delete my account" to confirm.')
            return redirect('delete_user_account')
        
        request.user._deleted_by = 'self'
        request.user._deletion_reason = deletion_reason
        
        username = request.user.username
        
        try:
            with transaction.atomic():
                logout(request)
                User.objects.filter(username=username).delete()
                
                messages.success(request, 'Your account has been successfully deleted.')
                return redirect('account_deleted_success')
                
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your account: {str(e)}')
            return redirect('delete_user_account')


def account_deleted_success(request):
    """View to show successful account deletion"""
    return render(request, 'messaging/account_deleted.html')
