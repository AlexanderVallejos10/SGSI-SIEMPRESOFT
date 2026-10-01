from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .busqueda import buscar, fuentes


@login_required
def sugerencias(request):
    texto = request.GET.get("q", "").strip()[:80]
    return JsonResponse({"q": texto, "grupos": buscar(request.user, texto, limite=4)})


@login_required
def resultados(request):
    texto = request.GET.get("q", "").strip()[:80]
    solo = request.GET.get("en") or None
    grupos = buscar(request.user, texto, limite=30 if solo else 8, solo=solo)
    titulos = {clave: titulo for clave, titulo, _, _ in fuentes()}
    return render(request, "busqueda/resultados.html", {
        "q": texto,
        "grupos": grupos,
        "solo": solo,
        "solo_titulo": titulos.get(solo, ""),
        "total": sum(len(g["items"]) for g in grupos),
    })
