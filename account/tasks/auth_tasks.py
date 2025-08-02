from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_code_to_email(email: str, code: int) -> None:
    print(f' КОД ==============================={code}')
    subject = "Обнаружен вход"
    message = (
        f"Ваш код подтверждения: {code}\n\n"
        "Если вы не пытались войти в аккаунт, мы рекомендуем сменить пароль как можно скорее."
    )
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject,
        message,
        from_email,
        [email],
        fail_silently=False,
    )