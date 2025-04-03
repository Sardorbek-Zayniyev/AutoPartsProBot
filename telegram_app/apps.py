from django.apps import AppConfig


class TelegramAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_app'
    verbose_name = "AutoPartsProBot Management" 

    def ready(self):
        import telegram_app.signals 