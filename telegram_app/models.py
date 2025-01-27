from django.db import models


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
        return f"{self.full_name} {self.role}"


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
    available = models.BooleanField(default=True)
    photo = models.ImageField(
        upload_to="product_photos/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"
