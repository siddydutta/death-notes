from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from accounts.models import User
from web.models import ActivityLog


@receiver(user_logged_in)
def add_login_activitylog(sender, request, user: User, **kwargs):
    if request.path.startswith('/admin/'):
        return

    ActivityLog.objects.create(
        user=user,
        type=ActivityLog.Type.CHECKED_IN,
        description='Checked in to Death Notes',
    )
