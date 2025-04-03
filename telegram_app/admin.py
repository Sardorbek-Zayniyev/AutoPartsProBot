from django.contrib import admin
from django.db import transaction
import uuid
from django.utils.html import format_html
from .models import (Category, Product, User, CarBrand, 
                     CarModel, Cart, CartItem, SavedItemList,
                     SavedItem, Discount, Promocode, 
                     Order, OrderItem, Reward, RewardHistory, 
                     PromocodeHistory, AppliedPromocode, Question)
from django import forms

class BaseAdmin(admin.ModelAdmin):
    """Admin panelda owner va updated_by maydonlarini avtomatik to‘ldiradigan asosiy class."""
    # def save_model(self, request, obj, form, change):
    #     """Obyektni yaratish yoki yangilashda owner va updated_by maydonlarini belgilash."""
    #     with transaction.atomic():
    #         if not change or not obj.pk:  # Yangi obyekt yaratilsa
    #             obj.owner = request.user
    #         obj.updated_by = request.user  # Har doim yangilangan user
    #         super().save_model(request, obj, form, change)
    pass

class SubCategoryInline(admin.TabularInline): 
    model = Category
    extra = 1  
    fk_name = 'parent_category'
    readonly_fields = ('description',)

class ProductInline(admin.TabularInline):
    model = Product
    fields = ('name', 'car_brand', 'car_model', 'price', 'available', 'stock', 'quality', 'reserved_stock')
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
    readonly_fields = ('product', 'created_at')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product', 'quantity', 'price', 'subtotal')
    extra = 0
    readonly_fields = ('subtotal',)

class PromocodeInline(admin.StackedInline):
    model = Promocode
    extra = 0
    fields = ('code', 'discount_percentage', 'valid_from', 'valid_until', 'is_active', 'usage_limit', 'required_points')
    show_change_link = True

class AppliedPromocodeInline(admin.TabularInline):
    model = AppliedPromocode
    fields = ('promocode', 'applied_at')
    extra = 0
    readonly_fields = ('applied_at',)
    autocomplete_fields = ['promocode']
    verbose_name = "Applied Promocode"
    verbose_name_plural = "Applied Promocodes"

@admin.register(User)
class UserAdmin(BaseAdmin):
    list_display = ('full_name', 'telegram_id', 'phone_number', 'role')
    list_filter = ('role',)
    search_fields = ('full_name', 'telegram_id', 'phone_number', 'role')
    ordering = ('-role',)
    jazzmin_settings = {
        "list_filter_sticky": True,  # Sticky filters on the sidebar
        "list_per_page": 20,         # Fewer items per page for better readability
    }

@admin.register(Category)
class CategoryAdmin(BaseAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)
    readonly_fields = ('description', 'owner', 'updated_by')
    inlines = [SubCategoryInline, ProductInline]
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sub_categories")
    jazzmin_settings = {
        "list_per_page": 15,
        "related_modal_active": True,  # Enable modal popups for related objects
    }

@admin.register(CarBrand)
class CarBrandAdmin(BaseAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [CarModelInline]
    jazzmin_settings = {
        "list_filter_sticky": True,
    }

class ProductByCarModelInline(admin.TabularInline):
    model = Product
    fields = ('name', 'category', 'price', 'available')
    extra = 0

@admin.register(CarModel)
class CarModelAdmin(BaseAdmin):
    list_display = ('id', 'name', 'brand')
    list_filter = ('brand',)
    search_fields = ('name', 'brand__name')
    ordering = ('brand', 'name')
    inlines = [ProductByCarModelInline]

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.car_brand:
            self.fields["car_model"].queryset = CarModel.objects.filter(brand=self.instance.car_brand).order_by("name")
        else:
            self.fields["car_model"].queryset = CarModel.objects.none()

@admin.register(Product)
class ProductAdmin(BaseAdmin):
    form = ProductForm
    list_display = ('name', 'category', 'car_brand', 'car_model', 'price', 'available','is_active', 'stock', 'quality', 'reserved_stock')
    list_filter = ('category', 'car_brand', 'car_model', 'available', 'owner')
    search_fields = ('name', 'car_brand__name', 'car_model__name', 'owner__full_name')
    ordering = ('category', 'car_brand', 'car_model')
    readonly_fields = ('id', 'owner')
    fieldsets = (
        ('General Information', {
            'fields': ('category', 'car_brand', 'car_model', 'name', 'description', 'quality', 'is_active', 'status', 'rejection_reason',  'owner', 'updated_by'),
        }),
        ('Pricing and Availability', {
            'fields': ('price', 'available', 'stock', 'reserved_stock'),
        }),
        ('Images', {
            'fields': ('photo',),
        }),
    )
    autocomplete_fields = ["car_brand", "car_model"]
    class Media:
        js = ('admin/js/car_model_filter.js',)
    jazzmin_settings = {
        "list_per_page": 20,
        "show_ui_builder": True,  # Enable UI customization tool
        "changeform_format": "horizontal_tabs",  # Use tabs for form layout
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.order_by("name")
        elif db_field.name == "car_brand":
            kwargs["queryset"] = CarBrand.objects.order_by("name")
        elif db_field.name == "car_model":
            kwargs["queryset"] = CarModel.objects.order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if obj.car_model and obj.car_model.brand != obj.car_brand:
                car_model = CarModel.objects.filter(name=obj.car_model.name, brand=obj.car_brand).first()
                if not car_model:
                    car_model = CarModel.objects.create(name=obj.car_model.name, brand=obj.car_brand)
                obj.car_model = car_model
            super().save_model(request, obj, form, change)

@admin.register(Cart)
class CartAdmin(BaseAdmin):
    list_display = ('user', 'is_active', 'total_price', 'created_at', 'updated_at')
    list_filter = ('is_active', 'user')
    search_fields = ('user__full_name', 'id')
    readonly_fields = ('last_message_id',)
    inlines = [CartItemInline, AppliedPromocodeInline]
    jazzmin_settings = {
        "list_filter_sticky": True,
    }

@admin.register(CartItem)
class CartItemAdmin(BaseAdmin):
    list_display = ('product', 'cart', 'quantity', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('cart', 'product')
    search_fields = ('cart__id', 'product__name')

@admin.register(SavedItemList)
class SavedItemListAdmin(BaseAdmin):
    list_display = ('user', 'name', 'created_at')
    search_fields = ('user__username', 'name')
    inlines = [SavedItemInline]

@admin.register(SavedItem)
class SavedItemAdmin(BaseAdmin):
    list_display = ('product', 'saved_item_list', 'created_at')
    list_filter = ('saved_item_list__user', 'product')

@admin.register(Discount)
class DiscountAdmin(BaseAdmin):
    def display_products(self, obj):
        return ", ".join([product.name for product in obj.products.all()])
    display_products.short_description = 'Products'
    list_display = ('name', 'percentage', 'display_products', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('products__name',)
    ordering = ('-start_date',)
    jazzmin_settings = {
        "list_per_page": 15,
        "related_modal_active": True,
    }

@admin.register(Promocode)
class PromocodeAdmin(BaseAdmin):
    list_display = ('code', 'discount_percentage', 'valid_from', 'valid_until', 'is_active', 'usage_limit', 'used_count')
    list_filter = ('is_active',)
    search_fields = ('code',)
    ordering = ('-valid_from',)
    fieldsets = (
        ('General Information', {
            'fields': ('code', 'discount_percentage', 'valid_from', 'valid_until', 'is_active'),
        }),
        ('Usage Details', {
            'fields': ('usage_limit', 'used_count', 'required_points'),
        }),
    )
    jazzmin_settings = {
        "changeform_format": "vertical_tabs",
    }
    def save_model(self, request, obj, form, change):
        if not obj.code:
            obj.code = str(uuid.uuid4())[:8].upper()
        super().save_model(request, obj, form, change)

@admin.register(Order)
class OrderAdmin(BaseAdmin):
    list_display = ('order_display', 'user', 'status_colored', 'total_price', 'payment_status_colored', 'created_at')
    list_filter = ('status', 'payment_status')
    search_fields = ('order_id', 'user__full_name')
    ordering = ('-created_at',)
    
    jazzmin_settings = {
        "list_filter_sticky": True,
    }

    def order_display(self, obj):
        return f"#{obj.order_id}_{obj.user}"
    
    def status_colored(self, obj):
        colors = {
            'Pending': '#ff9800',    # To‘q sariq
            'Delivered': '#4caf50',    # Yashil
            'Shipped': '#2196f3',  # Moviy
            'Cancelled': '#f44336',  # Qizil
        }
        color = colors.get(obj.status, '#757575')  # Default kulrang

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    def payment_status_colored(self, obj):
        colors = {
            'Unpaid': '#f44336',  # 🔴 Qizil
            'Paid': '#4caf50',    # 🟢 Yashil
        }
        color = colors.get(obj.payment_status, '#757575')  # Default kulrang

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    
    status_colored.admin_order_field = 'status'
    status_colored.short_description = '📌 Holati'

    payment_status_colored.admin_order_field = 'payment_status'
    payment_status_colored.short_description = '💳 To‘lov holati'

@admin.register(OrderItem)
class OrderItemAdmin(BaseAdmin):
    list_display = ('product', 'order', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('order', 'product')
    search_fields = ('order__id', 'product__name')

@admin.register(Reward)
class RewardAdmin(BaseAdmin):
    list_display = ('name', 'reward_type', 'points_required', 'is_active', 'promocode')
    list_filter = ('reward_type', 'is_active')
    search_fields = ('name', 'description')
    fieldsets = (
        ('General Information', {
            'fields': ('name', 'reward_type', 'points_required', 'description', 'is_active'),
        }),
        ('Promocode Details', {
            'fields': ('promocode',),
            'classes': ('collapse',),
        }),
    )
    jazzmin_settings = {
        "changeform_format": "horizontal_tabs",
    }
    def get_inline_instances(self, request, obj=None):
        if obj and obj.reward_type == "promocode":
            return [inline(self.model, self.admin_site) for inline in self.inlines]
        return []
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.reward_type != "promocode":
            fieldsets = [fieldset for fieldset in fieldsets if fieldset[0] != 'Promocode Details']
        return fieldsets
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "promocode":
            kwargs["queryset"] = Promocode.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(RewardHistory)
class RewardHistoryAdmin(BaseAdmin):
    list_display = ('user', 'reward', 'redeemed_at', 'points_used', 'is_successful', 'is_used')
    list_filter = ('is_successful', 'reward')
    search_fields = ('user__full_name', 'reward__name')

@admin.register(PromocodeHistory)
class PromocodeHistoryAdmin(BaseAdmin):
    list_display = ('user', 'promocode', 'redeemed_at', 'points_used', 'is_successful')
    list_filter = ('is_successful', 'promocode')
    search_fields = ('user__full_name', 'promocode__code')

@admin.register(AppliedPromocode)
class AppliedPromocodeAdmin(BaseAdmin):
    list_display = ('cart', 'promocode', 'applied_at')
    list_filter = ('promocode',)
    search_fields = ('cart__id', 'promocode__code')
    readonly_fields = ('applied_at',)
    autocomplete_fields = ['cart', 'promocode']
    ordering = ('-applied_at',)
    jazzmin_settings = {
        "list_per_page": 20,
        "list_filter_sticky": True,
    }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'cols': 50}),
            'answer': forms.Textarea(attrs={'rows': 3, 'cols': 50}),
        }

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    list_display = ('category_colored', 'user_link', 'status_badge', 'claimed_by_link', 'created_at', 'response_time')
    list_filter = ('status', 'category', 'claimed_by', 'created_at')
    search_fields = ('user__full_name', 'text', 'answer', 'id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'response_time_display', 'photo_display')
    fieldsets = (
        ('Asosiy ma’lumotlar', {
            'fields': ('user', 'category', 'text', 'created_at'),
            'description': 'Foydalanuvchi savolining asosiy detallari.',
        }),
        ('Javob va holat', {
            'fields': ('status', 'claimed_by', 'answer', 'updated_at', 'response_time_display', 'photo'),
            'description': 'Savolga javob berish va holatni boshqarish.',
        }),
    )
    autocomplete_fields = ['user', 'claimed_by']  # 'deferred_by' olib tashlandi
    list_per_page = 15
    actions = ['mark_as_answered', 'send_to_admins']

    # Maxsus ko‘rinishlar
    def user_link(self, obj):
        return format_html(
            obj.user.full_name
        )
    user_link.short_description = "Foydalanuvchi"

    def category_colored(self, obj):
        colors = {
            'technical': '#ff9800',
            'orders': '#4caf50',
            'general': '#2196f3',
        }
        color = colors.get(obj.category, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            color, obj.get_category_display()
        )
    category_colored.short_description = "Kategoriya"

    def status_badge(self, obj):
        badges = {
            'pending': ('#ff5722', 'Kutilmoqda'),
            'claimed': ('#ffeb3b', 'Qabul qilingan', '#000'),
            'answered': ('#4caf50', 'Javob berilgan'),
        }
        bg_color, text, *fg_color = badges.get(obj.status, ('#757575', 'Noma’lum'))
        fg_color = fg_color[0] if fg_color else '#fff'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            bg_color, fg_color, text
        )
    status_badge.short_description = "Holat"

    def claimed_by_link(self, obj):
        if obj.claimed_by:
            return format_html(
                '<a href="/admin/telegram_app/user/{}/change/" style="color: #d81b60;">{}</a>',
                obj.claimed_by.id, obj.claimed_by.full_name
            )
        return '-'
    claimed_by_link.short_description = "Qabul qilgan"

    def response_time(self, obj):
        if obj.status == 'answered' and obj.updated_at and obj.created_at:
            delta = obj.updated_at - obj.created_at
            minutes = delta.total_seconds() // 60
            return f"{int(minutes)} daqiqa"
        return '-'
    response_time.short_description = "Javob vaqti"

    def response_time_display(self, obj):
        return self.response_time(obj)
    response_time_display.short_description = "Javob berish vaqti"

    def photo_display(self, obj):
        if obj.photo:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 100px; border-radius: 8px;" alt="Savol rasmi"/></a>',
                obj.photo.url, obj.photo.url
            )
        return "Rasm yuklanmagan"
    photo_display.short_description = "Rasm"

    # Maxsus harakatlar
    def mark_as_answered(self, request, queryset):
        with transaction.atomic():
            updated = queryset.update(status='answered')
        self.message_user(request, f"{updated} ta savol 'Javob berilgan' deb belgilandi.")
    mark_as_answered.short_description = "Tanlanganlarni javob berilgan deb belgilash"

    def send_to_admins(self, request, queryset):
        for question in queryset:
            if question.status == 'pending':  # 'deferred' olib tashlandi
                admins = User.objects.filter(role__in=["Admin", "Superadmin"])
                for admin in admins:
                    pass  # Telegram bot integratsiyasi qo‘shilishi mumkin
        self.message_user(request, f"{queryset.count()} ta savol adminlarga qayta yuborildi.")
    send_to_admins.short_description = "Savollarni adminlarga qayta yuborish"

    jazzmin_settings = {
        "list_filter_sticky": True,
        "list_per_page": 15,
        "changeform_format": "horizontal_tabs",
        "related_modal_active": True,
        "show_ui_builder": True,
        "icons": {
            "telegram_app.Question": "fa fa-question-circle",
        },
    }

























