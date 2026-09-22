from pathlib import Path

print("=== REPARACIÓN DASHBOARD LIVE V72.1 ===")

# ------------------------------------------------------------
# 1) importer.py
# ------------------------------------------------------------
importer = Path("apps/dashboard_live/importer.py")

if not importer.exists():
    raise SystemExit(
        "ERROR: no existe apps/dashboard_live/importer.py"
    )

text = importer.read_text(encoding="utf-8")

backup = importer.with_name(
    importer.name + ".before_dashboard_live_v72_1.bak"
)

if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

old = '        source_formula=cell_data.get("formula", ""),\n'
new = '        source_formula=cell_data.get("formula") or "",\n'

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )
elif new not in text:
    raise SystemExit(
        "ERROR: no se encontró el bloque source_formula "
        "esperado en importer.py."
    )

importer.write_text(
    text,
    encoding="utf-8",
)

print(
    "OK: importer.py normaliza fórmula None -> cadena vacía"
)

# ------------------------------------------------------------
# 2) excel_io.py
# ------------------------------------------------------------
excel_io = Path(
    "apps/dashboard_live/excel_io.py"
)

if not excel_io.exists():
    raise SystemExit(
        "ERROR: no existe apps/dashboard_live/excel_io.py"
    )

text = excel_io.read_text(
    encoding="utf-8"
)

backup = excel_io.with_name(
    excel_io.name + ".before_dashboard_live_v72_1.bak"
)

if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

old = (
    '                "formula": formula_node.text '
    'if formula_node is not None else "",\n'
)

new = (
    '                "formula": '
    '(formula_node.text or "") '
    'if formula_node is not None else "",\n'
)

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )
elif new not in text:
    raise SystemExit(
        "ERROR: no se encontró el bloque de fórmula "
        "esperado en excel_io.py."
    )

excel_io.write_text(
    text,
    encoding="utf-8",
)

print(
    "OK: excel_io.py nunca devuelve formula=None"
)

print("")
print("V72.1 reparada.")
print("")
print("No requiere nueva migración.")
print("El fallo ocurrió dentro de una transacción atómica,")
print("por lo que la importación fallida debe haberse revertido.")
print("")
print("Siguiente:")
print(
    r"python -m py_compile "
    r"apps\dashboard_live\importer.py "
    r"apps\dashboard_live\excel_io.py"
)
print(
    "docker compose exec web python manage.py check"
)
print(
    "docker compose exec web python manage.py "
    "seed_dashboard_live --apply"
)
