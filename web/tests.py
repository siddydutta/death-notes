import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.timezone import now, timedelta
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from web.models import ActivityLog, Message
from web.serializers import MessageSerializer


User = get_user_model()


class SignalTests(TestCase):
    """Test the signals in the web app."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='user@test.com', password='foobar')

    def test_pre_save_message(self):
        """Test the pre_save signal for Message model."""
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        # When
        message.delay = 20
        message.save()
        # Then
        self.assertTrue(hasattr(message, '__previous_delay'))
        self.assertEqual(getattr(message, '__previous_delay'), 10)


class ModelTests(TestCase):
    """Test the models in the web app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = now() + timedelta(days=10)

    def test_save_final_word_message(self):
        """Test saving a final word message with validation checks."""
        # Given
        message = Message(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
            scheduled_at=self.scheduled_at,
        )
        # When
        with self.assertRaises(ValueError):
            message.save()
        message.delay = None
        message.scheduled_at = None
        with self.assertRaises(ValueError):
            message.save()
        message.delay = 10
        message.save()
        # Then
        self.assertEqual(str(message), 'Message 1 - FINAL_WORD - Test Subject')
        self.assertIsNotNone(message.id)

    def test_save_time_capsule_message(self):
        """Test saving a time capsule message with validation checks."""
        # Given
        message = Message(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
            scheduled_at=self.scheduled_at,
        )
        # When
        with self.assertRaises(ValueError):
            message.save()
        message.delay = None
        message.scheduled_at = None
        with self.assertRaises(ValueError):
            message.save()
        message.scheduled_at = now() - timedelta(days=1)
        with self.assertRaises(ValueError):
            message.save()
        message.scheduled_at = self.scheduled_at
        message.save()
        # Then
        self.assertIsNotNone(message.id)

    def test_send_message(self):
        """Test sending a message."""
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        # When
        with patch('web.models.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 1
            sent = message.send()
            # Then
            self.assertTrue(sent)
            self.assertEqual(message.status, Message.Status.DELIVERED)

    def test_send_delivered_message_no_force_send(self):
        """Test attempting to send an already delivered message without force send."""
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            status=Message.Status.DELIVERED,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        # When
        is_sent = message.send()
        # Then
        self.assertFalse(is_sent)

    def test_send_message_failed(self):
        """Test handling of message sending failure."""
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        # When
        with patch('web.models.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 0
            sent = message.send()
            # Then
            self.assertFalse(sent)
            self.assertEqual(message.status, Message.Status.FAILED)

    def test_activity_log_str(self):
        """Test string representation of ActivityLog model."""
        # Given
        ActivityLog.objects.create(user=self.user, type=ActivityLog.Type.CHECKED_IN)
        # When
        activity_log = ActivityLog.objects.first()
        # Then
        self.assertEqual(str(activity_log), 'Activity 1 - CHECKED_IN')


class ViewTests(APITestCase):
    """Test the API views in the web app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
        self.scheduled_at = now() + timedelta(days=10)

    def test_unauthorized_access(self):
        """Test that unauthenticated requests are rejected."""
        # Given
        self.client.credentials()
        # When
        response = self.client.get(reverse('home'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token(self):
        """Test handling of expired authentication tokens."""
        # Given
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + 'expired.token.here')
        # When
        response = self.client.get(reverse('home'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_home_api_view(self):
        """Test the home API view endpoint."""
        # Given
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
        # When
        response = self.client.get(reverse('home'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['total']['FINAL_WORD'], 1)
        self.assertEqual(response.json()['total']['TIME_CAPSULE'], 1)
        self.assertEqual(response.json()['delivered']['FINAL_WORD'], 0)
        self.assertEqual(response.json()['delivered']['TIME_CAPSULE'], 0)

    def test_checkin_api_view(self):
        """Test the check-in API endpoint."""
        # When
        response = self.client.post(reverse('checkin'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        activity_log = ActivityLog.objects.first()
        self.assertEqual(activity_log.user, self.user)
        self.assertEqual(activity_log.type, ActivityLog.Type.CHECKED_IN)
        self.assertIsNotNone(self.user.last_checkin)

    def test_user_api_view_get(self):
        """Test retrieving user information via the API."""
        # When
        response = self.client.get(reverse('user'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['email'], self.user.email)

    def test_user_api_view_patch(self):
        """Test updating user information via the API."""
        # Given
        data = {'first_name': 'Test', 'last_name': 'User'}
        # When
        response = self.client.patch(
            reverse('user'), data=json.dumps(data), content_type='application/json'
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')

    def test_message_viewset_list(self):
        """Test listing messages via the API."""
        # Given
        Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='test@test.com',
            subject='Test Message',
            text='Test',
            delay=10,
        )
        # When
        response = self.client.get(reverse('message-list'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)

    def test_message_viewset_create(self):
        """Test creating messages via the API."""
        # Given
        data = {
            'type': Message.Type.FINAL_WORD,
            'recipients': 'test@test.com',
            'subject': 'New Message',
            'text': 'Test content',
            'delay': 15,
        }
        # When
        response = self.client.post(reverse('message-list'), data)
        # Then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.user, self.user)
        self.assertEqual(message.subject, 'New Message')

    def test_message_viewset_filter(self):
        """Test filtering messages via the API."""
        # Given
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
        # When
        response = self.client.get(reverse('message-list') + '?type=FINAL_WORD')
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)
        self.assertEqual(response.json()['results'][0]['type'], 'FINAL_WORD')

    def test_activity_log_viewset(self):
        """Test retrieving activity logs via the API."""
        # Given
        ActivityLog.objects.create(user=self.user, type=ActivityLog.Type.CHECKED_IN)
        # When
        response = self.client.get(reverse('activity-list'))
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 1)
        self.assertEqual(response.json()['results'][0]['type'], 'CHECKED_IN')


class SerializerTests(TestCase):
    """Test the serializers in the web app."""

    def setUp(self):
        """Set up test data."""
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
        """Test updating a message via serializer."""
        # Given
        data = {
            'type': Message.Type.TIME_CAPSULE,
            'subject': 'Updated Subject',
            'text': 'Updated text',
            'delay': 20,
            'recipients': 'updated@test.com',
        }
        # When
        serializer = MessageSerializer(self.message, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_message = serializer.save()
        # Then
        self.assertEqual(updated_message.subject, 'Updated Subject')
        self.assertEqual(updated_message.text, 'Updated text')
        self.assertEqual(updated_message.delay, 20)
        self.assertEqual(updated_message.recipients, 'updated@test.com')
        self.assertEqual(updated_message.type, Message.Type.FINAL_WORD)
