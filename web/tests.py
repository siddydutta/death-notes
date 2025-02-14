from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.test import RequestFactory, TestCase
from django.utils.timezone import make_aware

from web.models import ActivityLog, Message
from web.signals import add_login_activitylog

User = get_user_model()


class SignalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='user@test.com', password='foobar')

    def test_add_login_activitylog(self):
        request = self.factory.get('/some/path/')
        add_login_activitylog(sender=None, request=request, user=self.user)

        self.assertTrue(
            ActivityLog.objects.filter(
                user=self.user, type=ActivityLog.Type.CHECKED_IN
            ).exists()
        )

    def test_add_login_activitylog_admin_path(self):
        request = self.factory.get('/admin/some/path/')
        add_login_activitylog(sender=None, request=request, user=self.user)

        self.assertFalse(
            ActivityLog.objects.filter(
                user=self.user, type=ActivityLog.Type.CHECKED_IN
            ).exists()
        )

    def test_pre_save_message(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        message.delay = 20

        pre_save.send(sender=Message, instance=message)

        self.assertTrue(hasattr(message, '__previous_delay'))
        self.assertEqual(getattr(message, '__previous_delay'), 10)


class MessageModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = make_aware(
            datetime.strptime('2025-02-10 10:00:00', '%Y-%m-%d %H:%M:%S')
        )

    def test_save_final_word_message(self):
        message = Message(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
            scheduled_at=self.scheduled_at,
        )
        with self.assertRaises(ValueError):
            message.save()
        message.delay = None
        message.scheduled_at = None
        with self.assertRaises(ValueError):
            message.save()
        message.delay = 10
        message.save()
        self.assertEqual(str(message), 'Message 1 - FINAL_WORD - Test Subject')
        self.assertIsNotNone(message.id)

    def test_save_time_capsule_message(self):
        message = Message(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
            scheduled_at=self.scheduled_at,
        )
        with self.assertRaises(ValueError):
            message.save()
        message.delay = None
        message.scheduled_at = None
        with self.assertRaises(ValueError):
            message.save()
        message.scheduled_at = self.scheduled_at
        message.save()
        self.assertIsNotNone(message.id)

    def test_send_message(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )

        with patch('web.models.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 1
            sent = message.send()
            self.assertTrue(sent)
            self.assertEqual(message.status, Message.Status.DELIVERED)

    def test_send_message_failed(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )

        with patch('web.models.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 0
            sent = message.send()
            self.assertFalse(sent)
            self.assertEqual(message.status, Message.Status.FAILED)
