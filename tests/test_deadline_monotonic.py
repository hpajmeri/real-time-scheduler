import unittest

from rt_scheduler.policies import DeadlineMonotonicScheduler


class TestDeadlineMonotonicScheduler(unittest.TestCase):
    def test_schedulable_workload(self) -> None:
        tasks = [
            {"execution": 1.0, "period": 4.0, "deadline": 4.0},
            {"execution": 1.0, "period": 5.0, "deadline": 5.0},
        ]
        scheduler = DeadlineMonotonicScheduler(tasks)
        result = scheduler.simulate(window=40.0)
        self.assertTrue(result.schedulable)
        self.assertEqual(len(result.preemptions), len(tasks))

    def test_unschedulable_due_to_deadline(self) -> None:
        tasks = [
            {"execution": 3.0, "period": 5.0, "deadline": 5.0},
            {"execution": 3.0, "period": 7.0, "deadline": 6.0},
        ]
        scheduler = DeadlineMonotonicScheduler(tasks)
        result = scheduler.simulate(window=60.0)
        self.assertFalse(result.schedulable)
        self.assertGreaterEqual(len(result.deadline_misses), 1)


if __name__ == "__main__":
    unittest.main()
