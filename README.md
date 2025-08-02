# JWT Auth API (Django)

Простое API для аутентификации с JWT-токенами. Поддержка мобильных и веб-клиентов.

## 🔧 Технологии
- Django + DRF
- JWT (access/refresh токены)
- Redis (кеш, Celery broker)
- Celery (отправка email)

## 🚀 Как запустить
1. Установите зависимости: `pip install -r requirements.txt`
2. Запустите Redis: `redis-server`
3. Запустите Celery: `celery -A master worker -l info`
4. Запустите сервер: `python manage.py runserver`

## 📌 Основные endpoints
- `POST /api/registration/` - Начало регистрации (email + username)
- `POST /api/registration/verification/` - Проверка кода из email
- `POST /api/registration/password-set/` - Установка пароля
- `POST /api/login/` - Логин (username + password)
- `POST /api/login/verification/` - Проверка кода для входа
- `POST /api/logout/` - Выход

## 🔐 Особенности
- **Для мобильных приложений**: токены возвращаются в JSON
- **Для веба**: токены в HttpOnly куках
- Автообновление токенов через `/api/token/refresh/`
- Документация: `/api/schema/swagger-ui/`

## ⚙️ Настройки
- В настройках укажите свои данные от БД и MAIL
