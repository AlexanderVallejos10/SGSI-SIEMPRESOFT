from pathlib import Path

settings = Path("config/settings/base.py")
text = settings.read_text(encoding="utf-8")
backup = settings.with_name(
    settings.name + ".before_org_v66.bak"
)

if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

app_line = '    "apps.organization.apps.OrganizationConfig",\n'

if "apps.organization.apps.OrganizationConfig" not in text:
    anchor = '    "apps.dashboard.apps.DashboardConfig",\n'

    if anchor not in text:
        raise SystemExit(
            "ERROR: no se encontró DashboardConfig en INSTALLED_APPS."
        )

    text = text.replace(
        anchor,
        anchor + app_line,
        1,
    )

settings.write_text(
    text,
    encoding="utf-8",
)

urls = Path("config/urls.py")
utext = urls.read_text(
    encoding="utf-8"
)
ubackup = urls.with_name(
    urls.name + ".before_org_v66.bak"
)

if not ubackup.exists():
    ubackup.write_text(
        utext,
        encoding="utf-8",
    )

organization_route = (
    '    path("organizacion/", include("apps.organization.urls")),\n'
)

if 'include("apps.organization.urls")' not in utext:
    dashboard_anchor = (
        '    path("", include("apps.dashboard.urls")),\n'
    )

    if dashboard_anchor not in utext:
        raise SystemExit(
            "ERROR: no se encontró include de dashboard en config/urls.py."
        )

    utext = utext.replace(
        dashboard_anchor,
        organization_route + dashboard_anchor,
        1,
    )

urls.write_text(
    utext,
    encoding="utf-8",
)

base = Path(
    "templates/base.html"
)

if base.exists():
    btext = base.read_text(
        encoding="utf-8"
    )

    bbackup = base.with_name(
        base.name + ".before_org_v66.bak"
    )

    if not bbackup.exists():
        bbackup.write_text(
            btext,
            encoding="utf-8",
        )

    btext = btext.replace(
        "{% url 'dashboard:organization' %}",
        "{% url 'organization:chart' %}",
    )

    base.write_text(
        btext,
        encoding="utf-8",
    )

delete_file = Path(
    "apps/core/deletion_protection.py"
)

if delete_file.exists():
    dtext = delete_file.read_text(
        encoding="utf-8"
    )

    dbackup = delete_file.with_name(
        delete_file.name + ".before_org_v66.bak"
    )

    if not dbackup.exists():
        dbackup.write_text(
            dtext,
            encoding="utf-8",
        )

    labels = [
        '        "organization.organizationalarea",\n',
        '        "organization.position",\n',
        '        "organization.positionassignment",\n',
    ]

    anchor = '        "dashboard.strategicfactor",\n'

    if anchor in dtext:
        addition = "".join(
            label
            for label in labels
            if label.strip() not in dtext
        )

        if addition:
            dtext = dtext.replace(
                anchor,
                anchor
                + "\n        # Organización\n"
                + addition,
                1,
            )

    delete_file.write_text(
        dtext,
        encoding="utf-8",
    )

print("OK: settings, URLs, menú y protección actualizados.")
