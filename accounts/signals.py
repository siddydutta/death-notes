from django.db.models.signals import pre_save
from django.dispatch import receiver

from accounts.models import User


@receiver(pre_save, sender=User)
def pre_save_user(sender, instance: User, **kwargs):
    """Signal handler to store previous values of a User instance.

    Args:
        sender (_type_): The model class that sent the signal.
        instance (User): The instance of User that triggered the signal.
    """
    if instance._state.adding:
        # skip if the user is being created
        return
    # cache the previous value in the instance for comparison
    previous = User.objects.only('interval').get(pk=instance.pk)
    instance.__previous_interval = previous.interval
