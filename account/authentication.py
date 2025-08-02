from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')
        if access_token is None:
            return None
        try:
            validation_token = self.get_validated_token(access_token)
            return self.get_user(validation_token), validation_token
        except Exception:
            return None