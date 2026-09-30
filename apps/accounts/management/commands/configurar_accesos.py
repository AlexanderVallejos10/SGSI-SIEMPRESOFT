"""Deja listos los accesos al sistema.

    python manage.py configurar_accesos

1. Sincroniza los roles y permisos (seed_rbac y seed_business_permissions).
2. El rol «Administrador SGSI» puede ver, crear y editar en todos los módulos (sin borrar).
3. El Gerente General y el Oficial / Jefe de Seguridad de la Información (según su puesto en el
   organigrama o su correo) pasan a ese rol.
4. Quien no tenga ningún rol recibe «Usuario / Colaborador».
5. Si los administradores aún no tienen contraseña, se generan sus credenciales y se muestran UNA
   vez aquí. Con ellas ingresan, crean su contraseña y generan las del resto desde «Accesos».

Se puede ejecutar las veces que haga falta: no duplica nada ni cambia contraseñas ya creadas
(salvo con --regenerar-admins).
"""

import unicodedata

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.security import ADMIN_ROLE, DEFAULT_ROLE, issue_credentials, sync_admin_role

ADMIN_POSITIONS = ("gerente general", "oficial de seguridad", "jefe de seguridad")
ADMIN_EMAILS = ("mguevara@siempresoft.com", "ksalazar@siempresoft.com")


def norm(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class Command(BaseCommand):
    help = "Configura roles, administradores del SGSI y credenciales iniciales."

    def add_arguments(self, parser):
        parser.add_argument("--regenerar-admins", action="store_true",
                            help="Genera credenciales nuevas para los administradores aunque ya tengan contraseña.")

    def handle(self, *args, **opts):
        call_command("seed_rbac", stdout=self.stdout)
        call_command("seed_business_permissions", stdout=self.stdout)
        with transaction.atomic():
            total = sync_admin_role()
            self.stdout.write(f"Rol «{ADMIN_ROLE}»: {total} permisos (ver, crear y editar en todos los módulos).")
            admins = self.find_admins()
            group = Group.objects.get(name=ADMIN_ROLE)
            for user in admins:
                user.groups.add(group)
                if not user.is_staff:
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])
            default = Group.objects.filter(name=DEFAULT_ROLE).first()
            if default:
                User = get_user_model()
                without = User.objects.filter(is_active=True, groups__isnull=True, is_superuser=False)
                for user in without:
                    user.groups.add(default)
                self.stdout.write(f"Rol «{DEFAULT_ROLE}» asignado a {without.count()} persona(s) sin rol.")

            issued = []
            for user in admins:
                if opts["regenerar_admins"] or not user.has_usable_password():
                    username, password = issue_credentials(user, None, reason="Configuración inicial de accesos")
                    issued.append((user.get_full_name() or username, username, password))

        self.stdout.write(self.style.SUCCESS("\nAdministradores del SGSI:"))
        for user in admins:
            self.stdout.write(f"  - {user.get_full_name() or user.username} ({user.email or user.username})")
        if not admins:
            self.stdout.write(self.style.WARNING(
                "  No se encontró al Gerente General ni al Oficial de Seguridad. Ubíquelos en el organigrama "
                "o créelos y vuelva a ejecutar el comando."))
        if issued:
            self.stdout.write(self.style.WARNING("\nCredenciales temporales (se muestran solo ahora; al ingresar se pide cambiarlas):"))
            for name, username, password in issued:
                self.stdout.write(f"  {name:32s} usuario: {username:14s} contraseña: {password}")
            self.stdout.write("\nIngreso: /ingresar/")

    def find_admins(self):
        User = get_user_model()
        found = {}
        try:
            from apps.organization.models import PositionAssignment
            for a in PositionAssignment.objects.filter(end_date__isnull=True).select_related("user", "position"):
                if any(key in norm(a.position.title) for key in ADMIN_POSITIONS):
                    found[a.user.pk] = a.user
        except Exception:
            pass
        for email in ADMIN_EMAILS:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                found[user.pk] = user
        for user in User.objects.filter(groups__name=ADMIN_ROLE):
            found[user.pk] = user
        return [u for u in found.values() if u.is_active or not u.has_usable_password()]
