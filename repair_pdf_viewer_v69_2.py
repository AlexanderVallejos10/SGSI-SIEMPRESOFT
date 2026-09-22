from pathlib import Path

print("=== REPARACIÓN VISOR PDF V69.2 ===")

views = Path("apps/dashboard/views.py")
text = views.read_text(encoding="utf-8")

backup = views.with_name(
    views.name + ".before_pdf_iframe_v69_2.bak"
)
if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

import_line = (
    "from django.views.decorators.clickjacking "
    "import xframe_options_sameorigin\n"
)

if import_line not in text:
    anchor = (
        "from django.shortcuts import render\n"
    )

    if anchor in text:
        text = text.replace(
            anchor,
            anchor + import_line,
            1,
        )
    else:
        # Fallback: insert after imports from django.
        marker = "from django.http import FileResponse, Http404, JsonResponse\n"
        if marker not in text:
            raise SystemExit(
                "ERROR: no se encontró un punto seguro "
                "para importar xframe_options_sameorigin."
            )
        text = text.replace(
            marker,
            marker + import_line,
            1,
        )

# Decorar únicamente el visor inline.
target = "@login_required\ndef artifact_view("
replacement = (
    "@login_required\n"
    "@xframe_options_sameorigin\n"
    "def artifact_view("
)

if replacement not in text:
    if target not in text:
        raise SystemExit(
            "ERROR: no se encontró artifact_view() "
            "en apps/dashboard/views.py"
        )
    text = text.replace(
        target,
        replacement,
        1,
    )

views.write_text(
    text,
    encoding="utf-8",
)

print("OK: artifact_view permite iframe SAMEORIGIN")
print("Backup:", backup)
print("")
print("Siguiente:")
print("python -m py_compile apps\\dashboard\\views.py")
print("docker compose exec web python manage.py check")
print("docker compose restart web")
