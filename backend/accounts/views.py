from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


from .serializers import RegisterSerializer, LoginSerializer


from django.contrib.auth import logout

from django.contrib.auth import logout
from django.shortcuts import redirect

class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        logout(request)
        return redirect('/api/accounts/login-page/')


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            }, status=201)

        return Response({"success": False, "errors": serializer.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"success": False, "message": "Invalid credentials"}, status=400)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


@method_decorator(csrf_exempt, name='dispatch')
class WhoAmIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "username": user.username,
                "email": user.email
            },
            status=status.HTTP_200_OK
        )
    
from django.shortcuts import render, redirect
from django.views import View

class LoginPageView(View):
    def get(self, request):
        return render(request, "login.html")


class RegisterPageView(View):
    def get(self, request):
        return render(request, "register.html")
    
    
