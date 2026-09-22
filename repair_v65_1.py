from pathlib import Path

print("=== REPARACION V65.1 ===")

selectors = Path("apps/dashboard/selectors.py")
text = selectors.read_text(encoding="utf-8")
backup = selectors.with_name(selectors.name + ".before_v65_1_repair.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

bad_signatures = [
    'def get_clause_context(str(code).rstrip(".")):',
    "def get_clause_context(str(code).rstrip('.')):",
]

for bad in bad_signatures:
    if bad in text:
        text = text.replace(bad, "def get_clause_context(code):", 1)
        break

if "def get_clause_context(code):" not in text:
    raise SystemExit("ERROR: no se encontró get_clause_context() para reparar.")

marker = "def get_clause_context(code):\n"
normalization = '    code = str(code or "").strip().rstrip(".")\n'
idx = text.find(marker)

if idx != -1:
    body_start = idx + len(marker)
    following = text[body_start:body_start + 180]
    if 'rstrip(".")' not in following and "rstrip('.')" not in following:
        text = text[:body_start] + normalization + text[body_start:]

selectors.write_text(text, encoding="utf-8")
print("OK: selectors.py reparado")

product = Path("apps/dashboard/product_contexts.py")
if product.exists():
    ptext = product.read_text(encoding="utf-8")
    pbackup = product.with_name(product.name + ".before_v65_1_repair.bak")
    if not pbackup.exists():
        pbackup.write_text(ptext, encoding="utf-8")

    ptext = ptext.replace("confidence_score", "confidence")

    ptext = ptext.replace(
        "AccessReview.objects\n        .filter(user=user)",
        "AccessReview.objects\n        .filter(access__user=user)",
    )
    ptext = ptext.replace(
        "AccessReview.objects.filter(user=user)",
        "AccessReview.objects.filter(access__user=user)",
    )

    ptext = ptext.replace(
        'getattr(item, "role_name", "") or getattr(item, "profile_name", "") or "—"',
        'getattr(item, "role_profile", "") or "—"',
    )

    product.write_text(ptext, encoding="utf-8")
    print("OK: product_contexts.py reparado")

installer = Path("install_siempresoft_v65_focus1.py")
if installer.exists():
    itext = installer.read_text(encoding="utf-8")
    ibackup = installer.with_name(installer.name + ".before_v65_1_repair.bak")
    if not ibackup.exists():
        ibackup.write_text(itext, encoding="utf-8")

    bad_installer_line = (
        "stext = stext.replace('get_clause_context(code)', "
        "'get_clause_context(str(code).rstrip(\".\"))')"
    )
    if bad_installer_line in itext:
        itext = itext.replace(
            bad_installer_line,
            "# V65.1: get_clause_context normaliza el código dentro de la función",
            1,
        )

    installer.write_text(itext, encoding="utf-8")
    print("OK: instalador V65 local neutralizado")

print("")
print("Reparación terminada. Ahora ejecute py_compile y manage.py check.")
