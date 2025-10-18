import unittest

from rate_monotonic_scheduler import RateMonotonicScheduler


class TestRateMonotonicScheduler(unittest.TestCase):
    def test_schedulable_workload(self) -> None:
        tasks = [
            {"execution": 1.0, "period": 4.0, "deadline": 4.0},
            {"execution": 1.0, "period": 5.0, "deadline": 5.0},
        ]
        scheduler = RateMonotonicScheduler(tasks)
        result = scheduler.simulate(window=40.0, include_timeline=True)
        self.assertTrue(result.schedulable)
        self.assertEqual(len(result.preemptions), len(tasks))
        self.assertGreater(len(result.timeline), 0)

    def test_unschedulable_workload(self) -> None:
        tasks = [
            {"execution": 5.0, "period": 7.0, "deadline": 7.0},
            {"execution": 4.0, "period": 10.0, "deadline": 10.0},
        ]
        scheduler = RateMonotonicScheduler(tasks)
        result = scheduler.simulate(window=40.0)
        self.assertFalse(result.schedulable)
        self.assertGreaterEqual(len(result.deadline_misses), 1)


if __name__ == "__main__":
    unittest.main()
