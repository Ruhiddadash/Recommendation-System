from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()   # email or username
    password = serializers.CharField()

    def validate(self, attrs):
        login = attrs.get("login")
        password = attrs.get("password")

        # Login as email?
        if "@" in login:
            try:
                user = User.objects.get(email=login)
            except User.DoesNotExist:
                raise AuthenticationFailed("Invalid credentials")
        else:
            # Login as username
            try:
                user = User.objects.get(username=login)
            except User.DoesNotExist:
                raise AuthenticationFailed("Invalid credentials")

        user = authenticate(username=user.username, password=password)

        if not user:
            raise AuthenticationFailed("Invalid credentials")

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
