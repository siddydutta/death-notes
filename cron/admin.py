from django.contrib import admin

from cron.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'message',
        'scheduled_at',
        'is_completed',
    )
    list_select_related = ('message',)
    autocomplete_fields = ('message',)
    search_fields = ('message__user__email',)
    list_filter = ('is_completed',)
