
from django.db import models

class Plugin(models.Model):
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=20)
    provider = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

class InstalledPlugin(models.Model):
    STATUS_CHOICES = [
        ("installed", "Installed"),
        ("active", "Active"),
        ("disabled", "Disabled"),
        ("uninstalled", "Uninstalled"),
    ]
    plugin = models.ForeignKey(Plugin, on_delete=models.PROTECT)
    store_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    installed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.plugin} (store {self.store_id})"

    class Meta:
        unique_together = ("plugin", "store_id")
