from django.contrib.auth import views as auth_views
from django.urls import path

from . import views, views_access

app_name = "accounts"

urlpatterns = [
    path("usuarios/", views.user_list, name="user_list"),
    # ingreso y salida
    path("ingresar/", views_access.SgsiLoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    # cuenta propia
    path("cuenta/contrasena/", views_access.password_change, name="password_change"),
    path("cuenta/solicitud/", views_access.password_request, name="password_request"),
    path("perfil/", views_access.profile, name="profile"),
    # presencia y notificaciones
    path("conectados/", views_access.connected, name="connected"),
    path("notificaciones/", views_access.notifications, name="notifications"),
    path("notificaciones/<int:pk>/leida/", views_access.notification_read, name="notification_read"),
    path("api/pulso/", views_access.pulse, name="pulse"),
    # administración de accesos (Gerente General y Oficial de Seguridad de la Información)
    path("accesos/", views_access.access_list, name="access_list"),
    path("accesos/masivo/", views_access.access_bulk, name="access_bulk"),
    path("accesos/credenciales/", views_access.credentials_issued, name="credentials_issued"),
    path("accesos/solicitudes/<int:pk>/", views_access.password_request_resolve, name="password_request_resolve"),
    path("accesos/<uuid:pk>/", views_access.access_user, name="access_user"),
]
