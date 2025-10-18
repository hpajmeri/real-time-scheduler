"""Earliest Deadline First real-time scheduler."""

from __future__ import annotations

from typing import Dict, Sequence

from preemptive_priority_scheduler import (
    Job,
    PreemptivePriorityScheduler,
    PriorityKey,
    run_scheduler_cli,
)
from rt_scheduler import EPSILON


class EarliestDeadlineFirstScheduler(PreemptivePriorityScheduler):
    def __init__(self, tasks: Sequence[Dict[str, float]]) -> None:
        super().__init__(tasks, name="earliest_deadline_first")

    def priority_key(self, job: Job) -> PriorityKey:
        return (job.deadline, job.release_time, job.task_id, job.job_index)

    def feasibility_hint(self) -> bool:
        return self.utilization <= 1.0 + EPSILON


def main(argv: Sequence[str] | None = None) -> int:
    return run_scheduler_cli(EarliestDeadlineFirstScheduler, argv)


if __name__ == "__main__":
    raise SystemExit(main())
