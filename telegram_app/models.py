from django.db import models
from django.utils import timezone
import uuid


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

    def __str__(self):
        return f"{self.full_name}"


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CarBrand(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    brand = models.ForeignKey(
        CarBrand, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('brand', 'name')

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_products", editable=False
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_products"
    )
    QUALITY_CHOICES = [
        ("new", "New"),
        ("renewed", "Renewed"),
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("acceptable", "Acceptable"),
    ]
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products")
    car_brand = models.ForeignKey(
        CarBrand, on_delete=models.CASCADE, related_name="products")
    car_model = models.ForeignKey(
        CarModel, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=False)
    photo = models.ImageField(
        upload_to="product_photos/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    quality = models.CharField(
        max_length=10, choices=QUALITY_CHOICES, default="new"
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
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
        """Asl narx va chegirma qilingan narxni tuple sifatida qaytaradi."""
        active_discount = self.discounts.filter(
            is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()
        ).first()

        if active_discount:
            discounted_price = round(
                self.price * (1 - active_discount.percentage / 100), 2)
            return {"original_price": self.price, "discounted_price": discounted_price}

        return {"original_price": self.price, "discounted_price": None}

    @property
    def available_stock(self):
        return self.stock - self.reserved_stock

    def __str__(self):
        return f"{self.name}"


class Cart(models.Model):
    """Model representing a shopping cart."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    # session_id = models.CharField(max_length=255, null=True, blank=True)  # For guest carts
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def total_price(self):
        """Calculate the total price of the cart after all discounts."""
        total = sum(item.subtotal() for item in self.items.all())

        applied_promocode = self.applied_promocodes.first()
        if applied_promocode and applied_promocode.promocode.is_valid():
            total = total * \
                (1 - applied_promocode.promocode.discount_percentage / 100)
        return round(total, 2)

    def __str__(self):
        return f"Cart {self.id} ({'Active' if self.is_active else 'Inactive'})"


class CartItem(models.Model):
    """Model representing an item in the cart."""
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def get_quantity(self):
        return self.quantity

    def get_product(self):
        return self.product

    def subtotal(self):
        """Calculate subtotal price for this cart item after applying discount."""
        return self.product.discounted_price * self.quantity

    def __str__(self):
        return f"{self.product.name} (x{self.quantity}) in Cart {self.cart.id}"


class SavedItemList(models.Model):
    """Model for a list of saved items for later purchase."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='saved_item_lists')
    name = models.CharField(max_length=255, default="Wishlist")
    created_at = models.DateTimeField(auto_now_add=True)

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
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ('saved_item_list', 'product')

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
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='order')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    promocode = models.ForeignKey(
        'Promocode', on_delete=models.SET_NULL, null=True, blank=True)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Pending')

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Online', 'Online'),
    ]
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, default='Cash')

    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')

    order_id = models.CharField(
        max_length=20, unique=True, blank=True, null=True)

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
        return f"Order {self.id} ({self.status})"


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

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

    def __str__(self):
        return self.name


class Promocode(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_promocodes", default=1
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="updated_promocodes", default=1
    )
    reward = models.OneToOneField(
        Reward, on_delete=models.CASCADE, related_name="promocode", null=True, blank=True
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
            return self.code
        return None

    def __str__(self):
        return self.code


class AppliedPromocode(models.Model):
    """Model for tracking applied promocodes to a cart."""
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='applied_promocodes')
    promocode = models.ForeignKey(
        Promocode, on_delete=models.CASCADE, related_name='applied_carts')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promocode {self.promocode.code} applied to Cart {self.cart.id}"
