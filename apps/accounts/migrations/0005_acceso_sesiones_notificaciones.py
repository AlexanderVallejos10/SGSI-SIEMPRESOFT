import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_corporatesystem_status_as_of_and_more"),
    ]

    operations = [
        migrations.AddField("user", "must_change_password", models.BooleanField(default=False, help_text="Debe cambiar la contraseña al ingresar (credenciales nuevas o restablecidas).")),
        migrations.AddField("user", "password_changes", models.PositiveIntegerField(default=0, help_text="Veces que el usuario cambió su contraseña por su cuenta.")),
        migrations.AddField("user", "password_changed_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("user", "credentials_issued_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("user", "last_seen_at", models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(db_index=True, max_length=64)),
                ("started_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("ended_reason", models.CharField(blank=True, choices=[("logout", "Cerró sesión"), ("inactividad", "Cerrada por inactividad"), ("reemplazada", "Reemplazada por un nuevo ingreso")], max_length=20)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="connection_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Sesión de usuario", "verbose_name_plural": "Sesiones de usuarios", "ordering": ("-started_at",)},
        ),
        migrations.CreateModel(
            name="LoginAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(db_index=True, max_length=150)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("success", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"verbose_name": "Intento de ingreso", "verbose_name_plural": "Intentos de ingreso", "ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PasswordChangeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("approved", "Aprobada"), ("rejected", "Rechazada")], db_index=True, default="pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.TextField(blank=True)),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="password_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Solicitud de cambio de contraseña", "verbose_name_plural": "Solicitudes de cambio de contraseña", "ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(db_index=True, max_length=40)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True)),
                ("url", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("read_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Notificación", "verbose_name_plural": "Notificaciones", "ordering": ("-created_at",),
                     "indexes": [models.Index(fields=["recipient", "read_at"], name="acc_notif_unread_idx")]},
        ),
    ]
