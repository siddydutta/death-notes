import requests

from django.conf import settings
from msal import ConfidentialClientApplication


# URI to which Microsoft will redirect the user to after authentication
REDIRECT_URI = settings.MSAL_REDIRECT_URI

# URL to fetch user information from the Microsoft API
USER_INFO_URL = 'https://graph.microsoft.com/v1.0/me'

# scopes required to access user information
SCOPES = ['User.Read']

msal_app = ConfidentialClientApplication(
    client_id=settings.MSAL_CLIENT_ID,
    client_credential=settings.MSAL_CLIENT_SECRET,
    authority=settings.MSAL_AUTHORITY,
)


def get_user_info(access_token: str) -> dict:
    """
    Fetches user information from the Microsoft API using the provided access token.

    Args:
        access_token (str): The access token returned by Microsoft.

    Returns:
        dict: A dictionary containing the user's information retrieved from the API.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(USER_INFO_URL, headers=headers)
    return response.json()
