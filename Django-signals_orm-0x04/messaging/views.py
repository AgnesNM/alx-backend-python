# views.py - Complete views with user deletion functionality
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password
from .models import Message, Notification, MessageHistory, UserDeletionLog


@login_required
def delete_user_account(request):
    """View to handle user account deletion"""
    if request.method == 'GET':
        # Show deletion confirmation page
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
                User.objects.filter(username=username).delete()  # ✅ user.delete() equivalent
                
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
    """Admin view to delete a user account (requires admin privileges)"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        deletion_reason = request.POST.get('reason', 'Deleted by admin')
        
        # Set custom attributes for the deletion signal
        target_user._deleted_by = request.user.username
        target_user._deletion_reason = deletion_reason
        
        username = target_user.username
        
        try:
            with transaction.atomic():
                target_user.delete()  # ✅ Direct user.delete() call
                
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
def bulk_delete_users(request):
    """Admin view to delete multiple users at once"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        deletion_reason = request.POST.get('reason', 'Bulk deletion by admin')
        
        if not user_ids:
            messages.error(request, 'No users selected for deletion.')
            return redirect('admin_user_list')
        
        deleted_count = 0
        failed_deletions = []
        
        try:
            with transaction.atomic():
                for user_id in user_ids:
                    try:
                        user = User.objects.get(id=user_id)
                        
                        # Don't allow deleting self or superusers
                        if user == request.user or user.is_superuser:
                            failed_deletions.append(f"{user.username} (protected)")
                            continue
                        
                        # Set deletion attributes
                        user._deleted_by = request.user.username
                        user._deletion_reason = f"Bulk deletion: {deletion_reason}"
                        
                        user.delete()  # ✅ user.delete() call in loop
                        deleted_count += 1
                        
                    except User.DoesNotExist:
                        failed_deletions.append(f"User ID {user_id} (not found)")
                    except Exception as e:
                        failed_deletions.append(f"User ID {user_id} ({str(e)})")
                
                if deleted_count > 0:
                    messages.success(request, f'Successfully deleted {deleted_count} user(s).')
                
                if failed_deletions:
                    messages.warning(request, f'Failed to delete: {", ".join(failed_deletions)}')
                
        except Exception as e:
            messages.error(request, f'An error occurred during bulk deletion: {str(e)}')
        
        return redirect('admin_user_list')
    
    # GET request - show bulk deletion form
    users = User.objects.filter(is_superuser=False).exclude(id=request.user.id)
    
    return render(request, 'messaging/bulk_delete_users.html', {
        'users': users
    })


@login_required
def deletion_logs(request):
    """View to show user deletion logs (admin only)"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    logs = UserDeletionLog.objects.all()
    
    # Paginate logs
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/deletion_logs.html', {
        'logs': page_obj
    })


@login_required
def send_message(request):
    """View to send a new message"""
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message sent successfully',
                'message_id': message.id
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def edit_message(request, message_id):
    """View to edit an existing message"""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
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
    """View to display message edit history"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.user != message.sender and request.user != message.receiver:
        raise Http404("You don't have permission to view this message history")
    
    history_entries = MessageHistory.objects.filter(message=message).order_by('-edited_at')
    
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
def user_messages(request):
    """View to display user's messages with edit indicators"""
    messages_list = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp')
    
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/messages_list.html', {
        'messages': page_obj
    })


@login_required
def notifications_list(request):
    """View to display user's notifications"""
    notifications = Notification.objects.filter(user=request.user)
    
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
        Notification, 
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
def force_delete_user(request, user_id):
    """Force delete a user and all data (emergency admin function)"""
    if not request.user.is_superuser:
        raise Http404("Permission denied - superuser only")
    
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        if target_user.is_superuser:
            messages.error(request, 'Cannot delete superuser accounts.')
            return redirect('admin_user_list')
        
        username = target_user.username
        deletion_reason = request.POST.get('reason', 'Force deleted by superuser')
        
        try:
            with transaction.atomic():
                # Set deletion attributes
                target_user._deleted_by = f"FORCE_DELETE_{request.user.username}"
                target_user._deletion_reason = f"EMERGENCY: {deletion_reason}"
                
                # Force delete without additional checks
                target_user.delete()  # ✅ Direct force deletion
                
                messages.success(request, f'User {username} has been force deleted.')
                return redirect('admin_user_list')
                
        except Exception as e:
            messages.error(request, f'Force deletion failed: {str(e)}')
            return redirect('admin_user_list')
    
    return render(request, 'messaging/force_delete_user.html', {
        'target_user': target_user
    })


@login_required
def soft_delete_inactive_users(request):
    """Admin utility to delete inactive users (haven't logged in for X days)"""
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    if request.method == 'POST':
        days_threshold = int(request.POST.get('days', 365))
        cutoff_date = timezone.now() - timezone.timedelta(days=days_threshold)
        
        # Find inactive users
        inactive_users = User.objects.filter(
            last_login__lt=cutoff_date,
            is_staff=False,
            is_superuser=False
        ).exclude(id=request.user.id)
        
        deleted_count = 0
        
        try:
            with transaction.atomic():
                for user in inactive_users:
                    # Set deletion attributes
                    user._deleted_by = f"CLEANUP_{request.user.username}"
                    user._deletion_reason = f"Inactive for {days_threshold} days (last login: {user.last_login})"
                    
                    user.delete()  # ✅ Delete inactive users
                    deleted_count += 1
                
                messages.success(request, f'Deleted {deleted_count} inactive user accounts.')
                
        except Exception as e:
            messages.error(request, f'Error during cleanup: {str(e)}')
        
        return redirect('admin_user_list')
    
    # GET request - show cleanup form
    days_options = [30, 90, 180, 365, 730]  # Various threshold options
    
    return render(request, 'messaging/cleanup_inactive_users.html', {
        'days_options': days_options
    })


@login_required 
def delete_user_data_only(request):
    """Delete user's data but keep the account (data deletion request)"""
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')
        
        # Validate password
        if not check_password(password, request.user.password):
            messages.error(request, 'Invalid password. Please try again.')
            return redirect('delete_user_data_only')
        
        # Validate confirmation
        if confirmation.lower() != 'delete my data':
            messages.error(request, 'Please type "delete my data" to confirm.')
            return redirect('delete_user_data_only')
        
        try:
            with transaction.atomic():
                # Delete user's data but keep the account
                user = request.user
                
                # Count data before deletion
                messages_sent = user.sent_messages.count()
                messages_received = user.received_messages.count()
                notifications_count = user.notifications.count()
                message_edits = user.message_edits.count()
                
                # Delete related data (this will cascade properly)
                user.sent_messages.all().delete()
                user.received_messages.all().delete() 
                user.notifications.all().delete()
                user.message_edits.all().delete()
                
                # Log the data deletion
                UserDeletionLog.objects.create(
                    username=f"{user.username}_DATA_ONLY",
                    email=user.email,
                    deleted_by='self_data_only',
                    deletion_reason='User requested data deletion only',
                    messages_sent_count=messages_sent,
                    messages_received_count=messages_received,
                    notifications_count=notifications_count,
                    message_edits_count=message_edits
                )
                
                messages.success(request, 'Your data has been successfully deleted. Your account remains active.')
                return redirect('user_messages')
                
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your data: {str(e)}')
    
    # GET request - show data deletion form
    user_stats = {
        'messages_sent': request.user.sent_messages.count(),
        'messages_received': request.user.received_messages.count(),
        'notifications': request.user.notifications.count(),
        'message_edits': request.user.message_edits.count(),
    }
    
    return render(request, 'messaging/delete_user_data.html', {
        'user_stats': user_stats
    })
