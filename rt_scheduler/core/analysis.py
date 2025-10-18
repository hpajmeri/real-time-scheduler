"""Analysis helpers for schedulability checks."""

from __future__ import annotations

import math
from typing import Dict, Iterable

from .utils import EPSILON, calculate_total_utilization


def response_time_analysis(tasks: Iterable[Dict[str, float]]) -> bool:
    """Return whether a task set is feasible under Deadline Monotonic scheduling."""
    tasks_list = list(tasks)
    if not tasks_list:
        return True

    total_utilization = calculate_total_utilization(tasks_list)
    if total_utilization > 1.0 + EPSILON:
        return False

    ordered = sorted(tasks_list, key=lambda task: task["deadline"])
    for index, task in enumerate(ordered):
        higher_priority = ordered[:index]
        completion = sum(item["execution"] for item in higher_priority) + task["execution"]
        while True:
            interference = 0.0
            for hp in higher_priority:
                interference += math.ceil(completion / hp["period"]) * hp["execution"]
            if interference + task["execution"] <= completion + EPSILON:
                break
            new_completion = interference + task["execution"]
            if new_completion > task["deadline"] + EPSILON:
                return False
            if abs(new_completion - completion) <= EPSILON:
                break
            completion = new_completion
        if completion > task["deadline"] + EPSILON:
            return False
    return True
