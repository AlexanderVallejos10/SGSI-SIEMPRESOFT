from .security import is_sgsi_admin


def access(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    admin = is_sgsi_admin(user)
    data = {"sgsi_admin": admin, "unread_notifications": user.notifications.filter(read_at__isnull=True).count()}
    if admin:
        from .models import PasswordChangeRequest
        data["pending_password_requests"] = PasswordChangeRequest.objects.filter(status="pending").count()
    return data
