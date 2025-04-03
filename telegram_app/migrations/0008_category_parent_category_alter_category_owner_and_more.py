# Generated by Django 5.1.5 on 2025-02-21 23:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_app', '0007_alter_category_owner_alter_product_available_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='parent_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sub_categories', to='telegram_app.category'),
        ),
        migrations.AlterField(
            model_name='category',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='owned_categories', to='telegram_app.user'),
        ),
        migrations.AlterField(
            model_name='category',
            name='updated_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='updated_categories', to='telegram_app.user'),
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(default='This is product name', max_length=255),
        ),
    ]
