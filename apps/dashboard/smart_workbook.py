from decimal import Decimal, InvalidOperation

from apps.dashboard.models import (
    DashboardSnapshot,
    ObjectiveAlignment,
    SGSIMetric,
    SecurityObjective,
    StrategicFactor,
)


def _natural(value):
    import re

    return [
        int(part)
        if part.isdigit()
        else part.casefold()
        for part in re.split(
            r"(\d+)",
            str(value),
        )
    ]


def _display_value(raw, number_format):
    raw_text = str(raw or "").strip()

    if not raw_text:
        return "—"

    try:
        value = Decimal(raw_text)
    except InvalidOperation:
        return raw_text

    if "%" in str(number_format or ""):
        return (
            f"{(value * Decimal('100')):.2f}"
            .rstrip("0")
            .rstrip(".")
            + "%"
        )

    if value == value.to_integral():
        return str(
            value.to_integral()
        )

    return (
        f"{value:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def _matrix(snapshot, matrix_type):
    qs = (
        ObjectiveAlignment.objects
        .filter(
            snapshot=snapshot,
            matrix_type=matrix_type,
        )
        .order_by(
            "source_row",
            "objective_code",
        )
    )

    objective_codes = sorted(
        set(
            qs.values_list(
                "objective_code",
                flat=True,
            )
        ),
        key=_natural,
    )

    by_row = {}

    for item in qs:
        row = by_row.setdefault(
            item.source_row,
            {
                "source_row":
                    item.source_row,
                "source_code":
                    item.source_code,
                "source_group":
                    item.source_group,
                "description":
                    item.source_description,
                "cells": {},
            },
        )

        row["cells"][
            item.objective_code
        ] = item.relation_type

    return {
        "objective_codes":
            objective_codes,
        "rows": list(
            by_row.values()
        ),
    }


def get_smart_dashboard_context(
    artifact,
):
    snapshot = (
        DashboardSnapshot.objects
        .filter(
            source_artifact=artifact,
        )
        .order_by("-created_at")
        .first()
    )

    if snapshot is None:
        return None

    metrics = []

    for item in (
        SGSIMetric.objects
        .filter(snapshot=snapshot)
        .order_by("source_row")
    ):
        metrics.append(
            {
                "obj": item,
                "value": _display_value(
                    item.current_value_raw,
                    item.current_number_format,
                ),
                "compliance":
                    item.compliance_raw,
            }
        )

    objectives = []

    for item in (
        SecurityObjective.objects
        .filter(snapshot=snapshot)
        .order_by("source_row")
    ):
        objectives.append(
            {
                "obj": item,
                "value": _display_value(
                    item.current_value_raw,
                    item.current_number_format,
                ),
                "compliance":
                    item.compliance_raw,
            }
        )

    mefi = list(
        StrategicFactor.objects
        .filter(
            snapshot=snapshot,
            factor_type="internal",
        )
        .order_by("source_row")
    )

    mefe = list(
        StrategicFactor.objects
        .filter(
            snapshot=snapshot,
            factor_type="external",
        )
        .order_by("source_row")
    )

    return {
        "snapshot": snapshot,
        "metrics": metrics,
        "objectives": objectives,
        "oee": _matrix(
            snapshot,
            "oee_osi",
        ),
        "epi": _matrix(
            snapshot,
            "epi_osi",
        ),
        "mefi": mefi,
        "mefe": mefe,
    }
