import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from functional_test import Sample, Verdict, evaluate, main, read_trace


def trace(*, offset=0, ready=1, high_at=None, drop=(), repeat=False, stuck=False):
    return [
        Sample(offset + t, int(t == 20 or (repeat and t == 60)), ready,
               int(stuck or t == high_at))
        for t in range(0, 181, 20) if t not in drop
    ]


class FunctionalContractTests(unittest.TestCase):
    def test_inclusive_deadline_and_next_sample(self):
        self.assertEqual(evaluate(trace(high_at=120), "ready"),
                         Verdict("FT-01", "PASS", "first ack at +100 ms meets +100 ms deadline"))
        self.assertEqual(evaluate(trace(high_at=140), "ready").status, "FAIL")

    def test_start_relative_not_absolute(self):
        self.assertEqual(evaluate(trace(offset=1000, high_at=60), "ready"),
                         Verdict("FT-01", "PASS", "first ack at +40 ms meets +100 ms deadline"))

    def test_blocked_fixture_requires_entire_window(self):
        self.assertEqual(evaluate(trace(ready=0), "blocked").status, "PASS")
        self.assertEqual(evaluate(trace(ready=0, high_at=180), "blocked"),
                         Verdict("FT-02", "FAIL", "unexpected ack at +160 ms"))

    def test_ready_without_ack_is_failure_with_complete_trace(self):
        self.assertEqual(evaluate(trace(), "ready").status, "FAIL")

    def test_gap_is_inconclusive_even_if_an_ack_was_recorded(self):
        self.assertEqual(evaluate(trace(high_at=120, drop=(100,)), "ready"),
                         Verdict("FT-01", "INCONCLUSIVE", "expected sample at 100 ms; saw 120 ms"))

    def test_truncated_tail_and_missing_baseline(self):
        self.assertEqual(evaluate(trace(ready=0, drop=(180,)), "blocked").status, "INCONCLUSIVE")
        self.assertEqual(evaluate(trace(drop=(0,)), "ready").status, "INCONCLUSIVE")

    def test_extra_off_grid_sample(self):
        samples = trace(high_at=60)
        samples.insert(3, Sample(55, 0, 1, 0))
        self.assertIn("saw 55 ms", evaluate(samples, "ready").evidence)

    def test_multiple_requests_and_stale_ack(self):
        self.assertIn("multiple start requests", evaluate(trace(repeat=True), "ready").evidence)
        self.assertIn("already high", evaluate(trace(stuck=True), "ready").evidence)

    def test_fixture_changes_are_not_equipment_failures(self):
        samples = trace(high_at=60)
        samples[2] = Sample(40, 0, 0, 0)
        self.assertIn("requires ready=1", evaluate(samples, "ready").evidence)
        self.assertEqual(evaluate(trace(ready=0), "ready").status, "INCONCLUSIVE")

    def test_no_trigger_or_samples(self):
        self.assertIn("no recorded start", evaluate([Sample(0, 0, 1, 0)], "ready").evidence)
        self.assertIn("no baseline", evaluate([], "blocked").evidence)

    def test_reader_rejects_bad_bits_duplicate_timestamp_and_bad_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.csv"
            for body, error in [("0,0,1,true\n", ValueError),
                                ("0,0,1,0\n0,1,1,0\n", ValueError),
                                ('0,"1,1,0\n', csv.Error)]:
                with self.subTest(body=body):
                    path.write_text("time_ms,start,ready,ack\n" + body)
                    with self.assertRaises(error):
                        read_trace(path)

    def test_cli_matches_documented_exit_codes(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        cases = [("ready", "ready-on-time", 0), ("ready", "ready-late", 1),
                 ("blocked", "blocked-quiet", 0), ("blocked", "blocked-unexpected", 1),
                 ("ready", "ready-gap", 3), ("ready", "missing", 2)]
        for mode, name, expected in cases:
            with self.subTest(name=name), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main([mode, str(root / (name + ".csv"))]), expected)


if __name__ == "__main__":
    unittest.main()
