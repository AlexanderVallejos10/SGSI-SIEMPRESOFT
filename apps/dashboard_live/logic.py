import re
from decimal import Decimal

from .models import MatrixType


def parse_indicator(indicator):
    text = (
        str(indicator or "")
        .replace("≤", "<=")
        .replace("≥", ">=")
        .replace(",", ".")
        .strip()
    )
    match = re.search(r"(<=|>=|=|<|>)?\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None, None
    operator = match.group(1) or ""
    target = Decimal(match.group(2))
    if not operator:
        operator = "=" if "%" in text and target == Decimal("100") else "<="
    return operator, target


def compliance(indicator, current_value):
    if current_value is None:
        return "NO"
    operator, target = parse_indicator(indicator)
    if operator is None:
        return ""
    current = Decimal(current_value)
    if operator == "<=":
        ok = current <= target
    elif operator == ">=":
        ok = current >= target
    elif operator == "<":
        ok = current < target
    elif operator == ">":
        ok = current > target
    else:
        ok = current == target
    return "SI" if ok else "NO"


def factor_summary(factors, matrix_type):
    rows = [item for item in factors if item.matrix_type == matrix_type]
    weight_sum = sum((item.weight for item in rows), Decimal("0"))
    score_sum = sum((item.score for item in rows), Decimal("0"))
    groups = {}
    for item in rows:
        groups.setdefault(item.group, Decimal("0"))
        groups[item.group] += item.score
    return {
        "rows": rows,
        "weight_sum": weight_sum,
        "score_sum": score_sum,
        "groups": groups,
        "weight_warning": weight_sum != Decimal("1"),
    }


def relation_score(alignments, objective):
    score = 0
    for item in alignments:
        if item.security_objective_id != objective.id:
            continue
        if item.relation == "P":
            score += 3
        elif item.relation == "S":
            score += 1
    return score
