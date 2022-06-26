from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from _datetime import datetime, timedelta

from .serializers import *


class ShopUnitListView(generics.CreateAPIView, generics.UpdateAPIView):
    """Обработчик ручки imports/."""
    queryset = ShopUnit.objects.all()
    serializer_class = ShopUnitImportRequestSerializer

    """Создаем новый объект."""
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        """Используем сериализатор для преобразования данных в JSON формат."""
        return Response(serializer.data)


class ShopUnitStatisticView(generics.RetrieveAPIView):
    """Обработчик ручки sales/."""
    queryset = ShopUnit.objects.all()
    serializer_class = ShopUnitStatisticSerializer

    """Получаем информацию о последних изменениях и отдаем ее клиенту."""
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk", None)

        if not pk:
            return Response({"code": 400, "message": "Validation Failed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ShopUnit.objects.get(pk=pk)
        except:
            return Response({"code": 404, "message": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            """Получаем дату из запроса."""
            date_in_str_start = request.query_params.get('dateStart')
            date_start = datetime.strptime(date_in_str_start, '%Y-%m-%dT%H:%M:%S.%fZ')
            date_in_str_end = request.query_params.get('dateEnd')
            date_end = datetime.strptime(date_in_str_end, '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            return Response({"code": 400, "message": "Validation Failed"}, status=status.HTTP_400_BAD_REQUEST)

        objects_by_id = ShopUnitHistory.objects.filter(oldId=pk)
        cur_object = ShopUnit.objects.get(pk=pk)

        objects = []
        cur_date = datetime.strptime(cur_object.date, '%Y-%m-%dT%H:%M:%S.%fZ')

        if date_end > cur_date >= date_start:
            objects.append(cur_object)

        """Ищем объекты, обновленные за последние 24 часа."""
        for item in objects_by_id:
            cur_date = datetime.strptime(item.date, '%Y-%m-%dT%H:%M:%S.%fZ')

            if date_end > cur_date >= date_start:
                objects.append(item)

                """Используем сериализатор для преобразования данных в JSON формат."""
        return Response({"items": ShopUnitStatisticSerializer(objects, many=True).data}, status=status.HTTP_200_OK)


class ShopUnitSalesView(generics.RetrieveAPIView):
    """Обработчик ручки sales/."""
    queryset = ShopUnit.objects.all()
    serializer_class = ShopUnitStatisticSerializer

    """Получаем информацию о последних изменениях и отдаем ее клиенту."""
    def get(self, request, *args, **kwargs):
        try:
            """Получаем дату из запроса."""
            date_in_str = request.query_params.get('date')
            date = datetime.strptime(date_in_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            return Response({"code": 400, "message": "Validation Failed"}, status=status.HTTP_400_BAD_REQUEST)

        hour_24 = timedelta(hours=24)
        old_date = date - hour_24
        objects = []

        """Ищем объекты, обновленные за последние 24 часа."""
        for item in ShopUnit.objects.all():
            cur_date = datetime.strptime(item.date, '%Y-%m-%dT%H:%M:%S.%fZ')
            if date >= cur_date >= old_date:
                objects.append(item)

                """Используем сериализатор для преобразования данных в JSON формат."""
        return Response({"items": ShopUnitStatisticSerializer(objects, many=True).data}, status=status.HTTP_200_OK)


class ShopUnitView(generics.RetrieveAPIView):
    """Обработчик ручки nodes/<str:pk:>."""
    serializer_class = ShopUnitSerializer

    """Используем обход в глубину для обновления цены и даты изменения товаров и категорий."""
    def dfs(self, cur_item):
        if cur_item.type == "OFFER":
            """Возвращаем два значения (цену всех товаров в дочерних категориях и их количетсво)."""
            return cur_item.price, 1
        if cur_item.children.all().count() == 0:
            cur_item.price = 0
            cur_item.save()
            return -1, -1

        summ = 0
        counter = 0
        child = []

        new_count = 0
        for item in cur_item.children.all():
            child += [item]
            new_price, new_count =  self.dfs(item)
            summ += new_price
            counter += new_count
        if new_count == 0:
            cur_item.price = None
        else:
            cur_item.price = summ / counter

        """Устанавливаем самую новую дату."""
        for item in child:
            item_date = datetime.strptime(item.date, '%Y-%m-%dT%H:%M:%S.%fZ')
            old_date = datetime.strptime(cur_item.date, '%Y-%m-%dT%H:%M:%S.%fZ')

            if item_date > old_date:
                new_date_str = item_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                new_date_str = new_date_str[:len(new_date_str)-4] + new_date_str[-1]
                cur_item.date = new_date_str

        cur_item.save()
        return summ, counter

    """Получаем информацию о товарах и категориях и передаем ее клиенту."""
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk", None)

        """Проверяем, корректный ли ключ нам пришел."""
        if not pk:
            return Response({"code": 400, "message": "Validation Failed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = ShopUnit.objects.get(pk=pk)
        except:
            return Response({"code": 404, "message": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        """Запускаем обновление информации."""
        self.dfs(instance)
        """Используем сериализатор для преобразования данных в JSON формат."""
        data = ShopUnitSerializer(instance).data
        return Response(data, status=status.HTTP_200_OK)


class DeleteShopUnitView(generics.DestroyAPIView):
    """Обработчик ручки delete/<str:pk>."""
    serializer_class = ShopUnitSerializer

    """Удаляем информацию о товарах или категориях."""
    def delete(self, request, *args, **kwargs):
        pk = kwargs.get("pk", None)

        if not pk:
            return Response({"code": 400, "message": "Validation Failed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = ShopUnit.objects.get(pk=pk)
        except:
            return Response({"code": 404, "message": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        """Удаляем все дочерние элементы."""
        to_del = [instance]

        while to_del:
            cur_del = to_del.pop()
            if cur_del.children.count() > 0:
                for item in cur_del.children.all():
                    to_del += [item]
            cur_del.delete()
        return Response(status=status.HTTP_200_OK)






