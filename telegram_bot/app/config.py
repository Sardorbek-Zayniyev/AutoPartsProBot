import os
import sys
import django
from decouple import config 

sys.path.append('/home/sardorbee/AAAAAAAAAAProjects/AutoPartsProBot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AutoPartsProBot.settings')
django.setup()

BOT_TOKEN=config('BOT_TOKEN')