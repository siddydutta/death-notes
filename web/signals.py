from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save
from django.dispatch import receiver

from accounts.models import User
from web.models import ActivityLog, Message


@receiver(user_logged_in)
def add_login_activitylog(sender, request, user: User, **kwargs):
    if request.path.startswith('/admin/'):
        return

    ActivityLog.objects.create(
        user=user,
        type=ActivityLog.Type.CHECKED_IN,
        description='Checked in to Death Notes',
    )


@receiver(pre_save, sender=Message)
def pre_save_message(sender, instance: Message, **kwargs):
    if instance._state.adding:
        return
    previous = Message.objects.only('delay', 'scheduled_at').get(pk=instance.pk)
    instance.__previous_delay = previous.delay
    instance.__previous_scheduled_at = previous.scheduled_at
