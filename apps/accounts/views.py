from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import UserStatus
from .selectors import (
    get_user_areas,
    get_user_list,
    get_user_summary,
)


@login_required
@permission_required(
    "accounts.view_user",
    raise_exception=True,
)
def user_list(request):
    """
    MK-04 - Usuarios y accesos.

    La información se obtiene desde registros
    reales de PostgreSQL.
    """

    search = request.GET.get(
        "q",
        "",
    ).strip()

    area = request.GET.get(
        "area",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    queryset = get_user_list(
        search=search,
        area=area,
        status=status,
    )

    paginator = Paginator(
        queryset,
        15,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "page_obj": page_obj,

        "summary": (
            get_user_summary()
        ),

        "areas": (
            get_user_areas()
        ),

        "status_choices": (
            UserStatus.choices
        ),

        "filters": {
            "q": search,
            "area": area,
            "status": status,
        },
    }

    return render(
        request,
        "accounts/user_list.html",
        context,
    )