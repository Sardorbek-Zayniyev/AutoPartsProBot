from django.contrib import admin
from .models import Category, Product, User, CarBrand, CarModel
from django.db import transaction


class ProductInline(admin.TabularInline):
    model = Product
    fields = ('name', 'car_brand', 'car_model', 'price', 'available')
    extra = 0


class CarModelInline(admin.TabularInline):
    model = CarModel
    fields = ('name',)
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'telegram_id', 'phone_number', 'role')
    list_filter = ('role',)
    search_fields = ('full_name', 'telegram_id', 'phone_number', 'role')
    ordering = ('-role',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [ProductInline]


@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [CarModelInline]


class ProductByCarModelInline(admin.TabularInline):
    model = Product
    fields = ('name', 'category', 'price', 'available')
    extra = 0


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand')
    list_filter = ('brand',)
    search_fields = ('name', 'brand__name')
    ordering = ('brand', 'name')
    inlines = [ProductByCarModelInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'category', 'car_brand', 'car_model', 'price', 'available')
    list_filter = ('category', 'car_brand', 'available')
    search_fields = ('name', 'car_brand__name', 'car_model__name')
    ordering = ('category', 'car_brand', 'car_model')
    readonly_fields = ('id',)
    fieldsets = (
        ('General Information', {
            'fields': ('category', 'car_brand', 'car_model', 'name', 'description'),
        }),
        ('Pricing and Availability', {
            'fields': ('price', 'available'),
        }),
        ('Images', {
            'fields': ('photo',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Admin panelda tranzaktsiya bilan modelni saqlash."""
        with transaction.atomic():
            # Agar brend va model mos kelmasa, yangisini yaratadi yoki bog'laydi
            if obj.car_model and obj.car_model.brand != obj.car_brand:
                car_model = CarModel.objects.filter(
                    name=obj.car_model.name, brand=obj.car_brand
                ).first()
                if not car_model:
                    car_model = CarModel.objects.create(
                        name=obj.car_model.name,
                        brand=obj.car_brand
                    )
                obj.car_model = car_model

            # Asosiy saqlash funksiyasini chaqiramiz
            super().save_model(request, obj, form, change)
