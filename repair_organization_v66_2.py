from pathlib import Path

print("=== REPARACIÓN ORGANIZATION V66.2 ===")

model_file = Path("apps/organization/models.py")
text = model_file.read_text(encoding="utf-8")

backup = model_file.with_name(
    model_file.name + ".before_org_v66_2.bak"
)
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

old_name = "org_assignment_position_active_idx"
new_name = "org_asg_pos_active_idx"

if old_name in text:
    text = text.replace(old_name, new_name)
elif new_name not in text:
    raise SystemExit(
        "ERROR: no se encontró el índice esperado en "
        "apps/organization/models.py"
    )

model_file.write_text(text, encoding="utf-8")
print(
    f"OK: índice renombrado: {old_name} -> {new_name}"
)

installer = Path(
    "install_organization_smartart_v66.py"
)

if installer.exists():
    itext = installer.read_text(
        encoding="utf-8"
    )
    ibackup = installer.with_name(
        installer.name + ".before_org_v66_2.bak"
    )

    if not ibackup.exists():
        ibackup.write_text(
            itext,
            encoding="utf-8"
        )

    if old_name in itext:
        itext = itext.replace(
            old_name,
            new_name,
        )
        installer.write_text(
            itext,
            encoding="utf-8"
        )
        print(
            "OK: instalador V66 local corregido"
        )

print("")
print("Reparación V66.2 terminada.")
print("Ahora ejecute py_compile y manage.py check.")
