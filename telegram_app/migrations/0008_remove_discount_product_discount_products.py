# Generated by Django 5.1.5 on 2025-02-01 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0007_promocode_remove_cartitem_discount_product_quality_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='discount',
            name='product',
        ),
        migrations.AddField(
            model_name='discount',
            name='products',
            field=models.ManyToManyField(related_name='discounts', to='telegram_app.product'),
        ),
    ]
