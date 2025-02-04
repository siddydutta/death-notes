from django.db import models

from web.models import Message


class Job(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.OneToOneField(Message, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
