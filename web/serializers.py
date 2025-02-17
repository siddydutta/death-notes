from rest_framework import serializers

from accounts.models import User
from web.models import ActivityLog, Message


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'interval',
        )
        read_only_fields = (
            'id',
            'email',
        )


class MessageSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Message
        fields = (
            'id',
            'user',
            'type',
            'recipients',
            'status',
            'subject',
            'text',
            'delay',
            'scheduled_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'status',
            'created_at',
            'updated_at',
        )

    def update(self, instance, validated_data):
        validated_data.pop('type', None)
        return super().update(instance, validated_data)


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = (
            'id',
            'timestamp',
            'type',
            'description',
        )
