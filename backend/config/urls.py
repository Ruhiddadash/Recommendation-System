from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from accounts.views import (
    LoginView, RegisterView,
    LoginPageView, RegisterPageView, LogoutView
)

from movies.views import dashboard_view  # NEW

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home Page
    path('', TemplateView.as_view(template_name='index.html'), name='home_page'),

    # Accounts (HTML Pages + Authentication API)
    path('api/accounts/', include('accounts.urls')),

    # Dashboard (Protected)
    path('dashboard/', dashboard_view, name="dashboard_page"),

    # Movie API
    path('api/movies/', include('movies.urls')),
]
