from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from accounts.models import User
from web.models import ActivityLog, Message
from web.serializers import ActivityLogSerializer, MessageSerializer, UserSerializer


class HomeAPIView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Message.objects.filter(user=request.user)

        response = {
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


class UserAPIView(APIView):
    serializer_class = UserSerializer

    def get_object(self):
        return User.objects.filter(id=self.request.user.id).first()

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.serializer_class(obj, many=False)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class MessageViewSet(ModelViewSet):
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ('type',)
    ordering_fields = (
        'delay',
        'scheduled_at',
        'subject',
    )
    ordering = ('-id',)
    search_fields = (
        'recipients',
        'subject',
    )

    def get_queryset(self):
        return Message.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ActivityLogViewSet(GenericViewSet, ListModelMixin):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    ordering = ('-id',)
    ordering_fields = ('timestamp',)

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user)
