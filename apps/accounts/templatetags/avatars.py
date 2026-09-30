from django import template

from apps.accounts.avatars import avatar_html

register = template.Library()


@register.simple_tag
def avatar(user, size=""):
    """{% avatar user %} o {% avatar user "lg" %}: la foto de la persona o sus iniciales."""
    if not user or not getattr(user, "pk", None):
        return ""
    return avatar_html(user, size)
