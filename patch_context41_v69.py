from pathlib import Path
import re


print("=== PATCH CONTEXT 4.1 V69 ===")

settings = Path("config/settings/base.py")
text = settings.read_text(encoding="utf-8")
backup = settings.with_name(
    settings.name + ".before_context41_v69.bak"
)

if not backup.exists():
    backup.write_text(text, encoding="utf-8")

app_ref = "apps.context41.apps.Context41Config"

if app_ref not in text:
    anchors = [
        '    "apps.organization.apps.OrganizationConfig",\n',
        '    "apps.dashboard.apps.DashboardConfig",\n',
    ]

    anchor = next(
        (item for item in anchors if item in text),
        None,
    )

    if anchor is None:
        raise SystemExit(
            "ERROR: no se encontró un punto seguro "
            "para registrar Context41Config."
        )

    text = text.replace(
        anchor,
        anchor
        + '    "apps.context41.apps.Context41Config",\n',
        1,
    )

settings.write_text(text, encoding="utf-8")
print("OK: Context41Config registrado")


urls = Path("config/urls.py")
utext = urls.read_text(encoding="utf-8")
ubackup = urls.with_name(
    urls.name + ".before_context41_v69.bak"
)

if not ubackup.exists():
    ubackup.write_text(utext, encoding="utf-8")

route = '    path("", include("apps.context41.urls")),\n'

if 'include("apps.context41.urls")' not in utext:
    match = re.search(
        r"urlpatterns\s*=\s*\[\s*\n",
        utext,
    )

    if not match:
        raise SystemExit(
            "ERROR: no se encontró urlpatterns "
            "en config/urls.py"
        )

    pos = match.end()
    utext = utext[:pos] + route + utext[pos:]

urls.write_text(utext, encoding="utf-8")
print("OK: /sgsi/4.1/ asignado al módulo Context41")


delete_file = Path(
    "apps/core/deletion_protection.py"
)

if delete_file.exists():
    dtext = delete_file.read_text(encoding="utf-8")
    dbackup = delete_file.with_name(
        delete_file.name + ".before_context41_v69.bak"
    )

    if not dbackup.exists():
        dbackup.write_text(dtext, encoding="utf-8")

    labels = [
        '        "context41.contextdocument",\n',
        '        "context41.contextdocumentversion",\n',
        '        "context41.legalrequirement",\n',
    ]

    missing = [
        label
        for label in labels
        if label.strip() not in dtext
    ]

    if missing:
        anchors = [
            '        "organization.positionassignment",\n',
            '        "dashboard.strategicfactor",\n',
            '        "controls.controldocumentassignment",\n',
        ]

        anchor = next(
            (item for item in anchors if item in dtext),
            None,
        )

        if anchor:
            dtext = dtext.replace(
                anchor,
                anchor
                + "\n        # SGSI 4.1\n"
                + "".join(missing),
                1,
            )

            delete_file.write_text(
                dtext,
                encoding="utf-8",
            )

            print(
                "OK: modelos 4.1 protegidos "
                "contra borrado físico"
            )

print("")
print("Patch V69 finalizado.")
