from __future__ import annotations

from typing import Iterable

from django.db import IntegrityError, transaction

from apps.subscriptions.services.entitlement_service import SubscriptionEntitlementService

from ..models import Category, Inventory, Product


class ProductService:
    @staticmethod
    def _validate_price(price) -> None:
        if price is None or price <= 0:
            raise ValueError("Price must be positive")

    @staticmethod
    def _validate_categories(store_id: int, categories: Iterable[Category] | None) -> list[int]:
        if not categories:
            return []
        category_ids = [c.id for c in categories]
        invalid_exists = Category.objects.filter(id__in=category_ids).exclude(store_id=store_id).exists()
        if invalid_exists:
            raise ValueError("All categories must belong to the same store")
        return category_ids

    @staticmethod
    @transaction.atomic
    def create_product(
        *,
        store_id: int,
        sku: str,
        name: str,
        price,
        categories: Iterable[Category] | None = None,
        quantity: int = 0,
        image_file=None,
    ):
        ProductService._validate_price(price)
        if not sku:
            raise ValueError("SKU is required")

        current_products = Product.objects.filter(store_id=store_id).count()
        SubscriptionEntitlementService.assert_within_limit(
            store_id=store_id,
            limit_field="max_products",
            current_usage=current_products,
            increment=1,
        )

        category_ids = ProductService._validate_categories(store_id, categories)

        try:
            product = Product.objects.create(
                store_id=store_id,
                sku=sku,
                name=name,
                price=price,
                image=image_file if image_file else None,
                is_active=quantity > 0,
            )
        except IntegrityError as exc:
            raise ValueError("SKU already exists for this store") from exc

        if category_ids:
            product.categories.set(category_ids)
        else:
            product.categories.clear()

        Inventory.objects.update_or_create(
            product=product,
            defaults={"quantity": quantity, "in_stock": quantity > 0},
        )

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        *,
        store_id: int,
        product: Product,
        sku: str,
        name: str,
        price,
        categories: Iterable[Category] | None = None,
        quantity: int = 0,
        image_file=None,
    ):
        if product.store_id != store_id:
            raise ValueError("Product does not belong to this store")

        ProductService._validate_price(price)
        if not sku:
            raise ValueError("SKU is required")

        category_ids = ProductService._validate_categories(store_id, categories)

        image_changed = False
        if image_file is False:
            if product.image:
                product.image.delete(save=False)
            product.image = None
            image_changed = True
        elif image_file:
            product.image = image_file
            image_changed = True

        product.sku = sku
        product.name = name
        product.price = price
        product.is_active = quantity > 0
        try:
            update_fields = ["sku", "name", "price", "is_active"]
            if image_changed:
                update_fields.append("image")
            product.save(update_fields=update_fields)
        except IntegrityError as exc:
            raise ValueError("SKU already exists for this store") from exc

        if category_ids:
            product.categories.set(category_ids)
        else:
            product.categories.clear()

        Inventory.objects.update_or_create(
            product=product,
            defaults={"quantity": quantity, "in_stock": quantity > 0},
        )

        return product
