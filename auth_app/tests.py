from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from auth_app.clients.microsoft import REDIRECT_URI, SCOPES


class MSLoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('auth_app.clients.microsoft.msal_app.get_authorization_request_url')
    def test_login_redirects_to_msal(self, mock_get_auth_url):
        mock_get_auth_url.return_value = 'https://login.microsoftonline.com/auth'

        response = self.client.get(reverse('ms-login'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://login.microsoftonline.com/auth')
        mock_get_auth_url.assert_called_once_with(
            scopes=SCOPES, redirect_uri=REDIRECT_URI
        )


class MSLoginCallbackViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('auth_app.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    @patch('auth_app.views.get_user_info')
    def test_callback_valid_code(self, mock_get_user_info, mock_acquire_token):
        mock_acquire_token.return_value = {'access_token': 'mock_token'}
        mock_get_user_info.return_value = {'email': 'test@example.com'}

        response = self.client.get(reverse('ms-callback'), {'code': 'valid_code'})

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'email': 'test@example.com'})
        mock_acquire_token.assert_called_once_with(
            code='valid_code', scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
        mock_get_user_info.assert_called_once_with('mock_token')

    def test_callback_missing_code(self):
        response = self.client.get(reverse('ms-callback'))

        self.assertEqual(response.status_code, 400)

    @patch('auth_app.clients.microsoft.msal_app.acquire_token_by_authorization_code')
    def test_callback_invalid_token(self, mock_acquire_token):
        mock_acquire_token.return_value = {}

        response = self.client.get(reverse('ms-callback'), {'code': 'invalid_code'})

        self.assertEqual(response.status_code, 400)
        mock_acquire_token.assert_called_once()
