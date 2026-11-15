from .models import StaffNotification


def unread_staff_notifications(request):
    if request.user.has_perm("members.view_member"):
        count = StaffNotification.objects.exclude(read_by=request.user).exclude(dismissed_by=request.user).count()
        return {"unread_staff_notification_count": count}
    return {}
