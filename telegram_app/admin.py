from django.contrib import admin
from .models import Category, Product, User, CarBrand, CarModel, Cart, CartItem, Wishlist, DiscountCode, Order, SavedItem, AppliedDiscount
from django.db import transaction


class ProductInline(admin.TabularInline):
    model = Product
    fields = ('name', 'car_brand', 'car_model', 'price', 'available')
    extra = 0


class CarModelInline(admin.TabularInline):
    model = CarModel
    fields = ('name',)
    extra = 0

class CartItemInline(admin.TabularInline):
    model = CartItem
    fields = ('product', 'quantity', 'discount', 'subtotal')
    extra = 0
    readonly_fields = ('subtotal',)


class AppliedDiscountInline(admin.TabularInline):
    model = AppliedDiscount
    fields = ('discount_code',)
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


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'total_price', 'created_at', 'updated_at')
    list_filter = ('is_active', 'user')
    search_fields = ('user__full_name', 'id')
    inlines = [CartItemInline, AppliedDiscountInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity', 'discount', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('cart', 'product')
    search_fields = ('cart__id', 'product__name')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__full_name',)


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added_at')
    search_fields = ('user__full_name', 'product__name')


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code',)


@admin.register(AppliedDiscount)
class AppliedDiscountAdmin(admin.ModelAdmin):
    list_display = ('cart', 'discount_code')
    list_filter = ('discount_code', 'cart')
    search_fields = ('cart__id', 'discount_code__code')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'user')
    search_fields = ('user__full_name', 'id')
    readonly_fields = ('total_price',)