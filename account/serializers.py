from rest_framework import serializers
from account.models import User


class PasswordSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        if ' ' in data['password']:
            raise serializers.ValidationError("Пароль не может содержать пробелы")
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data

class EmailCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, write_only=True)

    def validate(self, data):
        if len(str(data['code'])) != 6:
            raise serializers.ValidationError("Неверная длина кода")
        return data

class UsernameEmailSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    
    def validate(self, data):
        # Проверка на существования аккаунта с таким email и username
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Эта почта уже используется")
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Этот ник уже используется")
        
        # Проверка на длину ника
        if len(data['username']) < 3:
            raise serializers.ValidationError("Слишком короткое имя")
        if len(data['username']) > 30:
            raise serializers.ValidationError("Слишком длинное имя")
        
        return data
    
class UsernamePasswordSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'username',
            'bio',
        )