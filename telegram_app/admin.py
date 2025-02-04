from django.contrib import admin
from .models import Category, Product, User, CarBrand, CarModel, Cart, CartItem, SavedItemList, SavedItem, Discount, Promocode, AppliedPromocode, Order, OrderItem
from django.db import transaction

class ProductInline(admin.TabularInline):
    model = Product
    fields = ('name', 'car_brand', 'car_model', 'price', 'available', 'stock')
    extra = 0

class CarModelInline(admin.TabularInline):
    model = CarModel
    fields = ('name',)
    extra = 0

class CartItemInline(admin.TabularInline):
    model = CartItem
    fields = ('product', 'quantity', 'subtotal')
    extra = 0
    readonly_fields = ('subtotal',)

class SavedItemInline(admin.TabularInline):
    model = SavedItem
    extra = 0  
    readonly_fields = ('product', 'added_at')  

class AppliedPromocodeInline(admin.TabularInline):
    model = AppliedPromocode
    fields = ('promocode',)
    extra = 0

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product', 'quantity', 'price', 'subtotal')
    extra = 0   
    readonly_fields = ('subtotal',)


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
    list_display = ('name', 'category', 'car_brand', 'car_model', 'price', 'available', 'stock', 'quality', 'reserved_stock')
    list_filter = ('category', 'car_brand', 'available')
    search_fields = ('name', 'car_brand__name', 'car_model__name')
    ordering = ('category', 'car_brand', 'car_model')
    readonly_fields = ('id',)
    fieldsets = (
        ('General Information', {
            'fields': ('category', 'car_brand', 'car_model', 'name', 'description', 'quality',),
        }),
        ('Pricing and Availability', {
            'fields': ('price', 'available', 'stock', 'reserved_stock'),
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
    inlines = [CartItemInline, AppliedPromocodeInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('cart', 'product')
    search_fields = ('cart__id', 'product__name')
    

@admin.register(SavedItemList)
class SavedItemListAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'created_at')  
    search_fields = ('user__username', 'name')  
    inlines = [SavedItemInline] 

@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'saved_item_list', 'added_at') 
    list_filter = ('saved_item_list__user', 'product') 

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    def display_products(self, obj):
        return ", ".join([product.name for product in obj.products.all()])
    
    display_products.short_description = 'Products' 

    list_display = ('display_products', 'percentage', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('products__name',) 
    ordering = ('-start_date',)

@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'valid_from', 'valid_until', 'is_active', 'usage_limit')
    list_filter = ('is_active',)
    search_fields = ('code',)
    ordering = ('-valid_from',)

@admin.register(AppliedPromocode)
class AppliedPromocodeAdmin(admin.ModelAdmin):
    list_display = ('cart', 'promocode', 'applied_at')
    search_fields = ('cart__id', 'promocode__code')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total_price', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status')
    search_fields = ('order_id', 'user__full_name')
    ordering = ('-created_at',)
    # inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('order', 'product')
    search_fields = ('order__id', 'product__name')
