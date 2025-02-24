from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from accounts.models import User


class Message(models.Model):
    class Type(models.TextChoices):
        FINAL_WORD = 'FINAL_WORD', 'Final Word'
        TIME_CAPSULE = 'TIME_CAPSULE', 'Time Capsule'

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    type = models.CharField(max_length=20, choices=Type.choices)
    recipients = models.TextField(help_text='Comma-separated list of email recipients')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    subject = models.CharField(max_length=255)
    text = models.TextField()
    delay = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Delay before sending message for FINAL_WORD (in days)',
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the message is scheduled to be sent for TIME_CAPSULE',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.type == self.Type.FINAL_WORD:
            if not self.delay:
                raise ValueError('Delay must be set for FINAL_WORD messages')
            if self.scheduled_at:
                raise ValueError('Scheduled at must not be set for FINAL_WORD messages')
        if self.type == self.Type.TIME_CAPSULE:
            if self.delay:
                raise ValueError('Delay must not be set for TIME_CAPSULE messages')
            if not self.scheduled_at:
                raise ValueError('Scheduled at must be set for TIME_CAPSULE messages')
        return super().save(*args, **kwargs)

    def send(self, force_send=False) -> bool:
        if self.status == self.Status.DELIVERED and not force_send:
            return False

        html_message = render_to_string(
            template_name='message_template.html',
            context={
                'subject': self.subject,
                'text': self.text,
                'type': self.type,
                'user': self.user,
                'base_url': settings.FRONTEND_URL,
            },
        )
        plain_message = strip_tags(html_message)

        sent = send_mail(
            subject=self.subject,
            message=plain_message,
            from_email=f'Death Notes Service <{settings.EMAIL_HOST_USER}>',
            recipient_list=[email.strip() for email in self.recipients.split(',')],
            html_message=html_message,
        )
        self.status = self.Status.DELIVERED if sent == 1 else self.Status.FAILED
        self.save(update_fields=['status', 'updated_at'])
        return sent == 1

    def __str__(self):
        return f'Message {self.id} - {self.type} - {self.subject}'


class ActivityLog(models.Model):
    class Type(models.TextChoices):
        CHECKED_IN = 'CHECKED_IN', 'Checked In'
        MESSAGE_CREATED = 'MESSAGE_CREATED', 'Message Created'
        MESSAGE_DELIVERED = 'MESSAGE_DELIVERED', 'Message Delivered'
        MESSAGE_DELETED = 'MESSAGE_DELETED', 'Message Deleted'

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='activity_logs'
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Activity {self.id} - {self.type}'
