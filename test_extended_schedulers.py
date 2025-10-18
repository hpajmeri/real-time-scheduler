import unittest

from edf_scheduler import EarliestDeadlineFirstScheduler
from rate_monotonic_scheduler import RateMonotonicScheduler
from rt_schedulers_extended import build_scheduler


class TestExtendedSchedulers(unittest.TestCase):
    def test_build_scheduler_aliases(self) -> None:
        tasks = [{"execution": 1.0, "period": 3.0, "deadline": 3.0}]
        self.assertIsInstance(build_scheduler("rm", tasks), RateMonotonicScheduler)
        self.assertIsInstance(build_scheduler("rate_monotonic", tasks), RateMonotonicScheduler)
        self.assertIsInstance(build_scheduler("edf", tasks), EarliestDeadlineFirstScheduler)
        self.assertIsInstance(
            build_scheduler("earliest_deadline_first", tasks), EarliestDeadlineFirstScheduler
        )
        with self.assertRaises(ValueError):
            build_scheduler("unknown", tasks)


if __name__ == "__main__":
    unittest.main()
