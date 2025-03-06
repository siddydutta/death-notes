from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # connect signals on app initialization
        import accounts.signals  # noqa: F401

        return super().ready()
