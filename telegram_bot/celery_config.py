import os
from celery import Celery

# Django sozlamalar moduli
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AutoPartsProBot.settings.local')

app = Celery('telegram_bot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()