import unittest

from rt_scheduler.cli import build_scheduler
from rt_scheduler.policies import (
    DeadlineMonotonicScheduler,
    EarliestDeadlineFirstScheduler,
    LeastLaxityFirstScheduler,
    RateMonotonicScheduler,
)


class TestPolicyFactory(unittest.TestCase):
    def test_build_scheduler_aliases(self) -> None:
        tasks = [{"execution": 1.0, "period": 3.0, "deadline": 3.0}]
        self.assertIsInstance(build_scheduler("rm", tasks), RateMonotonicScheduler)
        self.assertIsInstance(build_scheduler("rate_monotonic", tasks), RateMonotonicScheduler)
        self.assertIsInstance(build_scheduler("edf", tasks), EarliestDeadlineFirstScheduler)
        self.assertIsInstance(
            build_scheduler("earliest_deadline_first", tasks), EarliestDeadlineFirstScheduler
        )
        self.assertIsInstance(build_scheduler("llf", tasks), LeastLaxityFirstScheduler)
        self.assertIsInstance(
            build_scheduler("least_laxity_first", tasks), LeastLaxityFirstScheduler
        )
        self.assertIsInstance(build_scheduler("dm", tasks), DeadlineMonotonicScheduler)
        with self.assertRaises(ValueError):
            build_scheduler("unknown", tasks)


if __name__ == "__main__":
    unittest.main()
