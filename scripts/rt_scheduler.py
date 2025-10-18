"""Compatibility wrapper around the packaged Deadline Monotonic scheduler."""

from __future__ import annotations

from typing import Sequence

from rt_scheduler.core.engine import run_scheduler_cli
from rt_scheduler.policies import DeadlineMonotonicScheduler


def main(argv: Sequence[str] | None = None) -> int:
    return run_scheduler_cli(DeadlineMonotonicScheduler, argv)


if __name__ == "__main__":
    raise SystemExit(main())
