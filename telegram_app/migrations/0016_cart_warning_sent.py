# Generated by Django 5.1.5 on 2025-03-04 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0015_remove_product_reserved_until_cart_reserved_until'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='warning_sent',
            field=models.BooleanField(default=False),
        ),
    ]
