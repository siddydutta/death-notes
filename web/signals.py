from django.db.models.signals import pre_save
from django.dispatch import receiver

from web.models import Message


@receiver(pre_save, sender=Message)
def pre_save_message(sender, instance: Message, **kwargs):
    if instance._state.adding:
        return
    previous = Message.objects.only('delay', 'scheduled_at').get(pk=instance.pk)
    instance.__previous_delay = previous.delay
    instance.__previous_scheduled_at = previous.scheduled_at
