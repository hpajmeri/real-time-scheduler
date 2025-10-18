# Real-Time Scheduler Suite

A production-grade collection of single-core real-time schedulers. The suite now includes:

- **Deadline Monotonic (DM)** — the original fixed-deadline simulator (`rt_scheduler.py`).
- **Rate Monotonic (RM)** — fixed-priority by period (`rate_monotonic_scheduler.py`).
- **Earliest Deadline First (EDF)** — optimal dynamic-priority scheduler (`edf_scheduler.py`).
- Shared preemptive engine and CLI helpers (`preemptive_priority_scheduler.py`, `rt_schedulers_extended.py`).

Each scheduler determines task-set feasibility and reports preemption/timeline data when requested.

## Problem

Real-time systems power critical infrastructure: aircraft autopilot, medical devices, industrial robotics. These systems must meet strict timing deadlines or fail catastrophically. Designing schedulable task sets requires sophisticated analysis—and mistakes are expensive.

**Question**: Given a set of periodic tasks with execution times, periods, and deadlines, can a CPU execute them all on time using fixed-priority scheduling?

This suite answers that question across multiple policies.

## Solution

The suite implements several canonical policies:

- **Deadline Monotonic (DM)** — fixed priority by relative deadline; optimal among fixed-deadline assignments.
- **Rate Monotonic (RM)** — fixed priority by period; optimal among fixed-period assignments.
- **Earliest Deadline First (EDF)** — dynamic priority by imminent deadline; optimal for uniprocessors when utilization ≤ 1.

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

- `rt_scheduler.py`: Original DM scheduler with dual verification
- `preemptive_priority_scheduler.py`: Shared event-driven engine and CLI harness
- `rate_monotonic_scheduler.py`: RM policy wrapper
- `edf_scheduler.py`: EDF policy wrapper
- `rt_schedulers_extended.py`: Policy dispatcher CLI (`python rt_schedulers_extended.py edf workloads/...`)
- `test_scheduler.py`: Legacy DM workload regression suite
- `test_*.py`: Unit tests for RM, EDF, and CLI integrations
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
# Deadline Monotonic (legacy)
python3 rt_scheduler.py workloads/workload1.txt

# Rate Monotonic
python3 rate_monotonic_scheduler.py workloads/workload1.txt --timeline

# Earliest Deadline First
python3 edf_scheduler.py workloads/workload1.txt

# Unified dispatcher (rm | edf)
python3 rt_schedulers_extended.py edf workloads/workload1.txt --timeline
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
python3 -m unittest -v
```

This covers DM legacy tests, RM/EDF unit modules, and CLI integrations.

---

**Status**: Production-ready. Optimized for performance, correctness, and policy flexibility.
