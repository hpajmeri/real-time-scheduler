"""Least Laxity First (LLF) dynamic-priority scheduler."""

from __future__ import annotations

from typing import Dict, Sequence

from ..core.engine import Job, PreemptivePriorityScheduler, PriorityKey, run_scheduler_cli


class LeastLaxityFirstScheduler(PreemptivePriorityScheduler):
    def __init__(self, tasks: Sequence[Dict[str, float]]) -> None:
        super().__init__(tasks, name="least_laxity_first")

    def priority_key(self, job: Job, current_time: float) -> PriorityKey:
        laxity = (job.deadline - current_time) - job.remaining_time
        return (laxity, job.deadline, job.release_time, job.job_index)

    def dynamic_priority(self) -> bool:
        return True


def main(argv: Sequence[str] | None = None) -> int:
    return run_scheduler_cli(LeastLaxityFirstScheduler, argv)


if __name__ == "__main__":
    raise SystemExit(main())
