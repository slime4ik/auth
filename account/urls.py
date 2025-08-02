from django.urls import path
from rest_framework.routers import DefaultRouter
from account.views import RegistrationEmailAPIView, RegistrationCodeAPIView,\
RegistrationPasswordAPIView, LoginAPIView, LoginCodeAPIView, LogoutAPIView,\
CheckAuthAPIView, UserViewSet

urlpatterns = [
    # Регистрация
    path('registration/', RegistrationEmailAPIView.as_view(), name='registration_1_step'),
    path('registration/verification/', RegistrationCodeAPIView.as_view(), name='registration_2_step'),
    path('registration/password-set/', RegistrationPasswordAPIView.as_view(), name='registration_3_step'),
    # Вход
    path('login/', LoginAPIView.as_view(), name='login_1_step'),
    path('login/verification/', LoginCodeAPIView.as_view(), name='login_2_step'),
    # Выход
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    # Проверка авторизации по JWT
    path('is_authentificated/', CheckAuthAPIView.as_view(), name='check_auth')
]

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
urlpatterns += router.urls