"""Event-driven engine for preemptive priority schedulers."""

from __future__ import annotations

import argparse
import heapq
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .utils import EPSILON, calculate_hyperperiod, calculate_total_utilization, parse_workload_file

MAX_SIM_WINDOW = 1e5


@dataclass
class Job:
    task_id: int
    job_index: int
    release_time: float
    execution_time: float
    deadline: float
    remaining_time: float = field(init=False)
    completion_time: Optional[float] = None

    def __post_init__(self) -> None:
        self.remaining_time = self.execution_time


@dataclass
class TimelineSlice:
    task_id: int
    job_index: int
    start: float
    end: float


@dataclass
class DeadlineMiss:
    task_id: int
    job_index: int
    miss_time: float


@dataclass
class ScheduleResult:
    schedulable: bool
    preemptions: List[int]
    timeline: List[TimelineSlice]
    deadline_misses: List[DeadlineMiss]
    utilization: float
    context_switches: int
    cpu_time: float
    idle_time: float
    overhead_time: float

    def __bool__(self) -> bool:
        return self.schedulable


PriorityKey = Tuple[float, float, int, int]


class PreemptivePriorityScheduler:
    """Shared event-driven engine for priority schedulers."""

    def __init__(self, tasks: Sequence[Dict[str, float]], *, name: str, context_switch_cost: float = 0.0) -> None:
        self.name = name
        self.original_tasks = [dict(task) for task in tasks]
        self.task_count = len(self.original_tasks)
        self.hyperperiod = calculate_hyperperiod(self.original_tasks)
        self.utilization = calculate_total_utilization(self.original_tasks)
        self.context_switch_cost = max(0.0, context_switch_cost)
        self._validate_tasks()

    def priority_key(self, job: Job, current_time: float) -> PriorityKey:
        raise NotImplementedError

    def feasibility_hint(self) -> bool:
        return True

    def dynamic_priority(self) -> bool:
        return False

    def simulate(
        self,
        window: Optional[float] = None,
        *,
        include_timeline: bool = False,
    ) -> ScheduleResult:
        if self.task_count == 0:
            return ScheduleResult(True, [], [], [], 0.0, 0, 0.0, 0.0, 0.0)

        if not self.feasibility_hint():
            miss = DeadlineMiss(task_id=-1, job_index=-1, miss_time=0.0)
            return ScheduleResult(False, [0] * self.task_count, [], [miss], self.utilization, 0, 0.0, 0.0, 0.0)

        horizon = self._choose_window(window)
        jobs = self._generate_jobs(horizon)
        if not jobs:
            return ScheduleResult(True, [0] * self.task_count, [], [], self.utilization, 0, 0.0, 0.0, 0.0)

        ready_queue: List[Tuple[PriorityKey, int, Job]] = []
        jobs_by_release = sorted(jobs, key=lambda j: (j.release_time, j.task_id, j.job_index))
        job_release_index = 0
        executing: Optional[Job] = None
        preemptions = [0] * self.task_count
        timeline: List[TimelineSlice] = []
        deadline_misses: List[DeadlineMiss] = []
        sequence = 0
        current_time = 0.0
        segment_start: Optional[float] = None
        completed_jobs = 0
        context_switches = 0
        cpu_time = 0.0
        idle_time = 0.0
        overhead_time = 0.0
        last_task_id: Optional[int] = None

        while completed_jobs < len(jobs):
            if executing is None and not ready_queue and job_release_index < len(jobs_by_release):
                jump_time = jobs_by_release[job_release_index].release_time
                if jump_time > current_time + EPSILON:
                    idle_time += jump_time - current_time
                    current_time = jump_time

            while (
                job_release_index < len(jobs_by_release)
                and jobs_by_release[job_release_index].release_time <= current_time + EPSILON
            ):
                job = jobs_by_release[job_release_index]
                heapq.heappush(ready_queue, (self.priority_key(job, current_time), sequence, job))
                sequence += 1
                job_release_index += 1

            if self.dynamic_priority() and ready_queue:
                sequence = self._refresh_ready_queue(ready_queue, current_time, sequence)

            if executing is not None and ready_queue:
                exec_key = self.priority_key(executing, current_time)
                top_key, _, top_job = ready_queue[0]
                if self._key_less(top_key, exec_key) or (
                    self._keys_close(top_key, exec_key) and self._job_preempts(top_job, executing)
                ):
                    if include_timeline and segment_start is not None and current_time > segment_start + EPSILON:
                        timeline.append(
                            TimelineSlice(
                                task_id=executing.task_id,
                                job_index=executing.job_index,
                                start=segment_start,
                                end=current_time,
                            )
                        )
                    heapq.heappush(ready_queue, (exec_key, sequence, executing))
                    sequence += 1
                    preemptions[executing.task_id] += 1
                    executing = None
                    segment_start = None

            if executing is None and ready_queue:
                _, _, executing = heapq.heappop(ready_queue)
                if last_task_id is None or last_task_id != executing.task_id:
                    context_switches += 1
                    overhead_time += self.context_switch_cost
                last_task_id = executing.task_id
                segment_start = current_time

            next_release = (
                jobs_by_release[job_release_index].release_time
                if job_release_index < len(jobs_by_release)
                else float("inf")
            )
            next_completion = (
                current_time + executing.remaining_time if executing is not None else float("inf")
            )
            next_event = min(next_release, next_completion)
            if next_event == float("inf"):
                break

            run_time = max(0.0, next_event - current_time)
            if executing is not None and run_time > 0:
                executing.remaining_time -= run_time
                cpu_time += run_time
            elif run_time > 0:
                idle_time += run_time
            current_time = next_event

            for job in jobs:
                if job.completion_time is None and current_time > job.deadline + EPSILON:
                    deadline_misses.append(
                        DeadlineMiss(job.task_id, job.job_index, current_time)
                    )
            if deadline_misses:
                if (
                    include_timeline
                    and executing is not None
                    and segment_start is not None
                    and current_time > segment_start + EPSILON
                ):
                    timeline.append(
                        TimelineSlice(
                            task_id=executing.task_id,
                            job_index=executing.job_index,
                            start=segment_start,
                            end=current_time,
                        )
                    )
                return ScheduleResult(
                    False,
                    preemptions,
                    timeline if include_timeline else [],
                    deadline_misses,
                    self.utilization,
                    context_switches,
                    cpu_time,
                    idle_time,
                    overhead_time,
                )

            if executing is not None and executing.remaining_time <= EPSILON:
                executing.completion_time = current_time
                if segment_start is not None and include_timeline:
                    timeline.append(
                        TimelineSlice(
                            task_id=executing.task_id,
                            job_index=executing.job_index,
                            start=segment_start,
                            end=current_time,
                        )
                    )
                executing = None
                segment_start = None
                completed_jobs += 1

        return ScheduleResult(
            True,
            preemptions,
            timeline if include_timeline else [],
            deadline_misses,
            self.utilization,
            context_switches,
            cpu_time,
            idle_time,
            overhead_time,
        )

    def _generate_jobs(self, window: float) -> List[Job]:
        jobs: List[Job] = []
        for task_id, task in enumerate(self.original_tasks):
            release = 0.0
            job_index = 0
            while release <= window + EPSILON:
                deadline = release + task["deadline"]
                jobs.append(Job(task_id, job_index, release, task["execution"], deadline))
                release += task["period"]
                job_index += 1
        return jobs

    def _choose_window(self, window_override: Optional[float]) -> float:
        if window_override is not None and window_override > 0:
            return window_override

        candidate = self.hyperperiod if 0 < self.hyperperiod < MAX_SIM_WINDOW else 0.0
        max_deadline = max(task["deadline"] for task in self.original_tasks)
        total_period = sum(task["period"] for task in self.original_tasks)
        window = candidate or max(max_deadline, total_period)
        return min(max(window, max_deadline), MAX_SIM_WINDOW)

    @staticmethod
    def _key_less(left: PriorityKey, right: PriorityKey) -> bool:
        for lval, rval in zip(left, right):
            if isinstance(lval, float) or isinstance(rval, float):
                if abs(lval - rval) <= EPSILON:
                    continue
                return lval < rval
            if lval == rval:
                continue
            return lval < rval
        return False

    @staticmethod
    def _keys_close(a: PriorityKey, b: PriorityKey) -> bool:
        for aval, bval in zip(a, b):
            if isinstance(aval, float) or isinstance(bval, float):
                if abs(aval - bval) > EPSILON:
                    return False
            else:
                if aval != bval:
                    return False
        return True

    @staticmethod
    def _job_preempts(candidate: Job, incumbent: Job) -> bool:
        return (candidate.release_time, candidate.task_id, candidate.job_index) < (
            incumbent.release_time,
            incumbent.task_id,
            incumbent.job_index,
        )

    def _refresh_ready_queue(
        self,
        ready_queue: List[Tuple[PriorityKey, int, Job]],
        current_time: float,
        sequence: int,
    ) -> int:
        if not ready_queue:
            return sequence
        items = [entry[2] for entry in ready_queue]
        ready_queue.clear()
        for job in items:
            heapq.heappush(ready_queue, (self.priority_key(job, current_time), sequence, job))
            sequence += 1
        return sequence

    def _validate_tasks(self) -> None:
        for idx, task in enumerate(self.original_tasks):
            if task["execution"] <= 0 or task["period"] <= 0 or task["deadline"] <= 0:
                raise ValueError(f"Task {idx} has non-positive parameters: {task}")


def run_scheduler_cli(
    factory: Callable[[Sequence[Dict[str, float]]], PreemptivePriorityScheduler],
    argv: Optional[Iterable[str]] = None,
) -> int:
    parser = argparse.ArgumentParser(description="Real-time scheduler CLI")
    parser.add_argument("workload", help="Path to workload file")
    parser.add_argument(
        "--window",
        type=float,
        default=None,
        help="Optional simulation window override",
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="Emit execution slices for visualization",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    tasks = parse_workload_file(args.workload)
    scheduler = factory(tasks)
    result = scheduler.simulate(window=args.window, include_timeline=args.timeline)

    if result.schedulable:
        print("1")
        print(",".join(map(str, result.preemptions)))
        if args.timeline:
            for slice_ in result.timeline:
                print(
                    f"T{slice_.task_id}J{slice_.job_index}: {slice_.start:.6f}->{slice_.end:.6f}",
                    file=sys.stdout,
                )
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
