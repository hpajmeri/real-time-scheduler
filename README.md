# Real-Time Scheduler Suite

A production-grade reference implementation for single-core real-time scheduling. The project’s goal is to provide a single toolkit where researchers, educators, and practitioners can:

- Compare canonical policies under the same simulation and analysis pipeline.
- Study feasibility proofs versus empirical timelines with identical workloads.
- Capture instrumentation (preemptions, context switches, CPU/idle split) for performance studies.
- Prototype new policies by inheriting the shared engine rather than rebuilding scaffolding.

The suite ships with:

- **Deadline Monotonic (DM)** — fixed-deadline simulator (`rt_scheduler.policies.deadline_monotonic`).
- **Rate Monotonic (RM)** — fixed-priority by period (`rt_scheduler.policies.rate_monotonic`).
- **Earliest Deadline First (EDF)** — optimal dynamic-priority scheduler (`rt_scheduler.policies.earliest_deadline_first`).
- **Least Laxity First (LLF)** — adaptive laxity-driven scheduler (`rt_scheduler.policies.least_laxity_first`).
- Shared preemptive engine, CLI, and low-level bindings (`rt_scheduler.core`, `rt_scheduler.cli`, `rt_scheduler.low_level`).

Each scheduler determines task-set feasibility and reports preemption/timeline data when requested. Put differently: the “point” is to make it easy to answer *“can this task set meet its deadlines under policy X, and what does the execution trace look like?”* without rewriting engines or analysis code.

## Problem

Real-time systems power critical infrastructure: aircraft autopilot, medical devices, industrial robotics. These systems must meet strict timing deadlines or fail catastrophically. Designing schedulable task sets requires sophisticated analysis—and mistakes are expensive.

**Question**: Given a set of periodic tasks with execution times, periods, and deadlines, can a CPU execute them all on time using fixed-priority scheduling?

This suite answers that question across multiple policies.

## Solution

The suite implements several canonical policies:

- **Deadline Monotonic (DM)** — fixed priority by relative deadline; optimal among fixed-deadline assignments.
- **Rate Monotonic (RM)** — fixed priority by period; optimal among fixed-period assignments.
- **Earliest Deadline First (EDF)** — dynamic priority by imminent deadline; optimal for uniprocessors when utilization ≤ 1.

## Scheduler Deep Dive

### Deadline Monotonic (DM)

- **Priority semantics**: Static priority derived from each task's relative deadline; shorter deadline → higher priority.
- **Acceptance test**: Combines Liu & Layland utilization screen with exact Response Time Analysis (RTA). The Python RTA implementation is mirrored by an optional C backend (`rt_scheduler.low_level`) for deterministic latency on large task sets.
- **Simulation behavior**: Uses the shared preemptive engine with deterministic tie-breaking (deadline, release time, task id). Produces per-task preemption counts, context-switch totals, CPU/idle/overhead accounting.
- **Strengths**: Optimal within the space of fixed-deadline assignments; accurately models mixed criticality where deadlines differ from periods.
- **Limitations**: Requires deadline monotonic ordering; infeasible for deadline > period systems unless response-time convergence is reached.

### Rate Monotonic (RM)

- **Priority semantics**: Static priority equals task period (shorter period → higher priority). Harmonious with industry expectations for strictly periodic control loops.
- **Acceptance test**: Applies the classical utilization bound \(U_n = n(2^{1/n}-1)\), then falls back to DM's exact RTA for borderline cases. This two-phase filter keeps fast, sufficient checks while retaining completeness for near-saturated CPUs.
- **Simulation behavior**: Shares the DM engine but labels timeline slices with policy metadata. Outputs instrumentation fields used to diagnose jitter (timeline, context switches, CPU/idle/overhead time slices).
- **Strengths**: Predictable worst-case behavior for harmonic workloads; easy to reason about priority inversions.
- **Limitations**: Non-harmonic, highly-utilized task sets can pass the sufficient bound but still fail; jitter-sensitive systems may prefer EDF/LLF.

### Earliest Deadline First (EDF)

- **Priority semantics**: Dynamic priority equal to each job's absolute deadline at dispatch time. Queue reordering happens whenever a deadline changes or new job releases occur.
- **Acceptance test**: Utilization check (≤ 1.0 + ε) plus simulation; EDF is optimal on a single processor, so a utilization violation is a definitive failure. Simulation provides preemption/timeline data for instrumentation.
- **Strengths**: Offers 100% processor utilization for feasible sets; adapts gracefully to release jitter and sporadic arrivals modeled through workload files.
- **Limitations**: Requires run-time support for dynamic queue maintenance; high-frequency deadline churn increases context-switch counts, highlighted via instrumentation metrics.

### Least Laxity First (LLF)

- **Priority semantics**: Dynamic priority driven by laxity \(L = (deadline - now) - remaining\_time\). Jobs with shrinking slack preempt aggressively.
- **Acceptance test**: Pure simulation—LLF does not have a closed-form schedulability bound. The engine recalculates each job's priority on every dispatch, refreshing the heap to reflect new laxities.
- **Strengths**: Handles transient overload and deadline contractions by focusing CPU time on the most endangered jobs; useful for adversarial traces.
- **Limitations**: Sensitive to numeric noise near zero laxity; the implementation clamps at ε to avoid false negatives. Aggressive preemption can cause thrash, observable in the context-switch metric.

### Instrumentation & Diagnostics

- **Timeline reconstruction**: `TimelineSlice` captures every execution interval for offline visualization or jitter analysis.
- **Resource counters**: Each `ScheduleResult` exposes `context_switches`, `cpu_time`, `idle_time`, and `overhead_time`, enabling scheduling-cost studies.
- **Preemption accounting**: Per-task counters indicate priority inversions or thrashing hot spots.
- **Failure forensics**: When infeasible, the engine emits the first deadline miss (task id, job index, miss time), easing root-cause analysis across policies.

## Command-Line Interface

All interfaces funnel through `rt_scheduler.cli`, which exposes a single entry point with policy selection:

```bash
python3 -m rt_scheduler.cli <policy> <workload_path> [--window FLOAT] [--timeline]
```

| Argument | Description |
|----------|-------------|
| `policy` | One of `dm`, `deadline_monotonic`, `rm`, `rate_monotonic`, `edf`, `earliest_deadline_first`, `llf`, `least_laxity_first`. |
| `workload_path` | Path to a CSV-like workload file (three comma-separated floats per line: execution, period, deadline). |
| `--window` | Optional simulation horizon override (defaults to hyperperiod heuristic). |
| `--timeline` | Emit `T{task}J{job}: start->end` slices for visualization/trace replay. |

**Output format**

```
1
3,1,0
T0J0: 0.000000->1.000000
...
```

- First line: `1` if schedulable, `0` otherwise.
- Second line: comma-separated preemption counts per task (empty when infeasible).
- Optional timeline: emitted only when `--timeline` is set.
- Non-zero exit codes signal infeasibility (`2`) or runtime errors.

Legacy wrappers in `scripts/` (`rt_scheduler.py`, `rate_monotonic_scheduler.py`, etc.) simply forward to the module entry point for backward compatibility with older automation.

## Native C Response-Time Analysis

Module `rt_scheduler.low_level` accelerates Deadline Monotonic feasibility checks with a tiny C implementation:

- `build_library(force: bool = False) -> Path` builds (or rebuilds) `libdm_scheduler.{so|dylib}` using `clang`.
- `dm_schedulable_via_c(tasks: Sequence[dict]) -> bool` mirrors the Python `response_time_analysis`, returning `True` if the task set passes RTA.

Usage pattern:

```python
from rt_scheduler.low_level import build_library, dm_schedulable_via_c

build_library()  # no-op if the shared object already exists
is_feasible = dm_schedulable_via_c(tasks)
```

The Python layer automatically falls back to the pure-Python implementation when the shared object is absent; shipping the C code is about deterministic latency and parity with embedded toolchains.

Compiler expectations:

- Requires `clang` (or Apple’s Clang on macOS) in `PATH`.
- Produces position-independent code so the shared object loads via `ctypes`.
- Errors surface as `RuntimeError` with build output attached.

This module is optional but recommended for large task sets or tight benchmarking loops.

### Two Verification Methods

**Method 1: Response Time Analysis (RTA)**
- Mathematically analyze worst-case response times
- Fast: O(n²) complexity
- Catches infeasible task sets immediately

**Method 2: Event-Driven Simulation**  
- Execute jobs chronologically through a hyperperiod
- Accurate: Detects timing patterns RTA might miss
- Provides actual preemption counts

Both methods must agree. If either says "infeasible," the scheduler rejects the task set. RM reuses the same verification pipeline; EDF relies on utilization bound plus simulation.

## Why This Matters

Deadline Monotonic is **provably optimal**: if DM can't schedule your tasks, *no* fixed-priority algorithm can. EDF extends coverage to dynamic-priority systems, and RM offers the classic Liu & Layland baseline.

## Technical Approach

### Response Time Analysis

For each task, compute worst-case response time considering interference from higher-priority tasks. Solve iteratively until convergence. If response time ≤ deadline for all tasks, potentially feasible.

### Event-Driven Simulation

- Generate all job releases within hyperperiod H = LCM(P₀, ..., Pₙ)
- Maintain ready queue sorted by policy-specific priority
- At each time step: release new jobs → detect preemptions → execute highest-priority job
- Count preemptions per task
- Verify all deadlines met

### Floating-Point Precision

Task periods can be fractional (0.001, 0.05, etc.). LCM computation with epsilon tolerance (1e-9) ensures numeric stability.

## Implementation

**Core Components**:

- `rt_scheduler/core/engine.py`: Event-driven scheduler engine and CLI helpers
- `rt_scheduler/core/analysis.py`: Deadline Monotonic response-time analysis utilities
- `rt_scheduler/core/utils.py`: Workload parsing, hyperperiod/utilization helpers
- `rt_scheduler/policies/`: Concrete DM, RM, EDF, and LLF policy implementations
- `rt_scheduler/cli.py`: Unified command-line dispatcher (`python -m rt_scheduler.cli ...`)
- `rt_scheduler/low_level/`: C binding and build helpers for native response-time analysis checks
- Compatibility shims (`rt_scheduler.py`, `rate_monotonic_scheduler.py`, etc.) that forward to the package for legacy scripts
- `tests/`: Unit and CLI tests targeting the packaged modules
- `scripts/test_scheduler.py`: Legacy DM workload regression harness retained for workload sweeps
- `workloads/`: Test data directory with real-time workloads

## Example: Simple Task Set

**Three tasks**:
- Task A: execution=1ms, period=3ms, deadline=3ms
- Task B: execution=2ms, period=4ms, deadline=5ms  
- Task C: execution=1ms, period=5ms, deadline=5ms

**Step 1 - Assign Priorities**: By deadline: A > B > C
**Step 2 - Compute Hyperperiod**: LCM(3, 4, 5) = 60ms
**Step 3 - Verify Schedulability**: All tasks meet their deadlines

**Result**: Task set is schedulable.

## Real-World Applications

- **Avionics**: Flight control systems must meet microsecond deadlines
- **Automotive**: Engine control units coordinate fuel injection
- **Medical**: Pacemakers and insulin pumps run multiple periodic tasks
- **Industrial**: Robotic systems coordinate motion across multiple axes

## Design Insights

1. **Deadline Monotonic is elegant**: One sort implements years of scheduling theory
2. **Floating-point precision matters**: Epsilon tolerance is essential for correctness
3. **Hyperperiod explosion is real**: Coprime periods create astronomical LCMs
4. **Redundancy catches bugs**: Dual verification provides confidence
5. **Preemption patterns are subtle**: Only visible through full event-driven analysis

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Dual verification | RTA catches obvious infeasibility; simulation catches subtle patterns |
| Epsilon tolerance | Fractional periods require stable comparison |
| Hyperperiod heuristics | Large LCMs can exceed 10^12; fallback to RTA avoids timeout |
| Heap-based queue | O(log n) beats O(n log n) repeated sorting |
| Preemption on equal deadline | Original algorithm; implemented correctly |

## Getting Started

### CLI Usage

All commands print `1` on schedulable sets or `0` otherwise, followed by per-task preemption counts when applicable.

```bash
# Unified dispatcher (dm | rm | edf | llf)
python3 -m rt_scheduler.cli rm workloads/workload1.txt --timeline

# Policy-specific entry points remain for backward compatibility
python3 rt_scheduler.py workloads/workload1.txt
python3 rate_monotonic_scheduler.py workloads/workload1.txt
python3 edf_scheduler.py workloads/workload1.txt
python3 least_laxity_first_scheduler.py workloads/workload1.txt --timeline
```

Timeline slices are emitted as `T{task}J{job}: start->end` lines when `--timeline` is set.

## References

- Liu & Layland (1973) - Foundational scheduling paper
- Audsley et al. (1993) - Response Time Analysis framework
- Buttazzo (2011) - Real-Time Systems textbook

---

## Testing

Run targeted or full regression suites via:

```bash
python3 -m unittest discover tests -v
```

This covers DM legacy tests, RM/EDF unit modules, and CLI integrations.

---

**Status**: Production-ready. Optimized for performance, correctness, and policy flexibility.
