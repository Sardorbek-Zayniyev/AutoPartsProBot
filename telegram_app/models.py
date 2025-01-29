from django.db import models
from decimal import Decimal


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
    role = models.CharField(
        max_length=50,
        choices=UserRole,
        default=USER,
    )

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
        # Ensures unique model names per brand
        unique_together = ('brand', 'name')

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products")
    car_brand = models.ForeignKey(
        CarBrand, on_delete=models.CASCADE, related_name="products")
    car_model = models.ForeignKey(
        CarModel, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    photo = models.ImageField(
        upload_to="product_photos/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

class Cart(models.Model):
    """Model representing a shopping cart."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    # session_id = models.CharField(max_length=255, null=True, blank=True)  # For guest carts
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  

    def total_price(self):
        """Calculate the total price of the cart (after discounts)."""
        total = sum(item.subtotal() for item in self.items.all())
        return total

    def __str__(self):
        return f"Cart {self.id} ({'Active' if self.is_active else 'Inactive'})"


class CartItem(models.Model):
    """Model representing an item in the cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  #
    
    def get_quantity(self):
        return self.quantity
    
    def get_product(self):
        return self.product

    def subtotal(self):
        """Calculate the subtotal price for this cart item."""
        discounted_price = self.product.price * (1 - self.discount / Decimal(100))
        return discounted_price * self.quantity

    def __str__(self):
        return f"{self.product.name} (x{self.quantity}) in Cart {self.cart.id}"


class Wishlist(models.Model):
    """Model representing a user's wishlist."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, related_name='wishlisted_by', blank=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"


class SavedItem(models.Model):
    """Model for saved items for later purchase."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='saved_by')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} saved by {self.user.username}"


class DiscountCode(models.Model):
    """Model representing discount codes."""
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)  
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class AppliedDiscount(models.Model):
    """Model for tracking applied discounts to a cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='applied_discounts')
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.CASCADE, related_name='applied_carts')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discount {self.discount_code.code} applied to Cart {self.cart.id}"


class Order(models.Model):
    """Model representing a completed order."""
    cart = models.OneToOneField(Cart, on_delete=models.PROTECT, related_name='order')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Paid', 'Paid'),
            ('Shipped', 'Shipped'),
            ('Delivered', 'Delivered'),
            ('Cancelled', 'Cancelled'),
        ],
        default='Pending'
    )

    def __str__(self):
        return f"Order {self.id} ({self.status})"
