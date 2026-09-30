from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_acceso_sesiones_notificaciones")]

    operations = [
        migrations.AddField("user", "photo", models.FileField(blank=True, upload_to="avatares/")),
    ]
