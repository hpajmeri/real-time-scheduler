import unittest

from rt_scheduler.policies import LeastLaxityFirstScheduler


class TestLeastLaxityFirstScheduler(unittest.TestCase):
    def test_schedulable_dynamic_priorities(self) -> None:
        tasks = [
            {"execution": 1.0, "period": 4.0, "deadline": 4.0},
            {"execution": 1.5, "period": 5.0, "deadline": 5.0},
        ]
        scheduler = LeastLaxityFirstScheduler(tasks)
        result = scheduler.simulate(window=20.0)
        self.assertTrue(result.schedulable)
        self.assertEqual(len(result.preemptions), len(tasks))

    def test_detects_deadline_miss(self) -> None:
        tasks = [
            {"execution": 2.5, "period": 4.0, "deadline": 4.0},
            {"execution": 2.5, "period": 5.0, "deadline": 5.0},
        ]
        scheduler = LeastLaxityFirstScheduler(tasks)
        result = scheduler.simulate(window=20.0)
        self.assertFalse(result.schedulable)
        self.assertGreaterEqual(len(result.deadline_misses), 1)


if __name__ == "__main__":
    unittest.main()
