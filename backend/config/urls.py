from django.contrib import admin
from django.urls import path, include
from accounts.views import (
    LoginView, RegisterView,
    LoginPageView, RegisterPageView
)
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', TemplateView.as_view(template_name='index.html'), name='home_page'),

    path('', include('accounts.urls')),  # login-page burada
    
    # Dashboard – HTML page
    path('dashboard/', TemplateView.as_view(template_name="dashboard.html"), name="dashboard_page"),
    path('api/accounts/', include('accounts.urls')),
    path('api/movies/', include('movies.urls')),
]
