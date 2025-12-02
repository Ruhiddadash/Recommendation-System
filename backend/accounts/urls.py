from django.urls import path
from .views import RegisterView, LoginView, WhoAmIView, LoginPageView, RegisterPageView, LogoutView

urlpatterns = [
    # API endpoints
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('whoami/', WhoAmIView.as_view()),

    # HTML pages
    path('login-page/', LoginPageView.as_view(), name="login_page"),
    path('register-page/', RegisterPageView.as_view(), name='register_page'),
    path("api/accounts/logout/", LogoutView.as_view(), name="logout"),

]
