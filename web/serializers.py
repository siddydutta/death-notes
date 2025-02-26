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
    # user field is hidden and set to the current user
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
            'id',
            'status',
            'created_at',
            'updated_at',
        )

    def update(self, instance: Message, validated_data: dict) -> Message:
        """Override the update method to prevent the update of type and user fields."""
        validated_data.pop('type', None)
        validated_data.pop('user', None)
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
