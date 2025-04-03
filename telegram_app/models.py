from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid
from django.db.models import Sum

class User(models.Model):
    USER = "User"
    ADMIN = "Admin"
    SUPERADMIN = "Superadmin"

    UserRole = [
        (USER, "User"),
        (ADMIN, "Admin"),
        (SUPERADMIN, "Superadmin"),
    ]

    telegram_id = models.BigIntegerField(unique=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    extra_phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=50,
        choices=UserRole,
        default=USER,
    )
    region = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)

    points = models.PositiveIntegerField(default=0)
    last_pending_message_id = models.IntegerField(null=True, blank=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True) 

    def delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
    def __str__(self):
        return f"{self.full_name}"


class Category(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_categories"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_categories"
    )
    parent_category = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name="sub_categories",
        null=True, blank=True
    )
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent_category.name} → {self.name}" if self.parent_category else self.name


class CarBrand(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_car_brand"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_car_brand"
    )
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_car_model"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_car_model"
    )
    brand = models.ForeignKey(
        CarBrand, on_delete=models.CASCADE, related_name="car_models")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('brand', 'name')
        

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_products",
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_products", 
    )
    QUALITY_CHOICES = [
        ("new", "New"),
        ("renewed", "Renewed"),
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("acceptable", "Acceptable"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Ko'rib chiqilmoqda"),
        (STATUS_APPROVED, "Joylashtirildi"),
        (STATUS_REJECTED, "Rad etilgan"),
    ]
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products")
    car_brand = models.ForeignKey(
        CarBrand, on_delete=models.CASCADE, related_name="products")
    car_model = models.ForeignKey(
        CarModel, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255, default='This is product name')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="product_photos/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=15)
    reserved_stock = models.PositiveIntegerField(default=0)
    quality = models.CharField(
        max_length=10, choices=QUALITY_CHOICES, default="new"
    )
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_APPROVED
    )
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.is_active:
            self.status = Product.STATUS_APPROVED
        else:
            if self.status != Product.STATUS_REJECTED: 
                self.status = Product.STATUS_PENDING
        if self.name:
            self.name = self.name.title()

        if not self.available:
            self.stock = 0
        elif self.available and self.stock == 0:
            self.stock = 1

        if self.stock == 0:
            self.available = False
        elif self.stock > 0:
            self.available = True

        # if self.pk:  # If the instance already exists in DB
        #     existing = self.__class__.objects.get(pk=self.pk)
        #     if self.stock != existing.stock:
        #     # Stock was manually updated, determine availability
        #         self.available = self.stock > 0
        # else:
        # # If creating a new object, set stock based on availability
        #     if self.available:
        #         self.stock = 1
        #     else:
        #         self.stock = 0

        super().save(*args, **kwargs)
        if not self.available:
            for discount in self.discounts.all():
                discount.products.remove(self)

    @property
    def discounted_price(self):
        active_discount = self.discounts.filter(
            is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()
        if active_discount:
            return round(self.price * (1 - active_discount.percentage / 100), 2)
        return self.price

    def original_and_discounted_price(self):
        active_discount = self.discounts.filter(
            is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()
        ).first()
    
        if active_discount:
            percentage = Decimal(str(active_discount.percentage))
            discounted_price = round(
                self.price * (1 - percentage / Decimal('100')), 2
            )
            return {"original_price": self.price, "discounted_price": discounted_price}
    
        return {"original_price": self.price, "discounted_price": None}

    @property
    def available_stock(self):
        return self.stock - self.reserved_stock

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Model representing a shopping cart."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    # session_id = models.CharField(max_length=255, null=True, blank=True)  # For guest carts
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)   
    reserved_until = models.DateTimeField(null=True, blank=True)
    warning_sent = models.BooleanField(default=False)
    promocodes = models.ManyToManyField('Promocode', blank=True, related_name='used_in_carts')
    rewards = models.ManyToManyField('Reward', blank=True, related_name='applied_carts')
    last_message_id = models.IntegerField(null=True, blank=True)
    
    def total_price(self):
        total = self.items.aggregate(total=Sum(models.F('product__price') * models.F('quantity')))['total']
        return total or Decimal(0)

    def discounted_price(self):
        total = self.total_price()
        total_discount_percentage = sum(promo.discount_percentage for promo in self.promocodes.all())

        if total_discount_percentage > 0:
            discounted_total = total * (1 - Decimal(total_discount_percentage) / 100)
            return round(discounted_total, 2)

        return None
    
    def __str__(self):
        return f"Cart {self.id} ({'Active' if self.is_active else 'Inactive'})" 
    

class CartItem(models.Model):
    """Model representing an item in the cart."""
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def get_quantity(self):
        return self.quantity

    def get_product(self):
        return self.product

    def subtotal(self):
        """Calculate subtotal price for this cart item after applying discount."""
        return self.product.discounted_price * self.quantity

    def __str__(self):
        return f"{self.product} (x{self.quantity}) in Cart {self.cart.id}"


class SavedItemList(models.Model):
    """Model for a list of saved items for later purchase."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='saved_item_lists')
    name = models.CharField(max_length=255, default="Wishlist")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'name')


class SavedItem(models.Model):
    """Model for individual saved items in a saved item list."""
    saved_item_list = models.ForeignKey(
        SavedItemList, on_delete=models.CASCADE, related_name='saved_items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
        unique_together = ('saved_item_list', 'product')

    def get_product(self):
        return self.product
    
    def __str__(self):
        return f"{self.product.name}"


class Discount(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_discounts", editable=False, default=1
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_discounts",
    )
    name = models.CharField(max_length=255, null=True)
    products = models.ManyToManyField(
        Product, related_name='discounts', blank=True)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Discount percentage (e.g. 10 for 10%)")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_valid(self):

        return self.is_active and self.start_date <= timezone.now() <= self.end_date

    def save(self, *args, **kwargs):
        if not self.pk:
            if "user" in kwargs:
                self.owner = kwargs.pop("user")
            if not self.name:
                self.name = f"{self.start_date.strftime('%Y-%m-%d')} —> {self.end_date.strftime('%Y-%m-%d')}"
        super().save(*args, **kwargs)

        if self.end_date < timezone.now():
            self.is_active = False

    @property
    def start_date_normalize(self):
        return self.start_date.strftime('%Y-%m-%d %H:%M')

    @property
    def end_date_normalize(self):
        return self.end_date.strftime('%Y-%m-%d %H:%M')

    def __str__(self):
        return f"{self.name}"


class Order(models.Model):
    """Model representing a completed order."""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Payme', 'Payme'),
        ('Click', 'Click'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]

    order_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cart = models.ForeignKey(Cart, on_delete=models.PROTECT, related_name='order')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')

    region = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.order_id:
            self.order_id = self.created_at.strftime('%Y%m%d%H%M%S')

        super().save(update_fields=['order_id'])

        applied_promocode = self.cart.applied_promocodes.first()
        if applied_promocode and applied_promocode.promocode.is_valid():
            self.promocode = applied_promocode.promocode
            self.total_price = self.cart.total_price()

        
            
    def __str__(self):
        return f"#{self.order_id}_{self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def subtotal(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.discounted_price
        super().save(*args, **kwargs)


class Reward(models.Model):
    REWARD_TYPES = (
        ("free_shipping", "Free Shipping"),
        ("gift", "Gift"),
        ("promocode", "Promocode"),
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_rewards", default=1
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_rewards",
    )
    reward_type = models.CharField(
        max_length=20, choices=REWARD_TYPES, default='gift')
    name = models.CharField(max_length=255)
    points_required = models.PositiveIntegerField()
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    promocode = models.OneToOneField(
        'Promocode', on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'is_active': True},  # Only active promocodes can be selected
        related_name='reward'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

   
    def redeem(self, user):
        """Foydalanuvchi ball evaziga sovg'a olishi"""
        if user.points >= self.points_required:
            user.points -= self.points_required
            user.save()

            RewardHistory.objects.create(
                user=user,
                reward=self,
                points_used=self.points_required,
                is_successful=True
            )
            return self.name 
        else:
            RewardHistory.objects.create(
                user=user,
                reward=self,
                points_used=self.points_required,
                is_successful=False
            )
            return None
    
    def save(self, *args, **kwargs):
        # Ensure promocode is only linked if reward_type is "promocode"
        if self.reward_type != "promocode":
            self.promocode = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — {self.points_required} ball"


class Promocode(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_promocodes", default=1
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_promocodes", default=1
    )
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    required_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def is_valid(self):
        return (
            self.is_active
            and self.valid_from <= timezone.now() <= self.valid_until
            and self.used_count < self.usage_limit
        )

    def redeem(self, user):
        """Foydalanuvchi ball evaziga promokodni olishi"""
        if user.points >= self.required_points:
            user.points -= self.required_points
            user.save()

            PromocodeHistory.objects.create(
                user=user,
                promocode=self,
                points_used=self.required_points,
                is_successful=True
            )
            return self.code
        else:
            PromocodeHistory.objects.create(
                user=user,
                promocode=self,
                points_used=self.required_points,
                is_successful=False
            )
            return None

    def __str__(self):
        return self.code


class RewardHistory(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reward_history')
    reward = models.ForeignKey(
        Reward, on_delete=models.CASCADE, related_name='user_history')
    redeemed_at = models.DateTimeField(auto_now_add=True)
    points_used = models.PositiveIntegerField()
    is_used = models.BooleanField(default=False)
    is_successful = models.BooleanField(default=True)  

    class Meta:
        verbose_name_plural = 'Reward History'
    def __str__(self):
        return f"{self.reward.name} -- {self.redeemed_at}"


class PromocodeHistory(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='promocode_history')
    promocode = models.ForeignKey(
        Promocode, on_delete=models.CASCADE, related_name='user_history')
    redeemed_at = models.DateTimeField(auto_now_add=True)
    points_used = models.PositiveIntegerField()
    is_successful = models.BooleanField(default=True)  
   
    class Meta:
        verbose_name_plural = 'Promocode History'
    def __str__(self):
        return f"{self.user.full_name} redeemed {self.promocode.code} on {self.redeemed_at}"


class AppliedPromocode(models.Model):
    """Model for tracking applied promocodes to a cart."""
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='applied_promocodes')
    promocode = models.ForeignKey(
        Promocode, on_delete=models.CASCADE, related_name='applied_carts')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promocode {self.promocode.code} applied to Cart {self.cart.id}"


class Question(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CLAIMED = "claimed"
    STATUS_ANSWERED = "answered"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Kutilmoqda"),
        (STATUS_CLAIMED, "Ko'rib chiqilmoqda"),
        (STATUS_ANSWERED, "Javob berilgan"),
    ]

    CATEGORY_CHOICES = [
        ("technical", "Texnik yordam"),
        ("orders", "Buyurtmalar"),
        ("general", "Umumiy savollar"),
    ]

    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    claimed_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="claimed_questions",
        limit_choices_to={"role__in": ["Admin", "Superadmin"]}
    )
    answer = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to="question_photos/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Savol #{self.id} - {self.user.full_name} dan"

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.claimed_by and self.status != self.STATUS_CLAIMED:
            self.status = self.STATUS_CLAIMED
        if self.answer and self.status != self.STATUS_ANSWERED:
            self.status = self.STATUS_ANSWERED
        

        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="messages")
    admin = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_messages")
    text = models.TextField()
    is_from_user = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender = "User" if self.is_from_user else "Admin"
        return f"{self.user.full_name} ({sender}): {self.text[:30]}"
