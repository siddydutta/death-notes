from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    """Admin class for the User model."""

    list_display = (
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
    )
    search_fields = ('email__istartswith',)
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email',)}),
        (
            'Personal Info',
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'interval',
                    'last_checkin',
                )
            },
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_superuser',
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'is_active',
                    'is_staff',
                    'password1',
                    'password2',
                ),
            },
        ),
    )
    readonly_fields = ('last_checkin',)
