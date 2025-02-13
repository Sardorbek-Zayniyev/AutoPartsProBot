# Generated by Django 5.1.5 on 2025-02-13 21:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CarBrand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='Promocode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('discount_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('valid_from', models.DateTimeField()),
                ('valid_until', models.DateTimeField()),
                ('is_active', models.BooleanField(default=False)),
                ('usage_limit', models.PositiveIntegerField(default=1)),
                ('used_count', models.PositiveIntegerField(default=0)),
                ('required_points', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Reward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reward_type', models.CharField(choices=[('free_shipping', 'Free Shipping'), ('gift', 'Gift'), ('promocode', 'Promocode')], default='gift', max_length=20)),
                ('name', models.CharField(max_length=255)),
                ('points_required', models.PositiveIntegerField()),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.BigIntegerField(null=True, unique=True)),
                ('full_name', models.CharField(blank=True, max_length=255, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('extra_phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('role', models.CharField(choices=[('User', 'User'), ('Admin', 'Admin'), ('Superadmin', 'Superadmin')], default='User', max_length=50)),
                ('region', models.CharField(blank=True, max_length=100, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('street_address', models.CharField(blank=True, max_length=255, null=True)),
                ('points', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='CarModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='models', to='telegram_app.carbrand')),
            ],
            options={
                'unique_together': {('brand', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20)),
                ('payment_method', models.CharField(choices=[('Cash', 'Cash'), ('Card', 'Card'), ('Online', 'Online')], default='Cash', max_length=10)),
                ('payment_status', models.CharField(choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid')], default='Unpaid', max_length=10)),
                ('order_id', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order', to='telegram_app.cart')),
                ('promocode', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='telegram_app.promocode')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='telegram_app.user')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('available', models.BooleanField(default=False)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='product_photos/')),
                ('stock', models.PositiveIntegerField(default=0)),
                ('reserved_stock', models.PositiveIntegerField(default=0)),
                ('quality', models.CharField(choices=[('new', 'New'), ('renewed', 'Renewed'), ('excellent', 'Excellent'), ('good', 'Good'), ('acceptable', 'Acceptable')], default='new', max_length=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('car_brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='telegram_app.carbrand')),
                ('car_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='telegram_app.carmodel')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='telegram_app.category')),
                ('owner', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='owned_products', to='telegram_app.user')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updated_products', to='telegram_app.user')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='telegram_app.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='telegram_app.product')),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='telegram_app.cart')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_items', to='telegram_app.product')),
            ],
        ),
        migrations.CreateModel(
            name='AppliedPromocode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applied_promocodes', to='telegram_app.cart')),
                ('promocode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applied_carts', to='telegram_app.promocode')),
            ],
        ),
        migrations.AddField(
            model_name='promocode',
            name='reward',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='promocode', to='telegram_app.reward'),
        ),
        migrations.CreateModel(
            name='SavedItemList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Wishlist', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_item_lists', to='telegram_app.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'name')},
            },
        ),
        migrations.AddField(
            model_name='reward',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='owned_rewards', to='telegram_app.user'),
        ),
        migrations.AddField(
            model_name='reward',
            name='updated_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updated_rewards', to='telegram_app.user'),
        ),
        migrations.AddField(
            model_name='promocode',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='owned_promocodes', to='telegram_app.user'),
        ),
        migrations.AddField(
            model_name='promocode',
            name='updated_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='updated_promocodes', to='telegram_app.user'),
        ),
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, null=True)),
                ('percentage', models.DecimalField(decimal_places=2, help_text='Discount percentage (e.g. 10 for 10%)', max_digits=5)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('is_active', models.BooleanField(default=False)),
                ('products', models.ManyToManyField(blank=True, related_name='discounts', to='telegram_app.product')),
                ('owner', models.ForeignKey(default=1, editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='owned_discounts', to='telegram_app.user')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updated_discounts', to='telegram_app.user')),
            ],
        ),
        migrations.AddField(
            model_name='cart',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='carts', to='telegram_app.user'),
        ),
        migrations.CreateModel(
            name='SavedItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='telegram_app.product')),
                ('saved_item_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_items', to='telegram_app.saveditemlist')),
            ],
            options={
                'ordering': ['-added_at'],
                'unique_together': {('saved_item_list', 'product')},
            },
        ),
    ]
