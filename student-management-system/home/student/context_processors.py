from school.models import Notification

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notification': unread_notifications,
            'unread_notification_count': unread_notifications.count()
        }
    return {
        'unread_notification': [],
        'unread_notification_count': 0
    }