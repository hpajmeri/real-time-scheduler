"""Compatibility import for low-level bindings.

The actual implementation now lives in ``rt_scheduler.low_level``.
"""

from rt_scheduler.low_level import build_library, dm_schedulable_via_c

__all__ = ["build_library", "dm_schedulable_via_c"]
