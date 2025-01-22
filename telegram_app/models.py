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
