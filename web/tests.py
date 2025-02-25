import json
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from web.models import ActivityLog, Message
from web.serializers import MessageSerializer
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


class ModelTests(TestCase):
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

    def test_send_delivered_message_no_force_send(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            status=Message.Status.DELIVERED,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        is_sent = message.send()
        self.assertFalse(is_sent)

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

    def test_activity_log_str(self):
        ActivityLog.objects.create(user=self.user, type=ActivityLog.Type.CHECKED_IN)
        activity_log = ActivityLog.objects.first()
        self.assertEqual(str(activity_log), 'Activity 1 - CHECKED_IN')


class ViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
        self.scheduled_at = make_aware(
            datetime.strptime('2025-02-10 10:00:00', '%Y-%m-%d %H:%M:%S')
        )

    def test_unauthorized_access(self):
        self.client.credentials()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + 'expired.token.here')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_home_api_view(self):
        Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='test@test.com',
            subject='Test Final',
            text='Test',
            delay=10,
        )
        Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='test@test.com',
            subject='Test Capsule',
            text='Test',
            scheduled_at=self.scheduled_at,
        )

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['total']['FINAL_WORD'], 1)
        self.assertEqual(response.json()['total']['TIME_CAPSULE'], 1)
        self.assertEqual(response.json()['delivered']['FINAL_WORD'], 0)
        self.assertEqual(response.json()['delivered']['TIME_CAPSULE'], 0)

    def test_checkin_api_view(self):
        response = self.client.post(reverse('checkin'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_checkin)

    def test_user_api_view_get(self):
        response = self.client.get(reverse('user'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['email'], self.user.email)

    def test_user_api_view_patch(self):
        data = {'first_name': 'Test', 'last_name': 'User'}
        response = self.client.patch(
            reverse('user'), data=json.dumps(data), content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')

    def test_message_viewset_list(self):
        Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='test@test.com',
            subject='Test Message',
            text='Test',
            delay=10,
        )
        response = self.client.get(reverse('message-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)

    def test_message_viewset_create(self):
        data = {
            'type': Message.Type.FINAL_WORD,
            'recipients': 'test@test.com',
            'subject': 'New Message',
            'text': 'Test content',
            'delay': 15,
        }
        response = self.client.post(reverse('message-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.user, self.user)
        self.assertEqual(message.subject, 'New Message')

    def test_message_viewset_filter(self):
        Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='test@test.com',
            subject='Test Final',
            text='Test',
            delay=10,
        )
        Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='test@test.com',
            subject='Test Capsule',
            text='Test',
            scheduled_at=self.scheduled_at,
        )

        response = self.client.get(reverse('message-list') + '?type=FINAL_WORD')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)
        self.assertEqual(response.json()['results'][0]['type'], 'FINAL_WORD')

    def test_activity_log_viewset(self):
        ActivityLog.objects.create(user=self.user, type=ActivityLog.Type.CHECKED_IN)
        response = self.client.get(reverse('activity-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)
        self.assertEqual(response.json()['results'][0]['type'], 'CHECKED_IN')


class SerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='test@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )

    def test_message_serializer_update(self):
        data = {
            'type': Message.Type.TIME_CAPSULE,
            'subject': 'Updated Subject',
            'text': 'Updated text',
            'delay': 20,
            'recipients': 'updated@test.com',
        }

        serializer = MessageSerializer(self.message, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_message = serializer.save()

        self.assertEqual(updated_message.subject, 'Updated Subject')
        self.assertEqual(updated_message.text, 'Updated text')
        self.assertEqual(updated_message.delay, 20)
        self.assertEqual(updated_message.recipients, 'updated@test.com')
        self.assertEqual(updated_message.type, Message.Type.FINAL_WORD)
