# Generated by Django 5.1.5 on 2025-03-15 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0018_rewardhistory_is_used'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_pending_message_id',
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]
