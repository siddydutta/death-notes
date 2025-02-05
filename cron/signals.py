from datetime import timedelta

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import User
from cron.models import Job
from web.constants import MESSAGE_TYPE_MAPPING
from web.models import ActivityLog, Message


@receiver(user_logged_in)
def add_login_activitylog(sender, request, user: User, **kwargs):
    jobs = (
        Job.objects.only('scheduled_at', 'message__delay')
        .select_related('message')
        .filter(
            message__type=Message.Type.FINAL_WORD,
            message__delay__isnull=False,
            message__user_id=user.id,
        )
    )

    now = timezone.now()
    for job in jobs:
        job.scheduled_at = now + timedelta(days=job.message.delay)

    Job.objects.bulk_update(jobs, ['scheduled_at'])


@receiver(post_save, sender=Message)
def post_save_message(sender, created, instance: Message, **kwargs):
    if created:
        scheduled_at = (
            instance.scheduled_at
            if instance.type == Message.Type.TIME_CAPSULE
            else timezone.now() + timedelta(days=instance.delay)
        )
        Job.objects.create(
            message=instance,
            scheduled_at=scheduled_at,
        )
    else:
        if instance.type == Message.Type.TIME_CAPSULE:
            if instance.scheduled_at != getattr(
                instance, '__previous_scheduled_at', None
            ):
                Job.objects.filter(message_id=instance.id).update(
                    scheduled_at=instance.scheduled_at
                )
        elif instance.type == Message.Type.FINAL_WORD:
            if instance.delay != getattr(instance, '__previous_delay', None):
                scheduled_at = timezone.now() + timedelta(days=instance.delay)
                Job.objects.filter(message_id=instance.id).update(
                    scheduled_at=scheduled_at
                )


@receiver(pre_save, sender=Job)
def pre_save_job(sender, instance: Job, **kwargs):
    if instance._state.adding:
        return
    previous = Job.objects.only('is_completed').get(pk=instance.pk)
    instance.__previous_is_completed = previous.is_completed


@receiver(post_save, sender=Job)
def post_save_job(sender, created, instance: Job, **kwargs):
    if created:
        ActivityLog.objects.create(
            user_id=instance.message.user_id,
            type=ActivityLog.Type.MESSAGE_CREATED,
            description=f'{MESSAGE_TYPE_MAPPING[instance.message.type]} - "{instance.message.subject}" scheduled.',
        )
    if instance.is_completed is False:
        return
    if not hasattr(instance, '__previous_is_completed'):
        return
    if instance.is_completed == instance.__previous_is_completed:
        return

    ActivityLog.objects.create(
        user_id=instance.message.user_id,
        type=ActivityLog.Type.MESSAGE_DELIVERED,
        description=f'{MESSAGE_TYPE_MAPPING[instance.message.type]} - "{instance.message.subject}" delivered.',
    )
