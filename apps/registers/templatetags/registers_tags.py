from django import template

register = template.Library()


@register.filter
def choices_for(section, key):
    """Opciones del campo; si el valor guardado no está en la lista (p. ej. «Foro»), también se ofrece."""
    field = next((f for f in section["fields"] if f["key"] == key), None)
    return list(field.get("choices", [])) if field else []


@register.simple_tag
def options(section, key, current):
    choices = choices_for(section, key)
    if current and current not in choices:
        choices = [current] + choices
    return choices


@register.filter
def slugify_state(value):
    return {
        "Realizada": "ok", "En uso": "ok", "Sí": "ok", "Autorizada": "ok",
        "En revisión": "warn", "Retirada": "off",
        "Programada": "plan", "Por revisar": "plan",
        "Reprogramada": "warn", "En desuso": "off", "Cancelada": "off", "No": "bad",
    }.get(value, "plan")


@register.filter
def get_item(data, key):
    return (data or {}).get(key, "")


@register.filter
def as_date(value):
    """2026-04-09 → 09/04/2026 (las fechas se guardan en ISO para ordenar y exportar)."""
    value = str(value or "")
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return f"{value[8:10]}/{value[5:7]}/{value[:4]}"
    return value
