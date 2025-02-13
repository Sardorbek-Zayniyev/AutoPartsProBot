import os
import sys
import django
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Django loyihasi joylashgan katalogni qo‘shish
sys.path.append('/home/sardorbee/AAAAAAAAAAProjects/AutoPartsProBot')

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AutoPartsProBot.settings.local')

django.setup()

BOT_TOKEN = config('BOT_TOKEN')
