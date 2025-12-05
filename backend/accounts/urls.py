# accounts/urls.py
from django.urls import path
from .views import (
    LoginView, RegisterView, LogoutView,
    LoginPageView, RegisterPageView, WhoAmIView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='api_login'),
    path('register/', RegisterView.as_view(), name='api_register'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # HTML Pages
    path('login-page/', LoginPageView.as_view(), name='login_page'),
    path('register-page/', RegisterPageView.as_view(), name='register_page'),

    # Who am I API
    path('whoami/', WhoAmIView.as_view(), name='who_am_i'),
]
