# Generated by Django 5.1.5 on 2025-01-31 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0002_carbrand_category_discountcode_carmodel_cart_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_id',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
