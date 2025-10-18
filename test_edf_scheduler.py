import unittest

from edf_scheduler import EarliestDeadlineFirstScheduler


class TestEarliestDeadlineFirstScheduler(unittest.TestCase):
    def test_schedulable_workload(self) -> None:
        tasks = [
            {"execution": 1.0, "period": 3.0, "deadline": 3.0},
            {"execution": 1.0, "period": 4.0, "deadline": 4.0},
            {"execution": 1.0, "period": 6.0, "deadline": 6.0},
        ]
        scheduler = EarliestDeadlineFirstScheduler(tasks)
        result = scheduler.simulate(window=60.0)
        self.assertTrue(result.schedulable)
        self.assertEqual(len(result.preemptions), len(tasks))

    def test_unschedulable_high_utilization(self) -> None:
        tasks = [
            {"execution": 2.0, "period": 4.0, "deadline": 4.0},
            {"execution": 3.0, "period": 5.0, "deadline": 5.0},
        ]
        scheduler = EarliestDeadlineFirstScheduler(tasks)
        result = scheduler.simulate(window=40.0)
        self.assertFalse(result.schedulable)
        self.assertGreaterEqual(len(result.deadline_misses), 1)


if __name__ == "__main__":
    unittest.main()
