"""Real-time scheduling algorithms, policies, and native integrations."""

from . import policies
from .core.analysis import response_time_analysis
from .core.engine import (
    DeadlineMiss,
    Job,
    PreemptivePriorityScheduler,
    PriorityKey,
    ScheduleResult,
    TimelineSlice,
    run_scheduler_cli,
)
from .core.utils import (
    EPSILON,
    calculate_hyperperiod,
    calculate_total_utilization,
    parse_workload_file,
)
from .low_level import build_library as build_native_library, dm_schedulable_via_c

__all__ = [
    "DeadlineMiss",
    "EPSILON",
    "Job",
    "PreemptivePriorityScheduler",
    "PriorityKey",
    "ScheduleResult",
    "TimelineSlice",
    "build_native_library",
    "calculate_hyperperiod",
    "calculate_total_utilization",
    "dm_schedulable_via_c",
    "parse_workload_file",
    "policies",
    "response_time_analysis",
    "run_scheduler_cli",
]
