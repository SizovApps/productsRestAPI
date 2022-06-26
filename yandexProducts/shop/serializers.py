from rest_framework import serializers

from .models import ShopUnit, ShopUnitHistory


class ListShopUnitModel:
    """Модель запроса на добавление списка товаров и категорий с учетом времени."""

    def __init__(self, items, updateDate):
        self.items = items
        self.updateDate = updateDate


class ShopUnitImport:
    """Модель данных для добавление списка товаров и категорий."""

    def __init__(self, id, name, parent_id, type, price):
        self.id = id
        self.name = name
        self.parentId = parent_id
        self.type = type
        self.price = price


class ShopUnitType:
    """Модель данных для типа продукта."""
    def __init__(self, type):
        self.type = type


class ShopUnitStatisticResponse:
    def __init__(self, items):
        self.items = items


class ShopUnitStatisticUnit:
    """Модель данных для создания статистики товаров и категорий."""

    def __init__(self, id, name, parent_id, type, price, date):
        self.id = id
        self.name = name
        self.parentId = parent_id
        self.type = type
        self.price = price
        self.date = date


class ShopUnitStatisticSerializer(serializers.Serializer):
    """Сериализатор данных для создания статистики товаров и категорий."""
    id = serializers.CharField()
    name = serializers.CharField()
    parentId = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    price = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.CharField()


class ShopUnitImportSerializer(serializers.Serializer):
    """Сериализатор данных для добавления списка товаров и категорий."""
    id = serializers.CharField()
    name = serializers.CharField()
    parentId = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    price = serializers.IntegerField(required=False)

    def create(self, validated_data):
        print(validated_data)
        return ShopUnitImport(**validated_data)


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.__class__(
            value,
            context=self.context)
        return serializer.data


class ShopUnitSerializer(serializers.ModelSerializer):
    """Сериализатор модели данных товара."""
    parentId = serializers.PrimaryKeyRelatedField(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = ShopUnit
        depth = 10
        fields = '__all__'

    """Получаем дочерние объекты."""
    def get_children(self, obj: ShopUnit):
        obj_children = obj.children

        if obj_children.all():
            return ShopUnitSerializer(obj_children, many=True).data

        if obj.type == ShopUnit.Type.OFFER:
            return None
        return []


class ShopUnitHistorySerializer(serializers.ModelSerializer):
    """Сериализатор модели данных истории товара."""
    id = serializers.CharField(required=False)

    class Meta:
        model = ShopUnitHistory
        fields = '__all__'


class ShopUnitImportRequestSerializer(serializers.Serializer):
    """Сериализатор для запроса изменения списка товаров."""
    items = ShopUnitImportSerializer(many=True)
    updateDate = serializers.CharField(max_length=100)

    def create(self, validated_data):
        items_data = validated_data.get('items')

        for item in items_data:
            item['date'] = validated_data.get('updateDate')

            if item.get('parentId'):
                item['parentId'] = ShopUnit.objects.get(pk=item.get('parentId'))

            """Обновляем товар или категорию или создаем новую."""
            if ShopUnit.objects.filter(pk=item.get('id')).exists():
                """Создаем записи об изменении товара или категории."""
                old = ShopUnit.objects.get(pk=item.get('id'))
                old_data = ShopUnitSerializer(old).data
                old_data["oldId"] = old_data["id"]
                old_data.pop("id")
                old_data.pop("children")

                history_serializer = ShopUnitHistorySerializer(data=old_data)
                history_serializer.is_valid(raise_exception=True)
                history_serializer.save()

                ShopUnitHistory.objects.create(**old_data)
                old.delete()

                ShopUnit.objects.create(**item)
            else:
                ShopUnit.objects.create(**item)

        return ListShopUnitModel(**validated_data)


