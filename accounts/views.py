import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.clients.microsoft import SCOPES, get_user_info, msal_app


User = get_user_model()
logger = logging.getLogger(__name__)


class MicrosoftAuthURLAPIView(APIView):
    """API for the Microsoft Auth URL."""

    permission_classes = []  # publicly accessible API for auth

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Get the Microsoft Auth URL.

        Args:
            request (Request): The request object.

        Returns:
            Response: The auth URL in the response object..
        """
        redirect_uri = request.query_params.get('redirect_uri')
        auth_url = msal_app.get_authorization_request_url(
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        return Response({'auth_url': auth_url})


class MicrosoftLoginCallbackAPIView(APIView):
    """API for handling the Microsoft login callback."""

    permission_classes = []  # publicly accessible API for auth

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Echoes the code back to the client.

        Args:
            request (Request): The request object.

        Returns:
            Response: The code in the response object.
        """
        code = request.GET.get('code')
        return Response({'code': code}, status=status.HTTP_200_OK)

    def post(self, request: Request, *args, **kwargs) -> Response:
        """Handle the Microsoft login callback.

        Args:
            request (Request): The request object.

        Returns:
            Response: The user info and tokens in the response object.
        """
        code = request.data.get('code')  # code from Microsoft auth
        redirect_uri = request.data.get('redirect_uri')
        if code is None or redirect_uri is None:
            return Response(
                {'error': 'Missing parameters'}, status=status.HTTP_400_BAD_REQUEST
            )
        # validate code and get auth token
        token_response = msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        access_token = token_response.get('access_token')
        if access_token is None:
            logger.debug(token_response)
            return Response(
                {'error': 'Invalid grant'}, status=status.HTTP_403_FORBIDDEN
            )
        # get user info and create user if not exists
        user_info = get_user_info(access_token)
        user, created = User.objects.get_or_create(
            email=user_info['mail'],
            defaults={
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
            },
        )
        # create tokens for the user
        refresh = RefreshToken.for_user(user)
        response = {
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        if created:
            return Response(response, status=status.HTTP_201_CREATED)
        return Response(response, status=status.HTTP_200_OK)
