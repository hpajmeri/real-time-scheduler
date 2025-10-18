import sys
import math
import heapq
from typing import List, Dict, Tuple

EPSILON = 1e-9

def gcd(a: float, b: float) -> float:
    """Compute GCD for floating-point numbers with epsilon tolerance."""
    while b > EPSILON:
        a, b = b, a % b
    return a

def lcm(a: float, b: float) -> float:
    """Compute LCM for floating-point numbers."""
    return abs(a * b) / gcd(a, b) if a and b else 0

def calculate_hyperperiod(tasks: List[Dict]) -> float:
    """Calculate hyperperiod as LCM of all task periods."""
    if not tasks:
        return 0
    hyperperiod = tasks[0]["period"]
    for task in tasks[1:]:
        hyperperiod = lcm(hyperperiod, task["period"])
    return hyperperiod

def parse_workload_file(filepath: str) -> List[Dict]:
    tasks = []
    with open(filepath, 'r') as file:
        for line in file:
            if not line.strip():
                continue
            parts = line.strip().split(',')
            if len(parts) != 3:
                raise ValueError(f"Invalid line: {line}")
            execution, period, deadline = map(float, parts)
            tasks.append({
                "execution": execution,
                "period": period,
                "deadline": deadline
            })
    return tasks

def calculate_total_utilization(tasks: List[Dict]) -> float:
    return sum(task["execution"] / task["period"] for task in tasks)

def response_time_analysis(tasks: List[Dict]) -> bool:
    total_utilization = calculate_total_utilization(tasks)
    if total_utilization > 1.0:
        return False
    sorted_tasks = sorted(tasks, key=lambda x: x["deadline"])
    for i, task in enumerate(sorted_tasks):
        higher_priority = sorted_tasks[:i]
        t = sum(hp_task["execution"] for hp_task in higher_priority) + task["execution"]
        while True:
            interference = 0
            for hp_task in higher_priority:
                interference += math.ceil(t / hp_task["period"]) * hp_task["execution"]
            if interference + task["execution"] <= t:
                break
            new_t = interference + task["execution"]
            if new_t > task["deadline"]:
                return False
            if abs(new_t - t) < 1e-9:
                break
            t = new_t
        if t > task["deadline"]:
            return False
    return True

class Job:
    """Represents a single job instance of a task."""
    def __init__(self, task_id: int, release_time: float, execution_time: float, deadline: float):
        self.task_id = task_id
        self.release_time = release_time
        self.execution_time = execution_time
        self.remaining_time = execution_time
        self.deadline = deadline
        self.completed = False
        self.completion_time = None
    
    def __lt__(self, other):
        """Comparison for priority queue: lower deadline = higher priority."""
        if abs(self.deadline - other.deadline) > EPSILON:
            return self.deadline < other.deadline
        # Tiebreaker: earlier release time
        return self.release_time < other.release_time

class DeadlineMonotonicScheduler:
    """Deadline Monotonic scheduler with dual verification."""
    
    def __init__(self, tasks: List[Dict]):
        self.original_tasks = [dict(task) for task in tasks]
        # Sort tasks but keep track of original indices
        sorted_with_idx = sorted(enumerate(self.original_tasks), key=lambda x: x[1]["deadline"])
        self.tasks = [task for _, task in sorted_with_idx]
        # Maps: sorted position -> original index (for output mapping)
        self.sorted_to_orig = [orig_idx for orig_idx, _ in sorted_with_idx]
        self.hyperperiod = calculate_hyperperiod(self.tasks)
        self.preemption_counts = [0] * len(self.tasks)

    def generate_jobs(self, window: float) -> List[Job]:
        """Generate all job instances within the given time window."""
        jobs = []
        for task_id, task in enumerate(self.tasks):
            release_time = 0
            while release_time < window:
                absolute_deadline = release_time + task["deadline"]
                job = Job(task_id, release_time, task["execution"], absolute_deadline)
                jobs.append(job)
                release_time += task["period"]
        return jobs

    def _should_preempt(self, executing_job: Job, new_job: Job) -> bool:
        """Determine if new_job should preempt executing_job based on deadlines."""
        # Preempt if new job has strictly earlier deadline
        if new_job.deadline < executing_job.deadline - EPSILON:
            return True
        # If deadlines are equal, preempt (original had this logic)
        if abs(new_job.deadline - executing_job.deadline) < EPSILON:
            return True
        return False

    def simulate(self, window: float = None) -> Tuple[bool, List[int]]:
        """
        Event-driven simulation of Deadline Monotonic scheduling.
        Returns (feasible, preemption_counts_in_original_order)
        """
        if not self.tasks:
            return True, []
        
        # Determine simulation window
        if window is None:
            total_utilization = sum(t["execution"] / t["period"] for t in self.original_tasks)
            if total_utilization > 1.0 + EPSILON:
                return False, [0] * len(self.original_tasks)
            
            # Use heuristics for large hyperperiods
            if self.hyperperiod > 1e6:
                if not response_time_analysis(self.original_tasks):
                    return False, [0] * len(self.original_tasks)
                window = min(1e4, self.hyperperiod)
            else:
                window = self.hyperperiod
        
        # First-pass RTA verification
        if not response_time_analysis(self.original_tasks):
            return False, [0] * len(self.original_tasks)
        
        # Generate jobs for simulation window
        jobs = self.generate_jobs(window)
        if not jobs:
            return True, [0] * len(self.original_tasks)
        
        # Event-driven simulation
        current_time = 0.0
        ready_queue = []
        executing_job = None
        jobs_by_release = sorted(jobs, key=lambda j: j.release_time)
        job_idx = 0
        self.preemption_counts = [0] * len(self.tasks)
        completed_count = 0
        
        while completed_count < len(jobs):
            # Release jobs at current time
            while job_idx < len(jobs_by_release):
                job = jobs_by_release[job_idx]
                if job.release_time > current_time + EPSILON:
                    break
                heapq.heappush(ready_queue, job)
                job_idx += 1
            
            # Check for preemption
            if executing_job and ready_queue:
                highest_priority = ready_queue[0]
                if self._should_preempt(executing_job, highest_priority):
                    self.preemption_counts[executing_job.task_id] += 1
                    heapq.heappush(ready_queue, executing_job)
                    executing_job = None
            
            # Select next job to execute
            if not executing_job and ready_queue:
                executing_job = heapq.heappop(ready_queue)
            
            # Compute next event time
            next_release = jobs_by_release[job_idx].release_time if job_idx < len(jobs_by_release) else float('inf')
            next_completion = current_time + executing_job.remaining_time if executing_job else float('inf')
            next_event = min(next_release, next_completion)
            
            if next_event >= 1e20:  # No more events
                break
            
            # Execute for the time interval
            run_time = next_event - current_time
            if executing_job:
                executing_job.remaining_time -= run_time
            
            current_time = next_event
            
            # Check deadline violations
            for job in jobs:
                if not job.completed and job.release_time <= current_time + EPSILON:
                    if current_time > job.deadline + EPSILON:
                        return False, [0] * len(self.original_tasks)
            
            # Handle job completion
            if executing_job and executing_job.remaining_time < EPSILON:
                executing_job.completed = True
                executing_job.completion_time = current_time
                completed_count += 1
                executing_job = None
        
        # Verify all jobs completed
        if completed_count < len(jobs):
            return False, [0] * len(self.original_tasks)
        
        # Map preemption counts from sorted order back to original order
        output_counts = [0] * len(self.original_tasks)
        for sorted_idx, orig_idx in enumerate(self.sorted_to_orig):
            output_counts[orig_idx] = self.preemption_counts[sorted_idx]
        
        return True, output_counts

def main():
    if len(sys.argv) != 2:
        sys.exit(1)
    filepath = sys.argv[1]
    try:
        tasks = parse_workload_file(filepath)
        scheduler = DeadlineMonotonicScheduler(tasks)
        schedulable, preemption_counts = scheduler.simulate()
        if schedulable:
            print("1")
            print(",".join(map(str, preemption_counts)))
        else:
            print("0")
            print("")
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
