from django.urls import include, path
from rest_framework.routers import DefaultRouter

from web.views import (
    ActivityLogViewSet,
    CheckinAPIView,
    HomeAPIView,
    MessageViewSet,
    UserAPIView,
)


router = DefaultRouter()
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'activity', ActivityLogViewSet, basename='activity')


urlpatterns = [
    path('', include(router.urls)),
    path('home/', HomeAPIView.as_view(), name='home'),
    path('checkin/', CheckinAPIView.as_view(), name='checkin'),
    path('user/', UserAPIView.as_view(), name='user'),
]
