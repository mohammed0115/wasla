"""
Payments models (MVP).

AR: يمثل عمليات الدفع المرتبطة بالطلبات (نجاح/فشل/قيد الانتظار).
EN: Represents payment attempts linked to orders (success/failed/pending).
"""

from django.db import models


class Payment(models.Model):
    """Payment record linked to an order."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="payments"
    )
    method = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.order} - {self.status}"
