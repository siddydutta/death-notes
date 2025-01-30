from django.urls import path

from auth_app.views import MSLoginCallbackView, MSLoginView


urlpatterns = [
    path('microsoft/login/', MSLoginView.as_view(), name='ms-login'),
    path('microsoft/callback/', MSLoginCallbackView.as_view(), name='ms-callback'),
]
