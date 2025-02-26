from django.db import models

from web.models import Message


class Job(models.Model):
    """
    Represents a scheduled job in the system.

    Attributes:
        id (AutoField): The primary key for the job.
        message (OneToOneField): A one-to-one relationship to the Message model.
                                 Deletes the job if the related message is deleted.
        scheduled_at (DateTimeField): The date and time when the job is scheduled to run.
        is_completed (BooleanField): Indicates whether the job has been completed. Defaults to False.
        created_at (DateTimeField): The date and time when the job was created. Automatically set on creation.
        updated_at (DateTimeField): The date and time when the job was last updated. Automatically set on update.
    """

    id = models.AutoField(primary_key=True)
    message = models.OneToOneField(Message, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # order by scheduled_at field
        ordering = ('scheduled_at',)
        # add an index on the scheduled_at field for faster querying
        indexes = [
            models.Index(fields=['scheduled_at']),
        ]
