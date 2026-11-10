from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("anket/yeni/", views.poll_create, name="create"),
    path("anket/<int:pk>/", views.poll_detail, name="detail"),
    path("anket/<int:pk>/oy/", views.vote, name="vote"),
    path("anket/<int:pk>/oy/geri-al/", views.vote_withdraw, name="vote_withdraw"),
    path("anket/<int:pk>/kapat/", views.poll_close, name="close"),
    path("anket/<int:pk>/ac/", views.poll_reopen, name="reopen"),
    path("anket/<int:pk>/sil/", views.poll_delete, name="delete"),
    path("anketlerim/", views.my_polls, name="my_polls"),
]
