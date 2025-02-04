from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
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
                ),
            },
        ),
    )
