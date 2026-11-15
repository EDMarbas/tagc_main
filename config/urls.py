from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from main.views import register

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/register/", register, name="register"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("members/", include("members.urls")),
    path("", include("main.urls")),
]
