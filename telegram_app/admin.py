from django.contrib import admin
from .models import Category, Product, User,  CarBrand, CarModel


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'telegram_id', 'phone_number', 'role')
    list_filter = ('role',)
    search_fields = ('full_name', 'telegram_id', 'phone_number', 'role')
    ordering = ('-role',)
    readonly_fields = ('id',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    readonly_fields = ('id',)


@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)  #
    readonly_fields = ('id',)


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'brand')
    list_filter = ('brand',)
    search_fields = ('name', 'brand__name')
    ordering = ('brand', 'name')
    readonly_fields = ('id',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'car_brand',
                    'car_model', 'price', 'available')
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
            'fields': ('photos',),
        }),
    )
