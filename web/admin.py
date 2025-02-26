from django.contrib import admin

from web.models import ActivityLog, Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin class for the Message model."""

    list_display = (
        'user',
        'type',
        'status',
        'subject',
        'delay',
        'scheduled_at',
    )
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    list_filter = (
        'type',
        'status',
    )
    search_fields = ('user__email',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin class for the ActivityLog model."""

    list_display = (
        'user',
        'type',
        'timestamp',
    )
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    list_filter = ('type',)
    search_fields = ('user__email',)
