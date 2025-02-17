from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import MicrosoftAuthURLAPIView, MicrosoftLoginCallbackAPIView


urlpatterns = [
    path('token/refresh/', TokenRefreshView.as_view(), name='refresh-token'),
    path('microsoft/url/', MicrosoftAuthURLAPIView.as_view(), name='ms-auth-url'),
    path(
        'microsoft/callback/',
        MicrosoftLoginCallbackAPIView.as_view(),
        name='ms-callback',
    ),
]
