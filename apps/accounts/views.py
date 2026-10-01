from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def user_list(request):
    return redirect("dashboard:entity_list", entity="usuarios")
