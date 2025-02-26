from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from accounts.models import User
from web.models import ActivityLog, Message
from web.serializers import ActivityLogSerializer, MessageSerializer, UserSerializer


class HomeAPIView(APIView):
    """API for retrieving user statistics for the home page."""

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Computes user statistics and returns them.

        Args:
            request (Request): The request object.

        Returns:
            Response: A response object with user statistics.
        """
        queryset = Message.objects.filter(user=request.user)
        response = {
            'last_checkin': request.user.last_checkin,
            'total': {
                'FINAL_WORD': queryset.filter(type=Message.Type.FINAL_WORD).count(),
                'TIME_CAPSULE': queryset.filter(type=Message.Type.TIME_CAPSULE).count(),
            },
            'delivered': {
                'FINAL_WORD': queryset.filter(
                    type=Message.Type.FINAL_WORD, status=Message.Status.DELIVERED
                ).count(),
                'TIME_CAPSULE': queryset.filter(
                    type=Message.Type.TIME_CAPSULE, status=Message.Status.DELIVERED
                ).count(),
            },
        }
        return Response(data=response, status=status.HTTP_200_OK)


class CheckinAPIView(APIView):
    """API for checking in to the app."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        """Updates the user's last checkin and creates an activity log.

        Args:
            request (Request): The request object.

        Returns:
            Response: A response object.
        """
        request.user.last_checkin = timezone.now()
        request.user.save()
        ActivityLog.objects.create(
            user=request.user,
            type=ActivityLog.Type.CHECKED_IN,
            description='Checked in to Death Notes',
        )
        return Response(status=status.HTTP_200_OK)


class UserAPIView(APIView):
    """APIs for retrieving and updating the user."""

    serializer_class = UserSerializer

    def get_object(self):
        """Retrieves user object based on the request user ID."""
        return User.objects.filter(id=self.request.user.id).first()

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Retrieves and returns the user.

        Args:
            request (Request): The request object.

        Returns:
            Response: A serialized user object.
        """
        obj = self.get_object()
        serializer = self.serializer_class(obj, many=False)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, *args, **kwargs) -> Response:
        """Updates and returns the user.

        Args:
            request (Request): The request object.

        Returns:
            Response: A serialized user object.
        """
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class MessageViewSet(ModelViewSet):
    """APIs for listing, retrieving, creating, updating, and deleting messages."""

    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ('type',)
    ordering = ('-id',)
    ordering_fields = (
        'delay',
        'scheduled_at',
        'subject',
    )
    search_fields = (
        'recipients',
        'subject',
    )

    def get_queryset(self):
        """Filtered queryset to prevent unauthorized access."""
        return Message.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set the user for the message to prevent BOLA."""
        serializer.save(user=self.request.user)


class ActivityLogViewSet(GenericViewSet, ListModelMixin):
    """API for listing activity logs."""

    serializer_class = ActivityLogSerializer
    ordering = ('-id',)
    ordering_fields = ('timestamp',)

    def get_queryset(self):
        """Filtered queryset to prevent unauthorized access."""
        return ActivityLog.objects.filter(user=self.request.user)
