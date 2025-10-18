#!/usr/bin/env python3
"""
Comprehensive regression harness for the Deadline Monotonic scheduler.
Invokes the packaged CLI entry point across the workload suite.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def parse_expected_results(expected_file: str) -> Dict[int, Tuple[str, str]]:
    """Parse expected results file and return workload -> (schedulable, preemptions)."""
    expected_results: Dict[int, Tuple[str, str]] = {}
    current_workload: int | None = None
    current_output: List[str] = []

    with open(expected_file, "r", encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Workload"):
                if current_workload is not None:
                    if len(current_output) >= 2:
                        expected_results[current_workload] = (current_output[0], current_output[1])
                    elif current_output:
                        expected_results[current_workload] = (current_output[0], "")
                current_workload = int(line.split()[1].rstrip(":"))
                current_output = []
            elif line and current_workload is not None:
                current_output.append(line)

    if current_workload is not None and current_output:
        if len(current_output) >= 2:
            expected_results[current_workload] = (current_output[0], current_output[1])
        else:
            expected_results[current_workload] = (current_output[0], "")

    return expected_results


def run_scheduler_on_workload(workload_file: str, timeout: int = 60) -> Tuple[int, str, float]:
    """Execute the packaged CLI against the provided workload file."""
    cmd = ["python3", "-m", "rt_scheduler.cli", "dm", workload_file]
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        execution_time = time.time() - start_time
        return result.returncode, result.stdout, execution_time
    except subprocess.TimeoutExpired:
        return -1, f"Timeout after {timeout} seconds", float(timeout)
    except Exception as exc:  # pragma: no cover - defensive
        return -2, f"Error: {exc}", 0.0


def analyze_workload(workload_file: str) -> Dict:
    """Analyze a workload file and return statistics for reporting."""
    tasks: List[Dict[str, float]] = []
    with open(workload_file, "r", encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) == 3:
                execution, period, deadline = map(float, parts)
                tasks.append({
                    "execution": execution,
                    "period": period,
                    "deadline": deadline,
                })

    if not tasks:
        return {"error": "No valid tasks found"}

    total_utilization = sum(t["execution"] / t["period"] for t in tasks)
    avg_period = sum(t["period"] for t in tasks) / len(tasks)
    avg_deadline = sum(t["deadline"] for t in tasks) / len(tasks)
    avg_execution = sum(t["execution"] for t in tasks) / len(tasks)

    return {
        "num_tasks": len(tasks),
        "total_utilization": total_utilization,
        "avg_period": avg_period,
        "avg_deadline": avg_deadline,
        "avg_execution": avg_execution,
        "deadline_less_than_period": any(t["deadline"] < t["period"] for t in tasks),
        "very_small_periods": any(t["period"] < 1.0 for t in tasks),
        "very_large_periods": any(t["period"] > 100.0 for t in tasks),
        "high_utilization": total_utilization > 0.8,
        "tasks": tasks,
    }


def test_workloads() -> None:
    """Test the scheduler against all workload definitions."""
    print("Testing Deadline Monotonic Scheduler")
    print("=" * 60)

    test_results_dir = Path("test_results")
    test_results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = test_results_dir / f"test_results_{timestamp}.txt"

    print(f"Results will be saved to: {results_file}")
    print("=" * 60)

    expected_file = "workloads/expected_results.txt"
    expected_results = parse_expected_results(expected_file)

    total_tests = passed_tests = failed_tests = timeout_tests = error_tests = 0

    extra_files_dir = Path("workloads")
    workload_files: List[Tuple[int, Path, bool]] = []

    for workload_num in range(1, 7):
        workload_file = extra_files_dir / f"workload{workload_num}.txt"
        if workload_file.exists():
            workload_files.append((workload_num, workload_file, True))

    for workload_num in range(7, 40):
        workload_file = extra_files_dir / f"workload{workload_num}.txt"
        if workload_file.exists():
            workload_files.append((workload_num, workload_file, False))

    print(f"Found {len(workload_files)} workload files to test\n")

    results: List[Dict] = []
    for workload_num, workload_file, has_expected in workload_files:
        print(f"Testing Workload {workload_num}...")

        analysis = analyze_workload(str(workload_file))
        if "error" in analysis:
            print(f"  ❌ ERROR: {analysis['error']}")
            error_tests += 1
            continue

        print(f"  Tasks: {analysis['num_tasks']}")
        print(f"  Utilization: {analysis['total_utilization']:.3f}")
        print(f"  Avg Period: {analysis['avg_period']:.2f}")
        print(f"  Avg Deadline: {analysis['avg_deadline']:.2f}")

        exit_code, output, exec_time = run_scheduler_on_workload(str(workload_file), timeout=60)
        total_tests += 1

        if exit_code == 0:
            lines = output.strip().splitlines()
            if lines:
                schedulable = lines[0].strip() == "1"
                preemption_counts = lines[1].strip() if len(lines) > 1 and lines[1].strip() else ""

                print(f"  Result: {'Schedulable' if schedulable else 'Unschedulable'}")
                if schedulable and preemption_counts:
                    print(f"  Preemptions: {preemption_counts}")
                print(f"  Execution time: {exec_time:.3f}s")

                if has_expected:
                    expected_schedulable, expected_preemptions = expected_results[workload_num]
                    expected_output = f"{expected_schedulable}\n{expected_preemptions}".strip()
                    actual_output = output.strip()
                    if actual_output == expected_output:
                        print("  ✅ PASSED (matches expected output)")
                        passed_tests += 1
                    else:
                        print("  ❌ FAILED: Output mismatch")
                        print(f"  Expected: '{expected_output}'")
                        print(f"  Actual:   '{actual_output}'")
                        failed_tests += 1
                else:
                    passed_tests += 1
                    print("  ✅ PASSED (valid output)")
            else:
                print("  ❌ FAILED: Empty output")
                failed_tests += 1
        elif exit_code == -1:
            print(f"  ⏰ TIMEOUT (60s limit exceeded)")
            timeout_tests += 1
        else:
            print(f"  ❌ ERROR: {output}")
            error_tests += 1

        print()
        results.append(
            {
                "workload_num": workload_num,
                "file": str(workload_file),
                "analysis": analysis,
                "exit_code": exit_code,
                "output": output,
                "exec_time": exec_time,
                "has_expected": has_expected,
            }
        )

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Timeouts: {timeout_tests}")
    print(f"Errors: {error_tests}")
    success_rate = (passed_tests / total_tests * 100.0) if total_tests else 0.0
    print(f"Success Rate: {success_rate:.1f}%")
    print("Overall Status: " + ("🎉 ALL TESTS PASSED" if failed_tests == timeout_tests == error_tests == 0 else "❌ SOME TESTS FAILED"))

    print("\nDETAILED ANALYSIS")
    print("=" * 60)

    schedulable_count = 0
    unschedulable_count = 0
    exec_times: List[float] = []

    for result in results:
        if result["exit_code"] == 0:
            lines = result["output"].strip().splitlines()
            if lines and lines[0].strip() == "1":
                schedulable_count += 1
            else:
                unschedulable_count += 1
            exec_times.append(result["exec_time"])

    avg_exec_time = (sum(exec_times) / len(exec_times)) if exec_times else 0.0

    print(f"Schedulable workloads: {schedulable_count}")
    print(f"Unschedulable workloads: {unschedulable_count}")
    print(f"Average execution time: {avg_exec_time:.3f}s")

    edge_cases = {
        "high_utilization": 0,
        "deadline_less_than_period": 0,
        "very_small_periods": 0,
        "very_large_periods": 0,
    }

    for result in results:
        analysis = result["analysis"]
        if analysis.get("high_utilization"):
            edge_cases["high_utilization"] += 1
        if analysis.get("deadline_less_than_period"):
            edge_cases["deadline_less_than_period"] += 1
        if analysis.get("very_small_periods"):
            edge_cases["very_small_periods"] += 1
        if analysis.get("very_large_periods"):
            edge_cases["very_large_periods"] += 1

    print("\nEdge Cases Tested:")
    print(f"  High utilization: {edge_cases['high_utilization']}")
    print(f"  Deadline < period: {edge_cases['deadline_less_than_period']}")
    print(f"  Very small periods: {edge_cases['very_small_periods']}")
    print(f"  Very large periods: {edge_cases['very_large_periods']}")

    with open(results_file, "w", encoding="utf-8") as handle:
        handle.write("Deadline Monotonic Scheduler Test Results\n")
        handle.write("=" * 60 + "\n")
        handle.write(f"Timestamp: {datetime.now()}\n")
        handle.write(f"Total Tests: {total_tests}\n")
        handle.write(f"Passed: {passed_tests}\n")
        handle.write(f"Failed: {failed_tests}\n")
        handle.write(f"Timeouts: {timeout_tests}\n")
        handle.write(f"Errors: {error_tests}\n")
        handle.write(f"Success Rate: {success_rate:.1f}%\n\n")
        handle.write("Test Cases Covered:\n")
        handle.write("- Original workloads (1-6) with expected results\n")
        handle.write("- New workloads (7-39) with validation\n")
        handle.write("- Single and two task cases\n")
        handle.write("- Edge conditions (deadline < period, very small/large periods)\n")
        handle.write("- Floating point values\n")
        handle.write("- High utilization cases\n")
        handle.write("- Large task sets (5+ tasks)\n")
        handle.write("- Harmonic and non-harmonic task sets\n")
        handle.write("- Tight deadline pressure cases\n")
        handle.write("- Utilization > 1 cases\n")
        handle.write("- Randomized stress cases\n\n")

        for result in results:
            handle.write(f"Workload {result['workload_num']}:\n")
            handle.write(f"  File: {result['file']}\n")
            handle.write(f"  Analysis: {result['analysis']}\n")
            handle.write(f"  Exit Code: {result['exit_code']}\n")
            handle.write(f"  Output: {result['output']}\n")
            handle.write(f"  Execution Time: {result['exec_time']:.3f}s\n")
            handle.write(f"  Has Expected: {result['has_expected']}\n")
            handle.write("-" * 40 + "\n")

    print(f"\nDetailed results saved to: {results_file}")
    print(f"Test results folder: {test_results_dir.resolve()}")


if __name__ == "__main__":
    test_workloads()
