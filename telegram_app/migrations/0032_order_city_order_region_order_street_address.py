# Generated by Django 5.1.5 on 2025-03-26 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0031_user_deleted_at_alter_order_cart_alter_order_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='city',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='region',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='street_address',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
