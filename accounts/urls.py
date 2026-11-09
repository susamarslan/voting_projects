from django.urls import path

from . import views

urlpatterns = [
    path("kayit/", views.register, name="register"),
    path("giris/", views.LoginView.as_view(), name="login"),
    path("cikis/", views.LogoutView.as_view(), name="logout"),
]
