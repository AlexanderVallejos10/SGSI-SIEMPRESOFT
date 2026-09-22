from apps.controls.models_iso import ISOClause


def sgsi_navigation(request):
    titles = {
        "4": "Contexto de la organización",
        "5": "Liderazgo",
        "6": "Planificación",
        "7": "Soporte",
        "8": "Operación",
        "9": "Evaluación del desempeño",
        "10": "Mejora",
    }

    menu = []

    for root, title in titles.items():
        children = list(
            ISOClause.objects
            .filter(
                code__startswith=f"{root}.",
                active=True,
            )
            .order_by("code")
            .values("code", "title")
        )

        children = [
            item
            for item in children
            if item["code"].count(".") == 1
        ]

        menu.append(
            {
                "code": root,
                "title": title,
                "children": children,
            }
        )

    return {
        "global_clause_menu": menu,
    }
