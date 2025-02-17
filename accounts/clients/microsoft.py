import requests

from django.conf import settings
from msal import ConfidentialClientApplication


REDIRECT_URI = settings.MSAL_REDIRECT_URI

USER_INFO_URL = 'https://graph.microsoft.com/v1.0/me'

SCOPES = ['User.Read']

msal_app = ConfidentialClientApplication(
    client_id=settings.MSAL_CLIENT_ID,
    client_credential=settings.MSAL_CLIENT_SECRET,
    authority=settings.MSAL_AUTHORITY,
)


def get_user_info(access_token: str) -> dict:
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(USER_INFO_URL, headers=headers)
    return response.json()
