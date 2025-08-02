from rest_framework.permissions import BasePermission
from account.models import User

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Проверяем, что пользователь - владелец профиля
        return obj.id == request.user.id
