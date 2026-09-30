from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    AreaForm,
    PositionAssignmentForm,
    PositionForm,
    PositionMoveForm,
    QuickUserForm,
)
from .models import (
    OrganizationalArea,
    OrganizationRelationType,
    Position,
    PositionAssignment,
)
from .services import (
    assign_user_to_position,
    close_assignment,
    save_area,
)


User = get_user_model()


def _can_change(request):
    return (
        request.user.is_superuser
        or request.user.has_perm(
            "organization.change_position"
        )
    )


def _tree_node(position):
    active_assignments = list(
        position.assignments
        .filter(end_date__isnull=True)
        .select_related("user")
        .order_by(
            "-is_primary",
            "start_date",
        )
    )

    children = list(
        position.children
        .filter(is_active=True)
        .select_related("area")
        .order_by(
            "sort_order",
            "title",
        )
    )

    return {
        "position": position,
        "assignments": active_assignments,
        "children": [
            _tree_node(child)
            for child in children
        ],
        "color": position.effective_color,
    }


@login_required
def chart(request):
    roots = list(
        Position.objects
        .filter(
            parent__isnull=True,
            is_active=True,
        )
        .select_related("area")
        .order_by(
            "sort_order",
            "title",
        )
    )

    context = {
        "roots": [
            _tree_node(root)
            for root in roots
        ],
        "position_count": (
            Position.objects
            .filter(is_active=True)
            .count()
        ),
        "vacant_count": sum(
            1
            for position in Position.objects.filter(is_active=True)
            if position.is_vacant
        ),
        "area_count": (
            OrganizationalArea.objects
            .filter(is_active=True)
            .count()
        ),
        "unassigned_count": Position.objects.filter(is_active=True, area__isnull=True).count(),
        "areas": OrganizationalArea.objects.filter(is_active=True).order_by("name"),
        "can_change": _can_change(request),
    }

    return render(
        request,
        "organization/chart.html",
        context,
    )


@login_required
@transaction.atomic
def position_create(request):
    if not _can_change(request):
        raise PermissionDenied

    mode = request.GET.get(
        "mode",
        "root",
    )

    relative_id = request.GET.get(
        "relative",
    )

    relative = None

    if relative_id:
        relative = get_object_or_404(
            Position,
            pk=relative_id,
        )

    initial = {
        "relation_type":
            OrganizationRelationType.LINE,
        "sort_order": 100,
        "max_occupants": 1,
        "is_active": True,
    }

    area_id = request.GET.get("area")
    if area_id:
        try:
            initial["area"] = OrganizationalArea.objects.get(pk=area_id, is_active=True)
        except (ValidationError, OrganizationalArea.DoesNotExist):
            pass

    if relative is not None:
        if mode == "child":
            initial.update(
                {
                    "parent": relative,
                    "area": relative.area,
                    "sort_order": 100,
                }
            )
        elif mode == "sibling":
            initial.update(
                {
                    "parent": relative.parent,
                    "area": relative.area,
                    "relation_type":
                        relative.relation_type,
                    "sort_order":
                        relative.sort_order + 10,
                }
            )
        elif mode == "assistant":
            initial.update(
                {
                    "parent": relative,
                    "area": relative.area,
                    "relation_type":
                        OrganizationRelationType.ASSISTANT,
                    "sort_order": 900,
                }
            )

    if request.method == "POST":
        form = PositionForm(
            request.POST,
        )

        if form.is_valid():
            position = form.save(
                commit=False
            )
            position.created_by = request.user
            position.updated_by = request.user
            position.full_clean()
            position.save()

            messages.success(
                request,
                "Puesto creado. El nuevo cuadro ya forma parte del organigrama.",
            )

            return redirect(
                "organization:chart"
            )
    else:
        form = PositionForm(
            initial=initial
        )

    return render(
        request,
        "organization/position_form.html",
        {
            "form": form,
            "title": "Nuevo puesto",
            "mode": mode,
            "relative": relative,
        },
    )


@login_required
@transaction.atomic
def position_edit(
    request,
    pk,
):
    if not _can_change(request):
        raise PermissionDenied

    position = get_object_or_404(
        Position,
        pk=pk,
    )

    if request.method == "POST":
        form = PositionForm(
            request.POST,
            instance=position,
        )

        if form.is_valid():
            position = form.save(
                commit=False
            )
            position.updated_by = request.user
            position.full_clean()
            position.save()

            messages.success(
                request,
                "Puesto actualizado.",
            )

            return redirect(
                "organization:chart"
            )
    else:
        form = PositionForm(
            instance=position
        )

    return render(
        request,
        "organization/position_form.html",
        {
            "form": form,
            "title": f"Editar: {position.title}",
            "position": position,
        },
    )


@login_required
@transaction.atomic
def position_move(
    request,
    pk,
):
    if not _can_change(request):
        raise PermissionDenied

    position = get_object_or_404(
        Position,
        pk=pk,
    )

    if request.method == "POST":
        form = PositionMoveForm(
            request.POST,
            instance=position,
        )

        if form.is_valid():
            position = form.save(
                commit=False
            )
            position.updated_by = request.user
            position.full_clean()
            position.save()

            messages.success(
                request,
                "Puesto movido dentro de la jerarquía.",
            )

            return redirect(
                "organization:chart"
            )
    else:
        form = PositionMoveForm(
            instance=position
        )

    return render(
        request,
        "organization/position_form.html",
        {
            "form": form,
            "title": f"Mover: {position.title}",
            "position": position,
        },
    )


@login_required
def assign_user(
    request,
    pk,
):
    if not _can_change(request):
        raise PermissionDenied

    position = get_object_or_404(
        Position,
        pk=pk,
    )

    if request.method == "POST":
        form = PositionAssignmentForm(
            request.POST,
            position=position,
        )

        if form.is_valid():
            assignment = form.save(
                commit=False
            )
            assignment.position = position
            assignment.created_by = request.user
            assignment.updated_by = request.user

            try:
                assign_user_to_position(assignment=assignment, actor=request.user)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Usuario asignado al puesto.")
                return redirect("organization:chart")
    else:
        form = PositionAssignmentForm(
            position=position,
            initial={
                "start_date":
                    timezone.localdate(),
                "is_primary": True,
            },
        )

    return render(
        request,
        "organization/assignment_form.html",
        {
            "form": form,
            "position": position,
        },
    )


@login_required
def quick_user_create(
    request,
    pk,
):
    if not _can_change(request):
        raise PermissionDenied

    position = get_object_or_404(
        Position,
        pk=pk,
    )

    if request.method == "POST":
        form = QuickUserForm(
            request.POST,
            position=position,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    values = {
                        "username":
                            form.cleaned_data["username"],
                        "first_name":
                            form.cleaned_data["first_name"],
                        "last_name":
                            form.cleaned_data["last_name"],
                        "email":
                            form.cleaned_data["email"],
                    }

                    try:
                        User._meta.get_field(
                            "business_code"
                        )
                        values["business_code"] = (
                            form.cleaned_data[
                                "business_code"
                            ]
                        )
                    except Exception:
                        pass

                    user = User(
                        **values
                    )

                    if hasattr(user, "status"):
                        status_field = (
                            user._meta.get_field(
                                "status"
                            )
                        )

                        default = (
                            status_field.get_default()
                        )

                        if default not in (
                            None,
                            "",
                        ):
                            user.status = default

                    user.is_active = True
                    user.set_unusable_password()
                    user.save()

                    assignment = (
                        PositionAssignment(
                            position=position,
                            user=user,
                            start_date=(
                                form.cleaned_data[
                                    "start_date"
                                ]
                            ),
                            is_primary=True,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                    )

                    assign_user_to_position(
                        assignment=assignment,
                        actor=request.user,
                    )
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:

                messages.success(
                    request,
                    "Usuario creado y asignado al puesto.",
                )

                return redirect(
                    "organization:chart"
                )
    else:
        form = QuickUserForm(
            position=position,
            initial={
                "start_date":
                    timezone.localdate(),
            },
        )

    return render(
        request,
        "organization/quick_user_form.html",
        {
            "form": form,
            "position": position,
        },
    )


@login_required
def assignment_close(
    request,
    pk,
):
    if request.method != "POST":
        raise PermissionDenied

    if not _can_change(request):
        raise PermissionDenied

    assignment = get_object_or_404(
        PositionAssignment,
        pk=pk,
        end_date__isnull=True,
    )

    close_assignment(
        assignment=assignment,
        actor=request.user,
    )

    messages.success(
        request,
        "La asignación se cerró. El puesto queda disponible.",
    )

    return redirect(
        "organization:chart"
    )


@login_required
@transaction.atomic
def position_archive(
    request,
    pk,
):
    if request.method != "POST":
        raise PermissionDenied

    if not _can_change(request):
        raise PermissionDenied

    position = get_object_or_404(
        Position,
        pk=pk,
    )

    if position.children.filter(
        is_active=True
    ).exists():
        messages.error(
            request,
            "No se puede desactivar un puesto que aún tiene subordinados activos.",
        )

        return redirect(
            "organization:chart"
        )

    position.is_active = False
    position.updated_by = request.user
    position.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    for assignment in position.assignments.filter(
        end_date__isnull=True
    ):
        close_assignment(
            assignment=assignment,
            actor=request.user,
        )

    messages.success(
        request,
        "Puesto desactivado. Se conserva el historial.",
    )

    return redirect(
        "organization:chart"
    )


@login_required
def areas(request):
    area_list = (
        OrganizationalArea.objects
        .select_related("parent")
        .annotate(
            position_count=Count("positions", filter=Q(positions__is_active=True), distinct=True),
            member_count=Count("positions__assignments__user", filter=Q(
                positions__is_active=True, positions__assignments__end_date__isnull=True
            ), distinct=True),
        )
        .order_by(
            "sort_order",
            "name",
        )
    )

    return render(
        request,
        "organization/areas.html",
        {
            "areas": area_list,
            "can_change": _can_change(request),
            "unassigned_positions": Position.objects.filter(
                is_active=True, area__isnull=True
            ).select_related("parent").order_by("title"),
        },
    )


@login_required
def area_create(request):
    if not _can_change(request):
        raise PermissionDenied

    if request.method == "POST":
        form = AreaForm(
            request.POST
        )

        if form.is_valid():
            try:
                area = save_area(form=form, actor=request.user)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Área creada y puestos vinculados.")
                return redirect("organization:area_detail", pk=area.pk)
    else:
        form = AreaForm()

    return render(
        request,
        "organization/area_form.html",
        {
            "form": form,
            "title": "Nueva área",
        },
    )


@login_required
def area_edit(
    request,
    pk,
):
    if not _can_change(request):
        raise PermissionDenied

    area = get_object_or_404(
        OrganizationalArea,
        pk=pk,
    )

    if request.method == "POST":
        form = AreaForm(
            request.POST,
            instance=area,
        )

        if form.is_valid():
            try:
                area = save_area(form=form, actor=request.user)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Área actualizada y puestos vinculados.")
                return redirect("organization:area_detail", pk=area.pk)
    else:
        form = AreaForm(
            instance=area
        )

    return render(
        request,
        "organization/area_form.html",
        {
            "form": form,
            "title": f"Editar área: {area.name}",
            "area": area,
        },
    )


@login_required
def area_detail(request, pk):
    area = get_object_or_404(OrganizationalArea.objects.select_related("parent"), pk=pk)
    positions = list(area.positions.select_related("parent").prefetch_related(Prefetch(
        "assignments",
        queryset=PositionAssignment.objects.filter(end_date__isnull=True).select_related("user"),
        to_attr="active_assignments",
    )).order_by("-is_active", "sort_order", "title"))
    active = [position for position in positions if position.is_active]
    members = {assignment.user_id for position in active for assignment in position.active_assignments}
    return render(request, "organization/area_detail.html", {
        "area": area,
        "positions": positions,
        "position_count": len(active),
        "member_count": len(members),
        "vacant_count": sum(not position.active_assignments for position in active),
        "subareas": area.children.order_by("sort_order", "name"),
        "can_change": _can_change(request),
    })


def _safe_reverse(name, *args):
    from django.urls import NoReverseMatch

    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return ""


@login_required
def position_trace(request, pk):
    """Trazabilidad del puesto: cadena de mando, personas y de qué es responsable en el SGSI."""
    from django.http import JsonResponse

    from apps.processes.models import ProcessNode
    from apps.risks.models import Risk, RiskTreatment
    from apps.traceability.models import DocumentLink

    position = get_object_or_404(Position.objects.select_related("area", "parent"), pk=pk)
    assignments = list(position.assignments.filter(end_date__isnull=True).select_related("user"))
    users = [a.user for a in assignments]

    chain = []
    parent = position.parent
    while parent is not None and len(chain) < 20:
        chain.append({"id": str(parent.pk), "title": parent.title})
        parent = parent.parent

    owned = ProcessNode.objects.filter(owner_position=position).order_by("code")
    involved = ProcessNode.objects.filter(involved_positions=position).exclude(owner_position=position).order_by("code")
    map_url = _safe_reverse("processes:map")
    risks = (
        Risk.objects.filter(Q(owner_position=position) | Q(owner__in=users), is_active=True)
        .distinct()
        .order_by("code")
    )
    treatments = (
        RiskTreatment.objects.filter(responsible__in=users).select_related("risk").order_by("risk__code")
        if users else RiskTreatment.objects.none()
    )
    links = (
        DocumentLink.objects.filter(Q(position=position) | Q(user__in=users), is_active=True)
        .select_related("document")
        .order_by("kind", "source_title")
    )

    def doc_item(link):
        doc = link.document
        return {
            "title": doc.title if doc else link.source_title,
            "url": _safe_reverse("dashboard:document_detail", doc.pk) if doc else "",
            "verified": link.verified,
        }

    return JsonResponse({
        "id": str(position.pk),
        "title": position.title,
        "code": position.code,
        "area": position.area.name if position.area else "",
        "critical": position.is_critical,
        "chain": chain,
        "people": [
            {
                "name": a.user.get_full_name() or a.user.username,
                "code": getattr(a.user, "business_code", "") or a.user.username,
                "since": a.start_date.strftime("%d/%m/%Y") if a.start_date else "",
                "url": _safe_reverse("dashboard:user_profile", a.user.pk),
            }
            for a in assignments
        ],
        "reports": [
            {"id": str(c.pk), "title": c.title}
            for c in position.children.filter(is_active=True).order_by("sort_order", "title")
        ],
        "processes": [
            {"code": p.code, "name": p.name, "role": "Dueño", "url": map_url}
            for p in owned
        ] + [
            {"code": p.code, "name": p.name, "role": "Participa", "url": map_url}
            for p in involved
        ],
        "risks": [
            {
                "code": r.code,
                "name": (r.scenario or r.event or "")[:140],
                "process": r.process,
                "url": _safe_reverse("traceability:risk_edit", r.pk),
            }
            for r in risks[:60]
        ],
        "risk_total": risks.count(),
        "treatments": [
            {"risk": t.risk.code, "action": t.action[:140], "status": t.status, "due": t.due_date.strftime("%d/%m/%Y") if t.due_date else ""}
            for t in treatments[:60]
        ],
        "documents_owned": [doc_item(l) for l in links if l.kind == "owner"],
        "documents_access": [doc_item(l) for l in links if l.kind == "access"],
    })
