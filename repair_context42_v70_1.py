from pathlib import Path
import re

print("=== REPARACIÓN CONTEXT42 V70.1 ===")

candidates = [
    Path("config/settings/base.py"),
    Path("config/settings.py"),
    Path("config/settings/local.py"),
    Path("config/settings/development.py"),
]

settings_path = next(
    (p for p in candidates if p.exists()),
    None,
)

if settings_path is None:
    raise SystemExit(
        "ERROR: no se encontró un archivo de settings conocido."
    )

text = settings_path.read_text(
    encoding="utf-8"
)

backup = settings_path.with_name(
    settings_path.name + ".before_context42_v70_1.bak"
)

if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

app_line = '"apps.context42.apps.Context42Config",'

if app_line not in text:
    # Preferir insertar junto a dashboard/organization para mantener orden.
    anchors = [
        '"apps.organization.apps.OrganizationConfig",',
        '"apps.context41.apps.Context41Config",',
        '"apps.dashboard.apps.DashboardConfig",',
        '"apps.dashboard",',
    ]

    inserted = False

    for anchor in anchors:
        if anchor in text:
            text = text.replace(
                anchor,
                anchor + "\n    " + app_line,
                1,
            )
            inserted = True
            break

    if not inserted:
        match = re.search(
            r"INSTALLED_APPS\s*=\s*\[\s*\n",
            text,
        )

        if not match:
            raise SystemExit(
                f"ERROR: se encontró {settings_path}, "
                "pero no se pudo localizar INSTALLED_APPS."
            )

        pos = match.end()
        text = (
            text[:pos]
            + "    "
            + app_line
            + "\n"
            + text[pos:]
        )

    settings_path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "OK: Context42Config agregado en",
        settings_path,
    )
else:
    print(
        "OK: Context42Config ya estaba registrado en",
        settings_path,
    )

# Reparar el instalador local para que no vuelva a fallar si se reejecuta.
installer = Path(
    "install_context42_v70.py"
)

if installer.exists():
    itext = installer.read_text(
        encoding="utf-8"
    )

    ibackup = installer.with_name(
        installer.name
        + ".before_context42_v70_1.bak"
    )

    if not ibackup.exists():
        ibackup.write_text(
            itext,
            encoding="utf-8",
        )

    if "config/settings/base.py" not in itext:
        itext = itext.replace(
            "candidates = [ROOT / 'config/settings.py', ROOT / 'config/settings/base.py']",
            "candidates = [ROOT / 'config/settings/base.py', ROOT / 'config/settings.py']",
        )

        installer.write_text(
            itext,
            encoding="utf-8",
        )

        print(
            "OK: instalador V70 local ajustado"
        )

print("")
print("Reparación terminada.")
print("Ahora ejecute:")
print("docker compose exec web python manage.py check")
print("docker compose exec web python manage.py makemigrations context42")
