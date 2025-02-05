from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'

    def ready(self):
        # connect signals
        import web.signals  # noqa: F401

        return super().ready()
