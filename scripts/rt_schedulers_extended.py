"""Compatibility wrapper around the packaged CLI dispatcher."""

from __future__ import annotations

from typing import Iterable, Optional

from rt_scheduler.cli import build_scheduler, main as _main


def main(argv: Optional[Iterable[str]] = None) -> int:
    return _main(argv)


__all__ = ["build_scheduler", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
