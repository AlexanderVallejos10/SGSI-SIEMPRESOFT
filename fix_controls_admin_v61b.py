from pathlib import Path

path = Path("apps/controls/admin.py")
text = path.read_text(encoding="utf-8")

backup = Path("apps/controls/admin_before_v61b_fix.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

old_clause = '''    autocomplete_fields = (
        "framework",
        "parent",
        "source_artifact",
    )
'''
new_clause = '''    raw_id_fields = (
        "framework",
    )

    autocomplete_fields = (
        "parent",
        "source_artifact",
    )
'''

old_support = '''    autocomplete_fields = (
        "control",
        "source_artifact",
    )
'''
new_support = '''    raw_id_fields = (
        "control",
    )

    autocomplete_fields = (
        "source_artifact",
    )
'''

if old_clause in text:
    text = text.replace(old_clause, new_clause, 1)
elif 'raw_id_fields = (\n        "framework",' not in text:
    raise SystemExit(
        "ERROR: no se encontró el bloque autocomplete_fields de ISOClauseAdmin."
    )

if old_support in text:
    text = text.replace(old_support, new_support, 1)
elif 'raw_id_fields = (\n        "control",' not in text:
    raise SystemExit(
        "ERROR: no se encontró el bloque autocomplete_fields de "
        "ControlSupportReferenceAdmin."
    )

path.write_text(text, encoding="utf-8")

print("OK: admin de controls corregido.")
print(f"Backup: {backup}")
print("- ISOClauseAdmin.framework usa raw_id_fields")
print("- ControlSupportReferenceAdmin.control usa raw_id_fields")
print("- Se conservan autocompletados seguros para parent/source_artifact")
