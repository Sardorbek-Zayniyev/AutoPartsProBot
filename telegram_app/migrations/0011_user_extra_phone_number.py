# Generated by Django 5.1.5 on 2025-02-03 17:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0010_user_city_user_state_user_street_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='extra_phone_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
