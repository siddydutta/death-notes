from typing import Callable
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from msal import ConfidentialClientApplication
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.clients.microsoft import SCOPES, USER_INFO_URL, get_user_info, msal_app
from accounts.models import User


class ViewTests(APITestCase):
    """Test the views in the accounts app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_uri = 'http://localhost:8000/api/auth/microsoft/callback/'

    @patch('accounts.clients.microsoft.msal_app.get_authorization_request_url')
    def test_microsoft_auth_url_api_view(
        self, mock_get_auth_url: Callable[[list[str], str], str]
    ):
        """Test the MicrosoftAuthUrlAPIView.

        Args:
            mock_get_auth_url (Callable[[list[str], str], str]): Mocked get_authorization_request_url function.
        """
        # Given
        mock_get_auth_url.return_value = 'https://login.microsoftonline.com/auth'
        # When
        response = self.client.get(
            reverse('ms-auth-url') + f'?redirect_uri={self.redirect_uri}'
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIsInstance(response.json().get('auth_url'), str)
        mock_get_auth_url.assert_called_once_with(
            scopes=SCOPES, redirect_uri=self.redirect_uri
        )

    def test_microsoft_login_callback_api_view_get(self):
        """Test the MicrosoftLoginCallbackAPIView GET method."""
        # Given
        # When
        response = self.client.get(reverse('ms-callback') + '?code=fake_code')
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.json()['code'], 'fake_code')

    @patch('accounts.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    @patch('accounts.views.get_user_info')
    def test_microsoft_login_callback_api_view_post_success(
        self,
        mock_get_user_info: Callable[[str], dict],
        mock_acquire_token: Callable[[str, list[str], str], dict],
    ):
        """Test the MicrosoftLoginCallbackAPIView POST method.

        Args:
            mock_get_user_info (Callable[[str], dict]): Mocked get_user_info function.
            mock_acquire_token (Callable[[str, list[str], str], dict]): Mocked acquire_token_by_authorization_code function.
        """
        # Given
        mock_acquire_token.return_value = {'access_token': 'fake_access_token'}
        mock_get_user_info.return_value = {
            'mail': 'test@example.com',
            'givenName': 'Test',
            'surname': 'User',
        }
        # When
        response = self.client.post(
            reverse('ms-callback'),
            {'code': 'fake_code', 'redirect_uri': self.redirect_uri},
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('user', response.json())
        self.assertIn('refresh', response.json())
        self.assertIn('access', response.json())
        mock_acquire_token.assert_called_once_with(
            code='fake_code', scopes=SCOPES, redirect_uri=self.redirect_uri
        )
        mock_get_user_info.assert_called_once_with('fake_access_token')
        # When
        response = self.client.post(
            reverse('ms-callback'),
            {'code': 'fake_code', 'redirect_uri': self.redirect_uri},
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_microsoft_login_callback_api_view_post_no_code(self):
        """Test the MicrosoftLoginCallbackAPIView POST method with no code."""
        # Given
        # When
        response = self.client.post(
            reverse('ms-callback'), {'redirect_uri': self.redirect_uri}
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('error', response.json())

    @patch('accounts.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    def test_microsoft_login_callback_api_view_post_invalid_grant(
        self,
        mock_acquire_token: Callable[[str, list[str], str], dict],
    ):
        """Test the MicrosoftLoginCallbackAPIView POST method with invalid grant.

        Args:
            mock_acquire_token (Callable[[str, list[str], str], dict]): Mocked acquire_token_by_authorization_code function.
        """
        # Given
        mock_acquire_token.return_value = {}
        # When
        response = self.client.post(
            reverse('ms-callback'),
            {'code': 'fake_code', 'redirect_uri': self.redirect_uri},
        )
        # Then
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('error', response.json())
        mock_acquire_token.assert_called_once_with(
            code='fake_code', scopes=SCOPES, redirect_uri=self.redirect_uri
        )


class ClientTests(TestCase):
    """Test the external client functions."""

    @patch('accounts.clients.microsoft.requests.get')
    def test_get_user_info_success(self, mock_get: Callable[[str], dict]):
        """Test the get_user_info function with a valid token.

        Args:
            mock_get (Callable[[str], dict]): Mocked requests.get function.
        """
        # Given
        expected_data = {
            'mail': 'test@example.com',
            'givenName': 'Test',
            'surname': 'User',
        }
        mock_get.return_value.json.return_value = expected_data
        # When
        result = get_user_info('fake_access_token')
        # Then
        self.assertEqual(result, expected_data)
        mock_get.assert_called_once_with(
            USER_INFO_URL, headers={'Authorization': 'Bearer fake_access_token'}
        )

    @patch('accounts.clients.microsoft.requests.get')
    def test_get_user_info_error(self, mock_get: Callable[[str], dict]):
        """Test the get_user_info function with an invalid token.

        Args:
            mock_get (Callable[[str], dict]): Mocked requests.get function.
        """
        # Given
        mock_get.return_value.json.return_value = {'error': 'Invalid token'}
        # When
        result = get_user_info('invalid_token')
        # Then
        self.assertEqual(result, {'error': 'Invalid token'})
        mock_get.assert_called_once_with(
            USER_INFO_URL, headers={'Authorization': 'Bearer invalid_token'}
        )

    def test_msal_configuration(self):
        """Test the MSAL configuration."""
        # Given
        # When
        # Then
        self.assertEqual(SCOPES, ['User.Read'])
        self.assertIsInstance(msal_app, ConfidentialClientApplication)


class ModelTests(TestCase):
    """Test the models in the accounts app."""

    def test_create_user(self):
        """Test creating a user."""
        # Given
        # When
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            interval=7,
        )
        # Then
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.interval, 7)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.last_checkin)
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(str(user), 'test@example.com')

    def test_create_user_without_email(self):
        """Test creating a user without an email."""
        # Given
        # When
        # Then
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='testpass123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        # Given
        # When
        admin_user = User.objects.create_superuser(
            email='admin@example.com', password='admin123'
        )
        # Then
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)


class SignalTests(TestCase):
    """Test the signals in the accounts app."""

    def test_pre_save_user(self):
        """Test the pre_save_user signal handler."""
        # Given
        user = User.objects.create_user(
            email='user@test.com', password='foobar', interval=7
        )
        # When
        user.interval = 14
        user.save()
        # Then
        self.assertTrue(hasattr(user, '__previous_interval'))
        self.assertEqual(getattr(user, '__previous_interval'), 7)
