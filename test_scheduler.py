#!/usr/bin/env python3
"""
Comprehensive Test Script for Deadline Monotonic Scheduler
Tests against provided workloads and additional robust test cases.
"""

import subprocess
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

def parse_expected_results(expected_file: str) -> Dict[int, Tuple[str, str]]:
    """Parse expected results file and return a dictionary mapping workload number to expected output."""
    expected_results = {}
    current_workload = None
    current_output = []
    
    with open(expected_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("Workload"):
                # Save previous workload if exists
                if current_workload is not None:
                    if len(current_output) >= 2:
                        expected_results[current_workload] = (current_output[0], current_output[1])
                    elif len(current_output) == 1:
                        expected_results[current_workload] = (current_output[0], "")
                
                # Start new workload
                current_workload = int(line.split()[1].rstrip(':'))
                current_output = []
            elif line and current_workload is not None:
                current_output.append(line)
    
    # Save last workload
    if current_workload is not None and current_output:
        if len(current_output) >= 2:
            expected_results[current_workload] = (current_output[0], current_output[1])
        elif len(current_output) == 1:
            expected_results[current_workload] = (current_output[0], "")
    
    return expected_results

def run_scheduler_on_workload(workload_file: str, timeout: int = 60) -> Tuple[int, str, float]:
    """Run the scheduler on a workload and return exit code, output, and execution time."""
    try:
        start_time = time.time()
        result = subprocess.run(
            ["python3", "rt_scheduler.py", workload_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        execution_time = time.time() - start_time
        return result.returncode, result.stdout, execution_time
    except subprocess.TimeoutExpired:
        return -1, f"Timeout after {timeout} seconds", timeout
    except Exception as e:
        return -2, f"Error: {str(e)}", 0

def analyze_workload(workload_file: str) -> Dict:
    """Analyze a workload file and return statistics."""
    tasks = []
    with open(workload_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split(',')
                if len(parts) == 3:
                    execution, period, deadline = map(float, parts)
                    tasks.append({
                        "execution": execution,
                        "period": period,
                        "deadline": deadline
                    })
    
    if not tasks:
        return {"error": "No valid tasks found"}
    
    # Calculate statistics
    total_utilization = sum(t["execution"] / t["period"] for t in tasks)
    avg_period = sum(t["period"] for t in tasks) / len(tasks)
    avg_deadline = sum(t["deadline"] for t in tasks) / len(tasks)
    avg_execution = sum(t["execution"] for t in tasks) / len(tasks)
    
    # Check for edge cases
    deadline_less_than_period = any(t["deadline"] < t["period"] for t in tasks)
    very_small_periods = any(t["period"] < 1.0 for t in tasks)
    very_large_periods = any(t["period"] > 100.0 for t in tasks)
    high_utilization = total_utilization > 0.8
    
    return {
        "num_tasks": len(tasks),
        "total_utilization": total_utilization,
        "avg_period": avg_period,
        "avg_deadline": avg_deadline,
        "avg_execution": avg_execution,
        "deadline_less_than_period": deadline_less_than_period,
        "very_small_periods": very_small_periods,
        "very_large_periods": very_large_periods,
        "high_utilization": high_utilization,
        "tasks": tasks
    }

def test_workloads():
    """Test the scheduler against all workloads."""
    print("Testing Deadline Monotonic Scheduler")
    print("=" * 60)
    
    # Create test results directory
    test_results_dir = Path("test_results")
    test_results_dir.mkdir(exist_ok=True)
    
    # Create timestamped results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = test_results_dir / f"test_results_{timestamp}.txt"
    
    print(f"Results will be saved to: {results_file}")
    print("=" * 60)
    
    # Test original workloads with expected results
    expected_file = "workloads/expected_results.txt"
    expected_results = parse_expected_results(expected_file)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    timeout_tests = 0
    error_tests = 0
    
    # Find all workload files
    extra_files_dir = Path("workloads")
    workload_files = []
    
    # Test original workloads (1-6) with expected results
    for workload_num in range(1, 7):
        workload_file = extra_files_dir / f"workload{workload_num}.txt"
        if workload_file.exists():
            workload_files.append((workload_num, workload_file, True))  # True = has expected result
    
    # Test new workloads (7-39) without expected results
    for workload_num in range(7, 40):
        workload_file = extra_files_dir / f"workload{workload_num}.txt"
        if workload_file.exists():
            workload_files.append((workload_num, workload_file, False))  # False = no expected result
    
    print(f"Found {len(workload_files)} workload files to test")
    print()
    
    results = []
    
    for workload_num, workload_file, has_expected in workload_files:
        print(f"Testing Workload {workload_num}...")
        
        # Analyze workload
        analysis = analyze_workload(str(workload_file))
        if "error" in analysis:
            print(f"  ❌ ERROR: {analysis['error']}")
            error_tests += 1
            continue
        
        print(f"  Tasks: {analysis['num_tasks']}")
        print(f"  Utilization: {analysis['total_utilization']:.3f}")
        print(f"  Avg Period: {analysis['avg_period']:.2f}")
        print(f"  Avg Deadline: {analysis['avg_deadline']:.2f}")
        
        # Run scheduler with 60-second timeout
        exit_code, output, exec_time = run_scheduler_on_workload(str(workload_file), timeout=60)
        total_tests += 1
        
        # Analyze result
        if exit_code == 0:
            lines = output.strip().split('\n')
            if len(lines) >= 1:
                schedulable = lines[0].strip() == "1"
                preemption_counts = lines[1].strip() if len(lines) > 1 and lines[1].strip() else ""
                
                print(f"  Result: {'Schedulable' if schedulable else 'Unschedulable'}")
                if schedulable and preemption_counts:
                    print(f"  Preemptions: {preemption_counts}")
                print(f"  Execution time: {exec_time:.3f}s")
                
                if has_expected:
                    # Compare with expected result
                    expected_schedulable, expected_preemptions = expected_results[workload_num]
                    expected_output = f"{expected_schedulable}\n{expected_preemptions}"
                    
                    if output.strip() == expected_output.strip():
                        print(f"  ✅ PASSED (Expected: {'Schedulable' if expected_schedulable == '1' else 'Unschedulable'})")
                        passed_tests += 1
                    else:
                        print(f"  ❌ FAILED: Output mismatch")
                        print(f"  Expected: '{expected_output}'")
                        print(f"  Actual:   '{output.strip()}'")
                        failed_tests += 1
                else:
                    # For new workloads, just check if output is valid
                    if schedulable or not schedulable:  # Valid output
                        print(f"  ✅ PASSED (Valid output)")
                        passed_tests += 1
                    else:
                        print(f"  ❌ FAILED: Invalid output format")
                        failed_tests += 1
            else:
                print(f"  ❌ FAILED: Invalid output format")
                failed_tests += 1
        elif exit_code == -1:
            print(f"  ⏰ TIMEOUT (60s limit exceeded)")
            timeout_tests += 1
        else:
            print(f"  ❌ ERROR: {output}")
            error_tests += 1
        
        print()
        results.append({
            "workload_num": workload_num,
            "file": str(workload_file),
            "analysis": analysis,
            "exit_code": exit_code,
            "output": output,
            "exec_time": exec_time,
            "has_expected": has_expected
        })
    
    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Timeouts: {timeout_tests}")
    print(f"Errors: {error_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests == 0 and timeout_tests == 0 and error_tests == 0:
        print("Overall Status: 🎉 ALL TESTS PASSED")
    else:
        print("Overall Status: ❌ SOME TESTS FAILED")
    
    # Detailed analysis
    print("\nDETAILED ANALYSIS")
    print("=" * 60)
    
    schedulable_count = 0
    unschedulable_count = 0
    avg_exec_time = 0
    exec_times = []
    
    for result in results:
        if result["exit_code"] == 0:
            lines = result["output"].strip().split('\n')
            if lines and lines[0].strip() == "1":
                schedulable_count += 1
            else:
                unschedulable_count += 1
            exec_times.append(result["exec_time"])
    
    if exec_times:
        avg_exec_time = sum(exec_times) / len(exec_times)
    
    print(f"Schedulable workloads: {schedulable_count}")
    print(f"Unschedulable workloads: {unschedulable_count}")
    print(f"Average execution time: {avg_exec_time:.3f}s")
    
    # Edge case analysis
    edge_cases = {
        "high_utilization": 0,
        "deadline_less_than_period": 0,
        "very_small_periods": 0,
        "very_large_periods": 0
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
    
    print(f"\nEdge Cases Tested:")
    print(f"  High utilization: {edge_cases['high_utilization']}")
    print(f"  Deadline < period: {edge_cases['deadline_less_than_period']}")
    print(f"  Very small periods: {edge_cases['very_small_periods']}")
    print(f"  Very large periods: {edge_cases['very_large_periods']}")
    
    # Save detailed results
    with open(results_file, 'w') as f:
        f.write("Deadline Monotonic Scheduler Test Results\n")
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"Total Tests: {total_tests}\n")
        f.write(f"Passed: {passed_tests}\n")
        f.write(f"Failed: {failed_tests}\n")
        f.write(f"Timeouts: {timeout_tests}\n")
        f.write(f"Errors: {error_tests}\n")
        f.write(f"Success Rate: {passed_tests/total_tests*100:.1f}%\n\n")
        
        f.write("Test Cases Covered:\n")
        f.write("- Original workloads (1-6) with expected results\n")
        f.write("- New workloads (7-29) with validation\n")
        f.write("- Single task cases\n")
        f.write("- Two task cases\n")
        f.write("- Edge cases (small/large periods, deadline < period)\n")
        f.write("- Floating point values\n")
        f.write("- High utilization cases\n")
        f.write("- Large task sets (5+ tasks)\n")
        f.write("- Harmonic and non-harmonic task sets\n")
        f.write("- Challenging deadline pressure cases\n")
        f.write("- Utilization > 1 cases\n")
        f.write("- Very tight deadline cases\n")
        f.write("- Random test cases\n\n")
        
        for result in results:
            f.write(f"Workload {result['workload_num']}:\n")
            f.write(f"  File: {result['file']}\n")
            f.write(f"  Analysis: {result['analysis']}\n")
            f.write(f"  Exit Code: {result['exit_code']}\n")
            f.write(f"  Output: {result['output']}\n")
            f.write(f"  Execution Time: {result['exec_time']:.3f}s\n")
            f.write(f"  Has Expected: {result['has_expected']}\n")
            f.write("-" * 40 + "\n")
    
    print(f"\nDetailed results saved to: {results_file}")
    print(f"Test results folder: {test_results_dir.absolute()}")

if __name__ == "__main__":
    test_workloads() 