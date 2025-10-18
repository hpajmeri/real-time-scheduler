"""Bindings to the C-based Deadline Monotonic feasibility checker."""

from __future__ import annotations

import ctypes
import platform
import subprocess
from pathlib import Path
from typing import Sequence

_LIB_NAME_BY_PLATFORM = {
    "Darwin": "libdm_scheduler.dylib",
    "Linux": "libdm_scheduler.so",
}


def _library_path() -> Path:
    root = Path(__file__).resolve().parent
    lib_name = _LIB_NAME_BY_PLATFORM.get(platform.system(), "libdm_scheduler.so")
    return root / lib_name


def build_library(force: bool = False) -> Path:
    """Build the shared library if it is missing."""
    lib_path = _library_path()
    if lib_path.exists() and not force:
        return lib_path

    src = Path(__file__).resolve().parent / "dm_scheduler.c"
    system = platform.system()
    cmd = ["clang", "-O2", "-fPIC", str(src), "-o", str(lib_path)]
    if system == "Darwin":
        cmd.insert(1, "-dynamiclib")
    else:
        cmd.insert(1, "-shared")

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("clang is required to build the real-time scheduler library") from exc

    return lib_path


def _load_library() -> ctypes.CDLL:
    lib_path = build_library()
    lib = ctypes.CDLL(str(lib_path))
    lib.dm_response_time_feasible.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
    ]
    lib.dm_response_time_feasible.restype = ctypes.c_int
    return lib


def dm_schedulable_via_c(tasks: Sequence[dict]) -> bool:
    """Run the C implementation of RTA against a task set."""
    if not tasks:
        return True

    lib = _load_library()
    count = len(tasks)

    exec_arr = (ctypes.c_double * count)(*[_task_field(task, "execution") for task in tasks])
    period_arr = (ctypes.c_double * count)(*[_task_field(task, "period") for task in tasks])
    deadline_arr = (ctypes.c_double * count)(*[_task_field(task, "deadline") for task in tasks])

    result = lib.dm_response_time_feasible(exec_arr, period_arr, deadline_arr, ctypes.c_size_t(count))
    return bool(result)


def _task_field(task: dict, field: str) -> float:
    value = task.get(field)
    if value is None:
        raise ValueError(f"Task missing required field '{field}'")
    return float(value)
