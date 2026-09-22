from pathlib import Path

settings_dir = Path("config/settings")
delete_file = Path("apps/core/deletion_protection.py")

if not settings_dir.exists():
    raise SystemExit("ERROR: no existe config/settings")

candidates = sorted(settings_dir.glob("*.py"))
target = None

for file_path in candidates:
    text = file_path.read_text(encoding="utf-8")
    if "INSTALLED_APPS" in text and "apps.controls" in text:
        target = file_path
        break

if target is None:
    raise SystemExit(
        "ERROR: no se encontró un archivo de settings con "
        "INSTALLED_APPS y apps.controls"
    )

settings_text = target.read_text(encoding="utf-8")
delete_text = delete_file.read_text(encoding="utf-8")

settings_backup = target.with_name(
    target.stem + "_before_dashboard_v62b.bak"
)
delete_backup = Path(
    "apps/core/deletion_protection_before_dashboard_v62b.bak"
)

if not settings_backup.exists():
    settings_backup.write_text(settings_text, encoding="utf-8")

if not delete_backup.exists():
    delete_backup.write_text(delete_text, encoding="utf-8")

app_entry = '    "apps.dashboard.apps.DashboardConfig",\n'

if "apps.dashboard.apps.DashboardConfig" not in settings_text:
    lines = settings_text.splitlines(keepends=True)
    insert_at = None

    for index, line in enumerate(lines):
        if "apps.controls" in line:
            insert_at = index + 1
            break

    if insert_at is None:
        raise SystemExit(
            "ERROR: no se encontró la línea de apps.controls "
            "para insertar dashboard."
        )

    lines.insert(insert_at, app_entry)
    settings_text = "".join(lines)

labels = [
    '        "dashboard.dashboardsnapshot",\n',
    '        "dashboard.dashboard sourcerow",\n',
]

# Etiquetas reales sin espacios.
labels = [
    '        "dashboard.dashboardsnapshot",\n',
    '        "dashboard.dashboardsourcerow",\n',
    '        "dashboard.sgsimetric",\n',
    '        "dashboard.securityobjective",\n',
    '        "dashboard.objectivealignment",\n',
    '        "dashboard.strategicfactor",\n',
]

anchor = '        "controls.controldocumentassignment",\n'

if anchor not in delete_text:
    raise SystemExit(
        "ERROR: no se encontró controls.controldocumentassignment "
        "en deletion_protection.py"
    )

addition = "".join(
    label
    for label in labels
    if label.strip() not in delete_text
)

if addition:
    delete_text = delete_text.replace(
        anchor,
        anchor + "\n        # Dashboard SGSI\n" + addition,
        1,
    )

target.write_text(settings_text, encoding="utf-8")
delete_file.write_text(delete_text, encoding="utf-8")

print("OK: DashboardConfig agregado a INSTALLED_APPS.")
print(f"Settings modificado: {target}")
print("OK: 6 modelos Dashboard agregados a protección física.")
