"""Shared utility helpers for real-time scheduling."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

EPSILON: float = 1e-9


def gcd(a: float, b: float) -> float:
    """Compute the GCD for floating-point values with an epsilon tolerance."""
    a = abs(a)
    b = abs(b)
    while b > EPSILON:
        a, b = b, a % b
    return a


def lcm(a: float, b: float) -> float:
    """Compute the least common multiple for floating-point values."""
    return abs(a * b) / gcd(a, b) if a and b else 0.0


def calculate_hyperperiod(tasks: Iterable[Dict[str, float]]) -> float:
    """Calculate the hyperperiod across all task periods."""
    iterator = iter(tasks)
    try:
        first = next(iterator)
    except StopIteration:
        return 0.0
    hyperperiod = first["period"]
    for task in iterator:
        hyperperiod = lcm(hyperperiod, task["period"])
    return hyperperiod


def parse_workload_file(filepath: str | Path) -> List[Dict[str, float]]:
    """Parse a workload definition file into a list of task dictionaries."""
    path = Path(filepath)
    tasks: List[Dict[str, float]] = []
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 3:
            raise ValueError(f"Invalid line: {line}")
        execution, period, deadline = map(float, parts)
        tasks.append(
            {
                "execution": execution,
                "period": period,
                "deadline": deadline,
            }
        )
    return tasks


def calculate_total_utilization(tasks: Iterable[Dict[str, float]]) -> float:
    """Return the cumulative processor utilization for a task set."""
    return sum(task["execution"] / task["period"] for task in tasks)
