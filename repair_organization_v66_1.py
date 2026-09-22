from pathlib import Path
import re

print("=== REPARACIÓN ORGANIZATION V66.1 ===")

# ------------------------------------------------------------------
# 1) INSTALLED_APPS
# ------------------------------------------------------------------
settings = Path("config/settings/base.py")
stext = settings.read_text(encoding="utf-8")
sbackup = settings.with_name(settings.name + ".before_org_v66_1.bak")

if not sbackup.exists():
    sbackup.write_text(stext, encoding="utf-8")

app_ref = "apps.organization.apps.OrganizationConfig"

if app_ref not in stext:
    dashboard_variants = [
        '    "apps.dashboard.apps.DashboardConfig",\n',
        "    'apps.dashboard.apps.DashboardConfig',\n",
        '    "apps.dashboard",\n',
        "    'apps.dashboard',\n",
    ]

    inserted = False

    for anchor in dashboard_variants:
        if anchor in stext:
            stext = stext.replace(
                anchor,
                anchor + '    "apps.organization.apps.OrganizationConfig",\n',
                1,
            )
            inserted = True
            break

    if not inserted:
        match = re.search(
            r"INSTALLED_APPS\s*=\s*\[\s*\n",
            stext,
        )
        if not match:
            raise SystemExit(
                "ERROR: no se pudo localizar INSTALLED_APPS en base.py"
            )

        pos = match.end()
        stext = (
            stext[:pos]
            + '    "apps.organization.apps.OrganizationConfig",\n'
            + stext[pos:]
        )

    settings.write_text(stext, encoding="utf-8")

print("OK: OrganizationConfig presente en INSTALLED_APPS")

# ------------------------------------------------------------------
# 2) config/urls.py
# ------------------------------------------------------------------
urls = Path("config/urls.py")
utext = urls.read_text(encoding="utf-8")
ubackup = urls.with_name(urls.name + ".before_org_v66_1.bak")

if not ubackup.exists():
    ubackup.write_text(utext, encoding="utf-8")

route_line = '    path("organizacion/", include("apps.organization.urls")),\n'

if 'include("apps.organization.urls")' not in utext:
    # Insertar justo después de "urlpatterns = [".
    match = re.search(
        r"urlpatterns\s*=\s*\[\s*\n",
        utext,
    )

    if not match:
        raise SystemExit(
            "ERROR: no se encontró el inicio de urlpatterns en config/urls.py"
        )

    pos = match.end()
    utext = (
        utext[:pos]
        + route_line
        + utext[pos:]
    )

    urls.write_text(utext, encoding="utf-8")

print("OK: /organizacion/ apunta a apps.organization.urls")

# ------------------------------------------------------------------
# 3) Menú global: Organización -> nueva app
# ------------------------------------------------------------------
base = Path("templates/base.html")

if base.exists():
    btext = base.read_text(encoding="utf-8")
    bbackup = base.with_name(base.name + ".before_org_v66_1.bak")

    if not bbackup.exists():
        bbackup.write_text(btext, encoding="utf-8")

    replacements = [
        (
            "{% url 'dashboard:organization' %}",
            "{% url 'organization:chart' %}",
        ),
        (
            'href="/organizacion/"',
            'href="{% url \'organization:chart\' %}"',
        ),
    ]

    for old, new in replacements:
        btext = btext.replace(old, new)

    base.write_text(btext, encoding="utf-8")
    print("OK: menú Organización actualizado")

# ------------------------------------------------------------------
# 4) Protección contra borrado físico
# ------------------------------------------------------------------
delete_file = Path("apps/core/deletion_protection.py")

if delete_file.exists():
    dtext = delete_file.read_text(encoding="utf-8")
    dbackup = delete_file.with_name(
        delete_file.name + ".before_org_v66_1.bak"
    )

    if not dbackup.exists():
        dbackup.write_text(dtext, encoding="utf-8")

    labels = [
        '        "organization.organizationalarea",\n',
        '        "organization.position",\n',
        '        "organization.positionassignment",\n',
    ]

    missing = [
        label
        for label in labels
        if label.strip() not in dtext
    ]

    if missing:
        # Preferir insertar después del último dashboard.* conocido.
        anchors = [
            '        "dashboard.strategicfactor",\n',
            '        "dashboard.objectivealignment",\n',
            '        "controls.controldocumentassignment",\n',
        ]

        anchor = next(
            (item for item in anchors if item in dtext),
            None,
        )

        if anchor is None:
            raise SystemExit(
                "ERROR: no se encontró un punto seguro para agregar "
                "los modelos organization en deletion_protection.py"
            )

        dtext = dtext.replace(
            anchor,
            anchor
            + "\n        # Organización\n"
            + "".join(missing),
            1,
        )

        delete_file.write_text(dtext, encoding="utf-8")

    print("OK: modelos organization protegidos")

print("")
print("Reparación V66.1 terminada.")
print("Siguiente: py_compile + manage.py check.")
