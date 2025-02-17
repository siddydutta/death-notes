import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.clients.microsoft import REDIRECT_URI, SCOPES, get_user_info, msal_app


User = get_user_model()
logger = logging.getLogger(__name__)


class MicrosoftAuthURLAPIView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        auth_url = msal_app.get_authorization_request_url(
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        return Response({'auth_url': auth_url})


class MicrosoftLoginCallbackAPIView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        code = request.GET.get('code')
        return Response({'code': code}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        if code is None:
            return Response(
                {'error': 'No code in request'}, status=status.HTTP_400_BAD_REQUEST
            )
        token_response = msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        access_token = token_response.get('access_token')
        if access_token is None:
            logger.debug(token_response)
            return Response(
                {'error': 'Invalid grant'}, status=status.HTTP_403_FORBIDDEN
            )
        user_info = get_user_info(access_token)
        user, created = User.objects.get_or_create(
            email=user_info['mail'],
            defaults={
                'first_name': user_info['givenName'],
                'last_name': user_info['surname'],
            },
        )
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
