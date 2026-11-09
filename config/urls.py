from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Geçici ana sayfa; Faz 2'de polls.feed ile değiştirilecek.
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
]
