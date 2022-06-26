
from django.db import models
from django.utils.translation import gettext_lazy as _


class ShopUnit(models.Model):
    """Описание  модели данных для хранения в базе данных."""
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=100)
    date = models.CharField(max_length=100)
    parentId = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)
    price = models.IntegerField(default=0, blank=True)

    class Type(models.TextChoices):
        OFFER = 'OFFER', _('OFFER')
        GRADUATE = 'CATEGORY', _('CATEGORY')
    type = models.CharField(max_length=100, choices=Type.choices)

    def __str__(self):
        return self.name


class ShopUnitHistory(models.Model):
    """Описание модели истории данных для хранения в базе данных."""
    id = models.IntegerField(primary_key=True, editable=False, db_index=True)
    oldId = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    date = models.CharField(max_length=100)
    parentId = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)
    price = models.IntegerField(default=0, blank=True)

    class Type(models.TextChoices):
        OFFER = 'OFFER', _('OFFER')
        GRADUATE = 'CATEGORY', _('CATEGORY')
    type = models.CharField(max_length=100, choices=Type.choices)

    def __str__(self):
        return self.name
