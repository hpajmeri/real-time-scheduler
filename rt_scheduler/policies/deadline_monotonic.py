"""Deadline Monotonic scheduler built on the shared preemptive engine."""

from __future__ import annotations

from typing import Dict, Sequence

from ..core.analysis import response_time_analysis
from ..core.engine import Job, PreemptivePriorityScheduler, PriorityKey, run_scheduler_cli


class DeadlineMonotonicScheduler(PreemptivePriorityScheduler):
    def __init__(self, tasks: Sequence[Dict[str, float]]) -> None:
        super().__init__(tasks, name="deadline_monotonic")

    def priority_key(self, job: Job, current_time: float) -> PriorityKey:
        task = self.original_tasks[job.task_id]
        return (task["deadline"], job.release_time, job.task_id, job.job_index)

    def feasibility_hint(self) -> bool:
        return response_time_analysis(self.original_tasks)


def main(argv: Sequence[str] | None = None) -> int:
    return run_scheduler_cli(DeadlineMonotonicScheduler, argv)


if __name__ == "__main__":
    raise SystemExit(main())
