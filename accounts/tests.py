from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.clients.microsoft import REDIRECT_URI, SCOPES


class ViewsTests(APITestCase):
    @patch('accounts.clients.microsoft.msal_app.get_authorization_request_url')
    def test_microsoft_auth_url_api_view(self, mock_get_auth_url):
        mock_get_auth_url.return_value = 'https://login.microsoftonline.com/auth'

        response = self.client.get(reverse('ms-auth-url'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIsInstance(response.json().get('auth_url'), str)
        mock_get_auth_url.assert_called_once_with(
            scopes=SCOPES, redirect_uri=REDIRECT_URI
        )

    @patch('accounts.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    @patch('accounts.views.get_user_info')
    def test_microsoft_login_callback_api_view_post_success(
        self, mock_get_user_info, mock_acquire_token
    ):
        mock_acquire_token.return_value = {'access_token': 'fake_access_token'}
        mock_get_user_info.return_value = {
            'mail': 'test@example.com',
            'givenName': 'Test',
            'surname': 'User',
        }

        response = self.client.post(reverse('ms-callback'), {'code': 'fake_code'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('user', response.json())
        self.assertIn('refresh', response.json())
        self.assertIn('access', response.json())
        mock_acquire_token.assert_called_once_with(
            code='fake_code', scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
        mock_get_user_info.assert_called_once_with('fake_access_token')

    def test_microsoft_login_callback_api_view_post_no_code(self):
        response = self.client.post(reverse('ms-callback'), {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('error', response.json())

    @patch('accounts.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    def test_microsoft_login_callback_api_view_post_invalid_grant(
        self, mock_acquire_token
    ):
        mock_acquire_token.return_value = {}

        response = self.client.post(reverse('ms-callback'), {'code': 'fake_code'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('error', response.json())
        mock_acquire_token.assert_called_once_with(
            code='fake_code', scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
