# apps.py
from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'  # Replace with your app name

    def ready(self):
        import messaging.signals  # Replace 'messaging' with your app name
