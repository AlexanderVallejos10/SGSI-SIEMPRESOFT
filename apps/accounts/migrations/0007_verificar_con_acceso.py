from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def verify(apps, schema_editor):
    """Quien ya recibió credenciales o ya ingresó fue revisado por un administrador: deja de figurar «por verificar»."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(Q(credentials_issued_at__isnull=False) | Q(last_login__isnull=False)).update(
        status="active", source_verified=True, status_as_of=timezone.localdate(), is_active=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_user_photo")]
    operations = [migrations.RunPython(verify, migrations.RunPython.noop)]
