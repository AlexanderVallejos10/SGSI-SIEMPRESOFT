from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
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
        "can_change": _can_change(request),
    }

    return render(
        request,
        "organization/chart.html",
        context,
    )


@login_required
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

            assign_user_to_position(
                assignment=assignment,
                actor=request.user,
            )

            messages.success(
                request,
                "Usuario asignado al puesto.",
            )

            return redirect(
                "organization:chart"
            )
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

                if hasattr(user, "position"):
                    user.position = (
                        position.title
                    )

                if (
                    hasattr(user, "area")
                    and position.area_id
                ):
                    user.area = (
                        position.area.name
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
    if not _can_change(request):
        raise PermissionDenied

    area_list = (
        OrganizationalArea.objects
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
            area = form.save(
                commit=False
            )
            area.created_by = request.user
            area.updated_by = request.user
            area.save()

            messages.success(
                request,
                "Área creada.",
            )

            return redirect(
                "organization:areas"
            )
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
            area = form.save(
                commit=False
            )
            area.updated_by = request.user
            area.save()

            messages.success(
                request,
                "Área actualizada.",
            )

            return redirect(
                "organization:areas"
            )
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
        },
    )
