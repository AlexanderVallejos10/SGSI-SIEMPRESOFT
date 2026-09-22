from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [
    path(
        "usuarios/",
        views.user_list,
        name="user_list",
    ),
]