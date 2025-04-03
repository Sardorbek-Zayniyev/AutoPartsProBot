from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Cart, CartItem

@receiver(post_save, sender=Cart)
def cart_post_save(sender, instance, created, **kwargs):
    if created:
        instance.reserved_until = None
        instance.warning_sent = False
        instance.save(update_fields=['reserved_until', 'warning_sent'])

@receiver(pre_delete, sender=CartItem)
def restore_reserved_stock(sender, instance, **kwargs):
    product = instance.product
    product.reserved_stock -= instance.quantity
    product.reserved_stock = max(product.reserved_stock, 0)
    product.available = product.available_stock > 0
    product.save()