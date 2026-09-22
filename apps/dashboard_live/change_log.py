from .models import DashboardChange


def log_changes(*, dataset, entity_type, entity_key, before, after, actor, trace_lookup):
    for field_name, old_value in before.items():
        new_value = after.get(field_name)
        if str(old_value if old_value is not None else "") == str(new_value if new_value is not None else ""):
            continue
        trace = trace_lookup.get(field_name)
        DashboardChange.objects.create(
            dataset=dataset,
            entity_type=entity_type,
            entity_key=str(entity_key),
            field_name=field_name,
            old_value="" if old_value is None else str(old_value),
            new_value="" if new_value is None else str(new_value),
            source_sheet=trace.source_sheet if trace else "",
            source_cell=trace.source_cell if trace else "",
            created_by=actor,
            updated_by=actor,
        )
