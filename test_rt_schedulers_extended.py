import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestSchedulerCLIs(unittest.TestCase):
    def _write_workload(self, tmpdir: Path, body: str) -> Path:
        path = tmpdir / "workload.txt"
        path.write_text(textwrap.dedent(body).strip() + "\n", encoding="ascii")
        return path

    def test_rate_monotonic_cli_schedulable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workload = self._write_workload(
                tmp_path,
                """
                1,4,4
                1,5,5
                """,
            )
            result = subprocess.run(
                [sys.executable, "rate_monotonic_scheduler.py", str(workload)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            lines = result.stdout.strip().splitlines()
            self.assertGreaterEqual(len(lines), 2)
            self.assertEqual(lines[0], "1")

    def test_edf_cli_unschedulable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workload = self._write_workload(
                tmp_path,
                """
                4,5,5
                4,6,6
                """,
            )
            result = subprocess.run(
                [sys.executable, "edf_scheduler.py", str(workload)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            lines = result.stdout.strip().splitlines()
            self.assertEqual(lines[0], "0")


if __name__ == "__main__":
    unittest.main()
