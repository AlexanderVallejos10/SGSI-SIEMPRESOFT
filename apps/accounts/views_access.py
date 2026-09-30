"""Ingreso al sistema, cuenta del usuario, conectados, notificaciones y administración de accesos."""

import io
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_not_required, login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .models import LoginAttempt, Notification, PasswordChangeRequest, UserSession
from .presence import close_stale_sessions, connected_time, human, online_users, touch
from .security import (
    ADMIN_ROLE,
    available_modules,
    can_change_own_password,
    change_own_password,
    client_ip,
    is_sgsi_admin,
    issue_credentials,
    module_state,
    request_password_change,
    resolve_password_request,
    set_user_access,
)

MAX_FAILURES = 5
LOCK_MINUTES = 15


def admin_required(view):
    def wrapper(request, *args, **kwargs):
        if not is_sgsi_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return login_required(wrapper)


def initials(user):
    from .avatars import initials as _initials
    return _initials(user)


def _photo_url(user):
    return user.photo.url if user.photo else ""


# ---------------------------------------------------------------- ingreso
@method_decorator(login_not_required, name="dispatch")
class SgsiLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def _locked(self, username):
        since = timezone.now() - timedelta(minutes=LOCK_MINUTES)
        ip = client_ip(self.request)
        fails = LoginAttempt.objects.filter(success=False, created_at__gte=since).filter(Q(username__iexact=username) | Q(ip_address=ip))
        last_ok = LoginAttempt.objects.filter(success=True, username__iexact=username, created_at__gte=since).order_by("-created_at").first()
        if last_ok:
            fails = fails.filter(created_at__gt=last_ok.created_at)
        return fails.count() >= MAX_FAILURES

    def get_context_data(self, **kwargs):
        from django.contrib.staticfiles import finders

        ctx = super().get_context_data(**kwargs)
        # Librerías de animación instaladas con «instalar_recursos_visuales» (sin ellas, animación nativa).
        ctx["motion"] = {key: bool(finders.find(path)) for key, path in (
            ("gsap", "vendor/gsap/gsap.min.js"), ("split", "vendor/gsap/SplitText.min.js"),
            ("draw", "vendor/gsap/DrawSVGPlugin.min.js"), ("lottie", "vendor/lottie_light.min.js"))}
        return ctx

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "").strip()
        if username and self._locked(username):
            form = self.get_form()
            form.errors.clear()
            form.add_error(None, f"Demasiados intentos fallidos. Espere {LOCK_MINUTES} minutos o pida ayuda al Oficial de Seguridad de la Información.")
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.user.must_change_password:
            return redirect("accounts:password_change")
        return response


# ---------------------------------------------------------------- contraseña propia
@login_required
def password_change(request):
    user = request.user
    allowed = can_change_own_password(user)
    pending = user.password_requests.filter(status="pending").first()
    errors = []
    if request.method == "POST" and allowed:
        new1, new2 = request.POST.get("new_password1", ""), request.POST.get("new_password2", "")
        current = request.POST.get("current_password", "")
        if not user.must_change_password and not user.check_password(current):
            errors.append("La contraseña actual no es correcta.")
        elif new1 != new2:
            errors.append("Las dos contraseñas nuevas no coinciden.")
        else:
            try:
                change_own_password(user, new1, request=request)
            except ValidationError as exc:
                errors += exc.messages
            except PermissionError as exc:
                errors.append(str(exc))
            else:
                update_session_auth_hash(request, user)
                messages.success(request, "Contraseña actualizada.")
                return redirect("accounts:profile")
    return render(request, "accounts/password_change.html", {
        "allowed": allowed, "forced": user.must_change_password, "errors": errors, "pending": pending,
        "is_admin": is_sgsi_admin(user),
    })


@login_required
@require_POST
def password_request(request):
    reason = request.POST.get("reason", "").strip()
    if len(reason) < 10:
        messages.error(request, "Explique en una frase por qué necesita cambiar la contraseña.")
        return redirect("accounts:password_change")
    _, created = request_password_change(request.user, reason, request=request)
    messages.success(request, "Solicitud enviada al Gerente General y al Oficial de Seguridad de la Información." if created
                     else "Ya tiene una solicitud pendiente; le avisaremos cuando la atiendan.")
    return redirect("accounts:password_change")


# ---------------------------------------------------------------- perfil
@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        from .avatars import remove_avatar, save_avatar
        try:
            if request.POST.get("action") == "remove_photo":
                remove_avatar(user, user, request=request)
                messages.success(request, "Foto retirada. Se muestran sus iniciales.")
            elif request.FILES.get("photo"):
                save_avatar(user, request.FILES["photo"], user, request=request)
                messages.success(request, "Foto de perfil actualizada.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("accounts:profile")
    sessions = list(UserSession.objects.filter(user=user)[:15])
    for s in sessions:
        s.duration_text = human(s.duration)
    assignment = None
    try:
        from apps.organization.models import PositionAssignment
        assignment = PositionAssignment.objects.filter(user=user, end_date__isnull=True).select_related("position", "position__area").first()
    except Exception:
        pass
    return render(request, "accounts/profile.html", {
        "u": user, "assignment": assignment, "roles": user.groups.order_by("name"), "modules": module_state(user),
        "sessions": sessions, "time_7": human(connected_time(user, 7)), "time_30": human(connected_time(user, 30)),
        "can_change": can_change_own_password(user), "is_admin": is_sgsi_admin(user),
        "pending": user.password_requests.filter(status="pending").first(),
    })


# ---------------------------------------------------------------- conectados
@login_required
def connected(request):
    close_stale_sessions()
    people = online_users()
    now = timezone.now()
    for p in people:
        p.initials = initials(p)
        p.since_text = human(now - p.online_since)
    recent = get_user_model().objects.filter(is_active=True, last_seen_at__isnull=False).exclude(pk__in=[p.pk for p in people]).order_by("-last_seen_at")[:20]
    return render(request, "accounts/connected.html", {"people": people, "recent": recent})


# ---------------------------------------------------------------- notificaciones
@login_required
def notifications(request):
    if request.method == "POST":
        request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
        return redirect("accounts:notifications")
    items = request.user.notifications.select_related("actor")[:100]
    return render(request, "accounts/notifications.html", {"items": items})


@login_required
@require_POST
def notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not n.read_at:
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
    return JsonResponse({"ok": True})


@login_required
def pulse(request):
    """Una sola consulta cada 25 s: mantiene la presencia y trae conectados y notificaciones nuevas."""
    touch(request, force=True)
    close_stale_sessions()  # sesiones abandonadas (navegador cerrado sin salir) se cierran solas
    try:
        after = int(request.GET.get("after") or 0)
    except ValueError:
        after = 0
    people = online_users()
    now = timezone.now()
    unread = request.user.notifications.filter(read_at__isnull=True)
    new_items = request.user.notifications.filter(pk__gt=after).order_by("-pk")[:10] if after else unread.order_by("-pk")[:10]
    data = {
        "server_time": now.isoformat(),
        "online": [{"id": str(p.pk), "name": p.get_full_name() or p.username, "initials": initials(p), "photo": _photo_url(p),
                    "position": p.position or "", "since": human(now - p.online_since), "me": p.pk == request.user.pk} for p in people],
        "unread": unread.count(),
        "notifications": [{"id": n.pk, "title": n.title, "body": n.body, "url": n.url, "kind": n.kind,
                           "created": n.created_at.isoformat(), "read": bool(n.read_at)} for n in new_items],
        "last_id": request.user.notifications.order_by("-pk").values_list("pk", flat=True).first() or 0,
    }
    if is_sgsi_admin(request.user):
        data["pending_requests"] = PasswordChangeRequest.objects.filter(status="pending").count()
    return JsonResponse(data)


# ---------------------------------------------------------------- administración de accesos
@admin_required
def access_list(request):
    request.session.pop("issued_credentials_xlsx", None)  # las contraseñas temporales no quedan guardadas
    close_stale_sessions()
    User = get_user_model()
    q = request.GET.get("q", "").strip()
    users = User.objects.all().prefetch_related("groups").order_by("-is_active", "first_name", "last_name")
    if q:
        users = users.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q) | Q(email__icontains=q) | Q(position__icontains=q))
    online_ids = {p.pk for p in online_users()}
    rows = []
    for u in users:
        rows.append({"u": u, "initials": initials(u), "online": u.pk in online_ids, "roles": [g.name for g in u.groups.all()],
                     "has_password": u.has_usable_password(), "time_30": human(connected_time(u, 30)) if u.last_seen_at else "—"})
    return render(request, "accounts/access_list.html", {
        "rows": rows, "q": q, "requests": PasswordChangeRequest.objects.filter(status="pending").select_related("user"),
        "roles": Group.objects.order_by("name"), "admin_role": ADMIN_ROLE,
        "stats": {"total": len(rows), "active": sum(1 for r in rows if r["u"].is_active),
                  "without_credentials": sum(1 for r in rows if not r["has_password"] and r["u"].is_active), "online": len(online_ids)},
    })


@admin_required
def access_user(request, pk):
    User = get_user_model()
    user = get_object_or_404(User, pk=pk)
    from apps.organization.models import Position, PositionAssignment

    if request.method == "POST":
        action = request.POST.get("action", "save")
        try:
            if action == "save":
                roles = set(request.POST.getlist("roles"))
                levels = {key: request.POST.get(f"mod_{key}", "none") for key, _, _ in available_modules()}
                changed = set_user_access(user, request.user, roles=roles, module_levels=levels, active=request.POST.get("active") == "1", request=request)
                messages.success(request, "Permisos guardados." if changed else "No hubo cambios en los permisos.")
            elif action == "position":
                _assign_position(request, user)
            elif action in ("photo", "remove_photo"):
                from .avatars import remove_avatar, save_avatar
                try:
                    if action == "remove_photo":
                        remove_avatar(user, request.user, request=request)
                        messages.success(request, "Foto retirada.")
                    elif request.FILES.get("photo"):
                        save_avatar(user, request.FILES["photo"], request.user, request=request)
                        messages.success(request, "Foto actualizada.")
                except ValidationError as exc:
                    messages.error(request, " ".join(exc.messages))
            elif action == "credentials":
                username, password = issue_credentials(user, request.user, request=request)
                request.session["issued_credentials"] = [{"name": user.get_full_name() or username, "username": username, "password": password}]
                return redirect("accounts:credentials_issued")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("accounts:access_user", pk=user.pk)

    current = PositionAssignment.objects.filter(user=user, end_date__isnull=True).select_related("position").first()
    sessions = list(UserSession.objects.filter(user=user)[:10])
    for s in sessions:
        s.duration_text = human(s.duration)
    return render(request, "accounts/access_user.html", {
        "u": user, "initials": initials(user), "roles": Group.objects.order_by("name"),
        "user_roles": set(user.groups.values_list("name", flat=True)), "modules": module_state(user),
        "positions": Position.objects.filter(is_active=True).select_related("area").order_by("title"),
        "current": current, "sessions": sessions, "admin_role": ADMIN_ROLE, "is_self": user == request.user,
        "time_30": human(connected_time(user, 30)),
    })


def _assign_position(request, user):
    from apps.organization.models import Position, PositionAssignment
    from apps.organization.services import assign_user_to_position, close_assignment

    position_id = request.POST.get("position", "")
    current = PositionAssignment.objects.filter(user=user, end_date__isnull=True, is_primary=True).first()
    if not position_id:
        if current:
            close_assignment(assignment=current, actor=request.user)
            messages.success(request, "Se retiró a la persona de su puesto en el organigrama.")
        return
    position = get_object_or_404(Position, pk=position_id, is_active=True)
    if current and current.position_id == position.pk:
        messages.info(request, "La persona ya ocupa ese puesto.")
        return
    taken = PositionAssignment.objects.filter(position=position, end_date__isnull=True).count()
    if position.max_occupants and taken >= position.max_occupants:
        raise ValueError(f"El puesto «{position.title}» ya está ocupado ({taken} de {position.max_occupants}).")
    try:
        assign_user_to_position(assignment=PositionAssignment(position=position, user=user, start_date=timezone.localdate(), is_primary=True), actor=request.user)
    except ValidationError as exc:
        raise ValueError(" ".join(exc.messages))
    from .security import notify
    notify([user], kind="organigrama", title=f"Te ubicaron en el puesto «{position.title}»",
           url=reverse("organization:chart"), actor=request.user)
    messages.success(request, f"Asignado al puesto «{position.title}».")


@admin_required
@require_POST
def access_bulk(request):
    User = get_user_model()
    ids = request.POST.getlist("users")
    action = request.POST.get("action")
    users = list(User.objects.filter(pk__in=ids))
    if not users:
        messages.error(request, "Marque al menos una persona.")
        return redirect("accounts:access_list")
    if action == "credentials":
        issued = []
        for u in users:
            username, password = issue_credentials(u, request.user, request=request)
            issued.append({"name": u.get_full_name() or username, "username": username, "password": password})
        request.session["issued_credentials"] = issued
        return redirect("accounts:credentials_issued")
    if action in ("activate", "deactivate"):
        changed = 0
        for u in users:
            if u == request.user and action == "deactivate":
                continue
            try:
                set_user_access(u, request.user, roles=set(u.groups.values_list("name", flat=True)),
                                module_levels={r["key"]: ("edit" if r["edit_direct"] else "view" if r["view_direct"] else "none") for r in module_state(u)},
                                active=action == "activate", request=request)
                changed += 1
            except ValueError as exc:
                messages.error(request, f"{u}: {exc}")
        messages.success(request, f"{changed} cuenta(s) actualizada(s).")
    return redirect("accounts:access_list")


@admin_required
def credentials_issued(request):
    """Muestra las contraseñas temporales UNA sola vez; al salir de esta página ya no se pueden ver."""
    issued = request.session.pop("issued_credentials", None)
    if request.GET.get("formato") == "xlsx":
        issued = request.session.pop("issued_credentials_xlsx", None)
        if not issued:
            messages.error(request, "Las credenciales solo se pueden descargar una vez, justo después de generarlas.")
            return redirect("accounts:access_list")
        return _credentials_xlsx(issued)
    if not issued:
        return redirect("accounts:access_list")
    request.session["issued_credentials_xlsx"] = issued
    return render(request, "accounts/credentials_issued.html", {"issued": issued, "login_url": request.build_absolute_uri(reverse("accounts:login"))})


def _credentials_xlsx(issued):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Credenciales"
    ws.append(["Colaborador", "Usuario", "Contraseña temporal"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for row in issued:
        ws.append([row["name"], row["username"], row["password"]])
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width, ws.column_dimensions["C"].width = 34, 18, 22
    ws.append([])
    ws.append(["Entregue cada contraseña solo a su titular. Al ingresar, el sistema pedirá cambiarla."])
    out = io.BytesIO()
    wb.save(out)
    response = HttpResponse(out.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="credenciales-temporales.xlsx"'
    response["Cache-Control"] = "no-store"
    return response


@admin_required
@require_POST
def password_request_resolve(request, pk):
    req = get_object_or_404(PasswordChangeRequest, pk=pk)
    approve = request.POST.get("decision") == "approve"
    try:
        password = resolve_password_request(req, request.user, approve, request.POST.get("note", ""), request=request)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("accounts:access_list")
    if approve:
        request.session["issued_credentials"] = [{"name": req.user.get_full_name() or req.user.username, "username": req.user.username, "password": password}]
        return redirect("accounts:credentials_issued")
    messages.success(request, "Solicitud rechazada; se avisó a la persona.")
    return redirect("accounts:access_list")
