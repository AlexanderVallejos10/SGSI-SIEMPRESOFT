from pathlib import Path

views = Path("apps/dashboard/views.py")
text = views.read_text(encoding="utf-8")

backup = views.with_name(
    views.name + ".before_user_profile_v67.bak"
)
if not backup.exists():
    backup.write_text(
        text,
        encoding="utf-8",
    )

import_line = (
    "from .user_profile_v67 import "
    "get_user_profile_context\n"
)

if (
    "from .user_profile_v67 import "
    "get_user_profile_context"
    not in text
):
    anchor = "from .workbench import ("

    if anchor not in text:
        raise SystemExit(
            "ERROR: no se encontró el import "
            "de workbench en dashboard/views.py"
        )

    text = text.replace(
        anchor,
        import_line + "\n" + anchor,
        1,
    )

start_marker = "def user_profile(request, pk):"

if start_marker in text:
    start = text.index(start_marker)

    end_candidates = [
        text.find("\n\n@login_required", start),
        text.find("\n\ndef health", start),
    ]

    end_candidates = [
        value
        for value in end_candidates
        if value != -1
    ]

    if not end_candidates:
        raise SystemExit(
            "ERROR: no se pudo delimitar "
            "la vista user_profile."
        )

    end = min(end_candidates)

    new_block = (
        "def user_profile(request, pk):\n"
        "    context = _base_context()\n"
        "    context.update(\n"
        "        get_user_profile_context(pk)\n"
        "    )\n"
        "    return render(\n"
        "        request,\n"
        "        \"dashboard/user_profile.html\",\n"
        "        context,\n"
        "    )\n"
    )

    text = (
        text[:start]
        + new_block
        + text[end:]
    )
else:
    raise SystemExit(
        "ERROR: no se encontró "
        "def user_profile(request, pk)."
    )

views.write_text(
    text,
    encoding="utf-8",
)

print(
    "OK: dashboard/views.py "
    "usa el perfil V67"
)
