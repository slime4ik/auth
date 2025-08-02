from django.core.cache import cache
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import uuid
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
# Импорты с account
from account.serializers import (
    UsernameEmailSerializer, EmailCodeSerializer,
    PasswordSerializer, UsernamePasswordSerializer,
    UserSerializer,
)
from account.permissions import IsOwner
from account.models import User
from account.utils import set_code_in_redis, check_code_in_redis
from account.tasks import send_code_to_email

# Регистрация — email
class RegistrationEmailAPIView(GenericAPIView):
    serializer_class = UsernameEmailSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            username = serializer.validated_data['username']
            code = set_code_in_redis(email)

            reg_token = str(uuid.uuid4())
            cache.set(f'reg:{reg_token}', {'email': email, 'username': username}, timeout=900)

            send_code_to_email.delay(email, code)
            print(email, code)
            return Response({'message': 'Код отправлен на почту', 'reg_token': reg_token})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Регистрация — код
class RegistrationCodeAPIView(GenericAPIView):
    serializer_class = EmailCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reg_token = request.data.get('reg_token')
            if not reg_token:
                return Response({'message': 'Нужен токен регистрации'}, status=status.HTTP_403_FORBIDDEN)

            reg_data = cache.get(f'reg:{reg_token}')
            if not reg_data:
                return Response({'message': 'Истёк токен регистрации'}, status=status.HTTP_403_FORBIDDEN)

            print(serializer.validated_data['code'])
            if not check_code_in_redis(reg_data['email'], serializer.validated_data['code']):
                return Response({'message': 'Неверный код'}, status=status.HTTP_403_FORBIDDEN)

            cache.set(f'reg:{reg_token}', {**reg_data, 'code_verified': True}, timeout=1800)
            return Response({'message': 'Код принят, придумайте пароль!', 'reg_token': reg_token})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Регистрация — пароль
class RegistrationPasswordAPIView(GenericAPIView):
    serializer_class = PasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reg_token = request.data.get('reg_token')
            reg_data = cache.get(f'reg:{reg_token}')

            if not reg_data or not reg_data.get('code_verified'):
                return Response({'message': 'Регистрация не подтверждена'}, status=status.HTTP_403_FORBIDDEN)

            user = User.objects.create(username=reg_data['username'], email=reg_data['email'])
            user.set_password(serializer.validated_data['password'])
            user.save()
            cache.delete(f'reg:{reg_token}')

            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            # проверяем: мобилка или веб
            client_type = request.headers.get('X-Client-Type', 'web')
            if client_type == 'mobile':
                # для мобильного клиента возвращаем токены в JSON
                return Response({
                    'message': 'Аккаунт создан!',
                    'access_token': str(access),
                    'refresh_token': str(refresh),
                }, status=status.HTTP_201_CREATED)
            else:
                # для браузера ставим куки (HttpOnly!)
                response = Response({'message': 'Аккаунт создан!'}, status=status.HTTP_201_CREATED)
                response.set_cookie(
                    key='refresh_token',
                    value=str(refresh),
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=7 * 24 * 3600,
                    domain="localhost"
                )
                response.set_cookie(
                    key='access_token',
                    value=str(access),
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=60 * 15,
                    domain="localhost"
                )
                return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Вход — логин + пароль
class LoginAPIView(GenericAPIView):
    serializer_class = UsernamePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            if not user:
                return Response({'message': 'Неверный логин или пароль'}, status=status.HTTP_403_FORBIDDEN)

            login_token = str(uuid.uuid4())
            code = set_code_in_redis(user.email)
            cache.set(f'login:{login_token}', user.email, timeout=300)

            send_code_to_email.delay(user.email, code)
            return Response({'message': 'Код отправлен на почту', 'login_token': login_token})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Вход - код
class LoginCodeAPIView(GenericAPIView):
    serializer_class = EmailCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            login_token = request.data.get('login_token')
            email = cache.get(f'login:{login_token}')
            if not login_token or not email:
                return Response({'message': 'Истёк токен или не указан'}, status=status.HTTP_403_FORBIDDEN)

            if not check_code_in_redis(email, serializer.validated_data['code']):
                return Response({'message': 'Неверный код'}, status=status.HTTP_403_FORBIDDEN)

            user = User.objects.get(email=email)
            refresh = RefreshToken.for_user(user)
            cache.delete(f'login:{login_token}')

            # определяем клиент
            client_type = request.headers.get('X-Client-Type', 'web')

            if client_type == 'mobile':
                # мобильный → возвращаем токены в JSON
                return Response({
                    'message': 'Успешный вход!',
                    'user_id': user.id,
                    'username': user.username,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                }, status=status.HTTP_200_OK)
            else:
                # веб
                response = Response({
                    'message': 'Успешный вход!',
                    'user_id': user.id,
                    'username': user.username,
                }, status=status.HTTP_200_OK)

                response.set_cookie(
                    key='refresh_token',
                    value=str(refresh),
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=604800,  # 7 дней
                    domain="localhost"
                )
                response.set_cookie(
                    key='access_token',
                    value=str(refresh.access_token),
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=60 * 15,  # 15 минут
                    domain="localhost"
                )
                return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Logout
class LogoutAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            client_type = request.headers.get('X-Client-Type', 'web')

            # Веб: читаем refresh_token из кук
            if client_type == 'web':
                refresh_token = request.COOKIES.get('refresh_token')
            else:
                # Мобилка: refresh_token придет в теле запроса
                refresh_token = request.data.get('refresh_token')

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception:
                    pass  # уже недействителен

            # Веб → удаляем куки
            if client_type == 'web':
                response = Response({'message': 'Вы вышли из аккаунта'}, status=status.HTTP_202_ACCEPTED)
                response.delete_cookie('access_token')
                response.delete_cookie('refresh_token')
                return response

            # Мобилка → просто ответ
            return Response({'message': 'Вы вышли из аккаунта'}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({'message': 'Ошибка при выходе'}, status=status.HTTP_400_BAD_REQUEST)

# Проверка авторизации
class CheckAuthAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'message': 'Вы авторизованы!',
            'user_id': request.user.id,
            'username': request.user.username
        })

# Кастомная выдача access токена
class CustomTokenRefreshView(TokenRefreshView):
    """
    /token/refresh/
    - web: читает refresh_token из куков и кладет новые токены обратно в куки
    - mobile: читает refresh_token из заголовка (или тела) и возвращает токены в json
    """
    def post(self, request, *args, **kwargs):
        client_type = request.headers.get('X-Client-Type', 'web')

        if client_type == 'web':
            # для браузера refresh берем из куков
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                return Response({'message': 'Нет refresh_token'}, status=401)

            # передаем в сериализатор
            request.data['refresh'] = refresh_token

            response = super().post(request, *args, **kwargs)

            if response.status_code == 200:
                # сетим новые куки
                response.set_cookie(
                    key='access_token',
                    value=response.data['access'],
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=60 * 15,
                    domain="localhost"
                )
                # refresh_token не обновляем (по стандарту SimpleJWT он статичен)
                del response.data['access']  # убираем из тела ответа
            return response

        else:
            # мобилка: refresh_token приходит в заголовке (или теле)
            refresh_token = (
                request.headers.get('X-Refresh-Token') or 
                request.data.get('refresh')
            )
            if not refresh_token:
                return Response({'message': 'Нет refresh_token'}, status=401)

            # подкладываем refresh в data для стандартной логики simplejwt
            request.data['refresh'] = refresh_token

            # вызываем стандартный метод
            response = super().post(request, *args, **kwargs)

            # ⚠️ ничего не ставим в куки — просто отдаем JSON
            return response
class UserViewSet(viewsets.ViewSet):

    def get_permissions(self):
        if self.action == 'update':
            return [IsOwner()]
        return [AllowAny()]

    def retrieve(self, request, pk=None):
        queryset = User.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def update(self, request, pk=None):
        queryset = User.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(request, user)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
