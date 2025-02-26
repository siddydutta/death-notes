from django.db.models.signals import pre_save
from django.dispatch import receiver

from web.models import Message


@receiver(pre_save, sender=Message)
def pre_save_message(sender, instance: Message, **kwargs):
    """Signal handler to store previous values of a Message instance.

    Args:
        sender (_type_): The model class that sent the signal.
        instance (Message): The instance of Message that triggered the signal.
    """
    if instance._state.adding:
        # skip if the message is being created
        return
    # cache the previous values in the instance for comparison
    previous = Message.objects.only('delay', 'scheduled_at').get(pk=instance.pk)
    instance.__previous_delay = previous.delay
    instance.__previous_scheduled_at = previous.scheduled_at
