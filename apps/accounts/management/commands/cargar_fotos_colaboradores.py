"""Carga las fotos de perfil de apps/accounts/data/fotos/ (nombre del archivo = nombre_apellido.jpg).

    python manage.py cargar_fotos_colaboradores [--reemplazar]

No reemplaza una foto que la persona ya haya subido, salvo con --reemplazar."""

import unicodedata
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from apps.accounts.avatars import save_avatar

FOLDER = Path(__file__).resolve().parents[2] / "data" / "fotos"


def tokens(text):
    text = unicodedata.normalize("NFKD", text or "")
    return ["".join(c for c in t if c.isalnum()) for t in "".join(c for c in text if not unicodedata.combining(c)).lower().replace("_", " ").split()]


class Command(BaseCommand):
    help = "Carga las fotos de perfil de los colaboradores."

    def add_arguments(self, parser):
        parser.add_argument("--reemplazar", action="store_true")

    def handle(self, *args, **opts):
        User = get_user_model()
        users = list(User.objects.all())
        for path in sorted(FOLDER.glob("*.jpg")):
            wanted = tokens(path.stem)
            matches = [u for u in users
                       if tokens(u.first_name)[:1] == wanted[:1] and set(wanted[1:]) & set(tokens(u.last_name))]
            if len(matches) != 1:
                self.stdout.write(self.style.WARNING(f"  {path.name}: {'no se encontró a la persona' if not matches else 'hay más de una persona con ese nombre'}"))
                continue
            user = matches[0]
            if user.photo and not opts["reemplazar"]:
                self.stdout.write(f"  {user.get_full_name()}: ya tiene foto (use --reemplazar para cambiarla)")
                continue
            save_avatar(user, SimpleUploadedFile(path.name, path.read_bytes(), content_type="image/jpeg"), None)
            self.stdout.write(self.style.SUCCESS(f"  {user.get_full_name()}: foto cargada"))
