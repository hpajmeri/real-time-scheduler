"""Rate Monotonic real-time scheduler."""

from __future__ import annotations

from typing import Dict, Sequence

from preemptive_priority_scheduler import (
    Job,
    PreemptivePriorityScheduler,
    PriorityKey,
    run_scheduler_cli,
)
from rt_scheduler import EPSILON


class RateMonotonicScheduler(PreemptivePriorityScheduler):
    def __init__(self, tasks: Sequence[Dict[str, float]]) -> None:
        super().__init__(tasks, name="rate_monotonic")

    def priority_key(self, job: Job) -> PriorityKey:
        task = self.original_tasks[job.task_id]
        return (task["period"], job.deadline, job.release_time, job.job_index)

    def feasibility_hint(self) -> bool:
        if self.task_count == 0:
            return True
        bound = self.task_count * ((2 ** (1 / self.task_count)) - 1)
        if self.utilization <= bound + EPSILON:
            return True
        return self.utilization <= 1.0 + EPSILON


def main(argv: Sequence[str] | None = None) -> int:
    return run_scheduler_cli(RateMonotonicScheduler, argv)


if __name__ == "__main__":
    raise SystemExit(main())
