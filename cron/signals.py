from datetime import timedelta

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import User
from cron.models import Job
from web.constants import MESSAGE_TYPE_MAPPING
from web.models import ActivityLog, Message


@receiver(post_save, sender=ActivityLog)
def update_jobs_on_checkin(sender, created: bool, instance: ActivityLog, **kwargs):
    """Signal handler to update the scheduled time of jobs when an ActivityLog instance is checked in.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        created (bool): A boolean indicating whether the instance was created.
        instance (ActivityLog): The instance of ActivityLog that triggered the signal.
    """
    if not created or instance.type != ActivityLog.Type.CHECKED_IN:
        return

    # filter user's final word messages with delay
    jobs = (
        Job.objects.only('scheduled_at', 'message__delay')
        .select_related('message')
        .filter(
            message__type=Message.Type.FINAL_WORD,
            message__delay__isnull=False,
            message__user_id=instance.user_id,
        )
    )

    now = timezone.now()
    for job in jobs:
        job.scheduled_at = now + timedelta(days=job.message.delay)

    # bulk update the scheduled time of jobs without triggering signals
    Job.objects.bulk_update(jobs, ['scheduled_at'])


@receiver(post_save, sender=User)
def update_jobs_on_interval_change(sender, created: bool, instance: User, **kwargs):
    """Signal handler to update the scheduled time of jobs when a User instance's interval is changed.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        instance (User): The instance of User that triggered the signal.
    """
    if created or getattr(instance, '__previous_interval', None) == instance.interval:
        return

    # filter user's time capsule messages
    jobs = (
        Job.objects.only('scheduled_at', 'message__delay')
        .select_related('message')
        .filter(
            message__type=Message.Type.FINAL_WORD,
            message__user_id=instance.id,
        )
    )

    delta = instance.interval - instance.__previous_interval
    for job in jobs:
        job.scheduled_at += timedelta(days=delta)

    # bulk update the scheduled time of jobs without triggering signals
    Job.objects.bulk_update(jobs, ['scheduled_at'])


@receiver(post_save, sender=Message)
def post_save_message(sender, created: bool, instance: Message, **kwargs):
    """Signal handler to create a Job instance when a Message instance is created.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        created (bool): A boolean indicating whether the instance was created.
        instance (Message): The instance of Message that triggered the signal.
    """
    if created:
        # create a job for the message
        scheduled_at = (
            instance.scheduled_at
            if instance.type == Message.Type.TIME_CAPSULE
            else timezone.now()
            + timedelta(days=instance.delay)
            + timedelta(days=instance.user.interval)
        )
        Job.objects.create(
            message=instance,
            scheduled_at=scheduled_at,
        )
    else:
        # update the corresponding job if the message is updated
        if instance.type == Message.Type.TIME_CAPSULE:
            if instance.scheduled_at != getattr(
                instance, '__previous_scheduled_at', None
            ):
                Job.objects.filter(message_id=instance.id).update(
                    scheduled_at=instance.scheduled_at
                )
        elif instance.type == Message.Type.FINAL_WORD:
            if instance.delay != getattr(instance, '__previous_delay', None):
                scheduled_at = (
                    timezone.now()
                    + timedelta(days=instance.delay)
                    + timedelta(days=instance.user.interval)
                )
                Job.objects.filter(message_id=instance.id).update(
                    scheduled_at=scheduled_at
                )


@receiver(pre_save, sender=Job)
def pre_save_job(sender, instance: Job, **kwargs):
    """Signal handler to store the previous value of the is_completed field of a Job instance.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        instance (Job): The instance of Job that triggered the signal.
    """
    if instance._state.adding:
        # skip if the instance is being created
        return
    # cache the previous value of the is_completed field in the instance for comparison
    previous = Job.objects.only('is_completed').get(pk=instance.pk)
    instance.__previous_is_completed = previous.is_completed


@receiver(post_save, sender=Job)
def post_save_job(sender, created: bool, instance: Job, **kwargs):
    """Signal handler to create an ActivityLog instance when a Job instance is created or updated.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        created (bool): A boolean indicating whether the instance was created.
        instance (Job): The instance of Job that triggered the signal.
    """
    if created:
        # create an activity log for a new job i.e. a new message
        ActivityLog.objects.create(
            user_id=instance.message.user_id,
            type=ActivityLog.Type.MESSAGE_CREATED,
            description=f'{MESSAGE_TYPE_MAPPING[instance.message.type]} - "{instance.message.subject}" scheduled.',
        )
    if instance.is_completed is False:
        # early return if the job is not completed
        return
    if (
        not hasattr(instance, '__previous_is_completed')
        or instance.is_completed == instance.__previous_is_completed
    ):
        # early return if the job is not updated
        return

    # create an activity log for a completed job
    ActivityLog.objects.create(
        user_id=instance.message.user_id,
        type=ActivityLog.Type.MESSAGE_DELIVERED,
        description=f'{MESSAGE_TYPE_MAPPING[instance.message.type]} - "{instance.message.subject}" delivered.',
    )


@receiver(post_delete, sender=Job)
def post_delete_job(sender, instance: Job, **kwargs):
    """Signal handler to create an ActivityLog instance when a Job instance is deleted.

    Args:
        sender (Type[Model]): The model class that sent the signal.
        instance (Job): The instance of Job that triggered the signal.
    """
    # create an activity log for a deleted job i.e. a deleted message
    ActivityLog.objects.create(
        user_id=instance.message.user_id,
        type=ActivityLog.Type.MESSAGE_DELETED,
        description=f'{MESSAGE_TYPE_MAPPING[instance.message.type]} - "{instance.message.subject}" deleted.',
    )
