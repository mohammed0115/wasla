
from ..models import Inventory

class InventoryService:
    @staticmethod
    def set_inventory(product, quantity):
        inventory, _ = Inventory.objects.get_or_create(product=product)
        inventory.quantity = quantity
        inventory.in_stock = quantity > 0
        inventory.save()
