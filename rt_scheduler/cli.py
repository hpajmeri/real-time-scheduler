"""Command-line dispatch utilities for the scheduler suite."""

from __future__ import annotations

import argparse
import sys
from typing import Dict, Iterable, Optional, Sequence, Type

from .core.engine import PreemptivePriorityScheduler
from .core.utils import parse_workload_file
from .policies import (
    DeadlineMonotonicScheduler,
    EarliestDeadlineFirstScheduler,
    LeastLaxityFirstScheduler,
    RateMonotonicScheduler,
)

POLICY_MAP: Dict[str, Type[PreemptivePriorityScheduler]] = {
    "dm": DeadlineMonotonicScheduler,
    "deadline_monotonic": DeadlineMonotonicScheduler,
    "rm": RateMonotonicScheduler,
    "rate_monotonic": RateMonotonicScheduler,
    "edf": EarliestDeadlineFirstScheduler,
    "earliest_deadline_first": EarliestDeadlineFirstScheduler,
    "llf": LeastLaxityFirstScheduler,
    "least_laxity_first": LeastLaxityFirstScheduler,
}


def build_scheduler(policy: str, tasks) -> PreemptivePriorityScheduler:
    try:
        factory = POLICY_MAP[policy.lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown scheduling policy '{policy}'") from exc
    return factory(tasks)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extended real-time schedulers")
    parser.add_argument("policy", help="Scheduling policy", choices=sorted(POLICY_MAP.keys()))
    parser.add_argument("workload", help="Path to workload file")
    parser.add_argument("--window", type=float, default=None, help="Override simulation window")
    parser.add_argument("--timeline", action="store_true", help="Emit execution slices")
    args = parser.parse_args(list(argv) if argv is not None else None)

    tasks = parse_workload_file(args.workload)
    scheduler = build_scheduler(args.policy, tasks)
    result = scheduler.simulate(window=args.window, include_timeline=args.timeline)

    if result.schedulable:
        print("1")
        print(",".join(map(str, result.preemptions)))
        if args.timeline:
            for slice_ in result.timeline:
                print(f"T{slice_.task_id}J{slice_.job_index}: {slice_.start:.6f}->{slice_.end:.6f}")
        return 0

    print("0")
    print("")
    if result.deadline_misses:
        miss = result.deadline_misses[0]
        print(
            f"Deadline miss on task {miss.task_id} job {miss.job_index} at {miss.miss_time:.6f}",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
