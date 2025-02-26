from django.apps import AppConfig


class CronConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cron'

    def ready(self):
        # connect signals on app initialization
        import cron.signals  # noqa: F401

        return super().ready()
