"""Unifica personas y activos duplicados: un código, una persona; un código, un activo.

    python manage.py unificar_personas            # muestra qué haría, sin cambiar nada
    python manage.py unificar_personas --aplicar  # unifica (en una transacción, con registro en la auditoría)
"""

from django.core.management.base import BaseCommand

from apps.accounts.unify import duplicate_assets, duplicate_groups, merge, merge_assets


def label(u):
    extra = []
    if u.has_usable_password():
        extra.append("con contraseña")
    if u.photo:
        extra.append("con foto")
    return f"{u.get_full_name() or u.username} [{u.business_code}, {u.username}{', ' + ', '.join(extra) if extra else ''}]"


class Command(BaseCommand):
    help = "Unifica personas y activos duplicados."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true")

    def handle(self, *args, **opts):
        apply = opts["aplicar"]
        groups = duplicate_groups()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Personas: {len(groups)} grupo(s) duplicado(s)"))
        for keep, dups, doubtful in groups:
            if doubtful:
                self.stdout.write(self.style.WARNING(f"  REVISAR A MANO: {label(keep)} y {', '.join(label(d) for d in dups)}"
                                                     " (más de una cuenta con contraseña propia y correos distintos)"))
                continue
            self.stdout.write(f"  Queda {label(keep)}  ←  {', '.join(label(d) for d in dups)}")
            if apply:
                for line in merge(keep, dups):
                    self.stdout.write(self.style.SUCCESS(f"      {line}"))
        assets = duplicate_assets()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Activos: {len(assets)} código(s) duplicado(s)"))
        for keep, dups in assets:
            self.stdout.write(f"  Queda {keep.code}  ←  {', '.join(d.code for d in dups)}")
            if apply:
                merge_assets(keep, dups)
        if not apply:
            self.stdout.write(self.style.NOTICE("\nVista previa: no se cambió nada. Ejecute con --aplicar para unificar."))
        else:
            self.stdout.write(self.style.SUCCESS("\nUnificación terminada."))
