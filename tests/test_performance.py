"""Tests for the controller-side performance counter."""

from __future__ import annotations

import unittest

from py4gw import PerfCounter


class PerfCounterTests(unittest.TestCase):
    """Verify timing storage and reporting without relying on sleep timing."""

    def test_records_bounded_history_and_reports_percentiles(self) -> None:
        """Reports summarize recorded samples in milliseconds."""

        counter = PerfCounter(history_size=3)
        for value in (1.0, 2.0, 3.0, 4.0):
            counter.record("scan", value)

        self.assertEqual(counter.history("scan"), [2.0, 3.0, 4.0])
        report = counter.report("scan")
        self.assertEqual(report.count, 3)
        self.assertEqual(report.minimum_ms, 2.0)
        self.assertEqual(report.average_ms, 3.0)
        self.assertEqual(report.p50_ms, 3.0)
        self.assertEqual(report.maximum_ms, 4.0)

    def test_averages_configured_sample_windows(self) -> None:
        """Native-style six-frame averaging can be selected explicitly."""

        counter = PerfCounter(samples_per_record=2)
        counter.record("update", 2.0)
        self.assertEqual(counter.history("update"), [])
        counter.record("update", 4.0)
        self.assertEqual(counter.history("update"), [3.0])

    def test_measure_context_records_on_exception(self) -> None:
        """A failed operation still contributes its elapsed sample."""

        counter = PerfCounter()
        with self.assertRaises(RuntimeError):
            with counter.measure("operation"):
                raise RuntimeError("expected")
        self.assertEqual(len(counter.history("operation")), 1)

    def test_unknown_metric_and_invalid_arguments_are_clear(self) -> None:
        """Invalid names and negative durations fail before recording."""

        counter = PerfCounter()
        self.assertIsNone(counter.end("missing"))
        with self.assertRaises(ValueError):
            counter.record("", 1.0)
        with self.assertRaises(ValueError):
            counter.record("bad", -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
