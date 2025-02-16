from django.urls import path

from accounts.views import MicrosoftAuthURLAPIView, MicrosoftLoginCallbackAPIView


urlpatterns = [
    path('microsoft/url/', MicrosoftAuthURLAPIView.as_view(), name='ms-auth-url'),
    path(
        'microsoft/callback/',
        MicrosoftLoginCallbackAPIView.as_view(),
        name='ms-callback',
    ),
]
