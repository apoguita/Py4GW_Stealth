"""Offline tests for the ported ``PyProfiler`` performance counters.

Source: ``Py4GW_Reforged_Native/include/profiler/profiler.h`` and
``src/profiler/profiler.cpp``. Every constant and every formula asserted here is
the source's, so a change in behaviour fails a test rather than a report.
"""

from __future__ import annotations

import unittest

from py4gw import MAX_SAMPLES, MetricSummary, PerfCounter
from py4gw.perf_counter import RECORD_EVERY, _MetricData


def _seed(counter: PerfCounter, name: str, samples: list[float]) -> None:
    """Place known samples in a metric's buffer.

    ``PerfCounter`` exposes no way to inject a duration, because the source has
    none either: ``Profiler`` records only what ``Start``/``End`` measure. Pinning
    the percentile formula needs known samples, so the buffer is written
    directly. That is deliberate here and belongs nowhere else.
    """

    data = counter._data_locked(name)
    data.samples[: len(samples)] = samples
    data.head = len(samples)
    data.full = False


class ConstantsTests(unittest.TestCase):
    """Verify the ported constants against the source."""

    def test_history_length_matches_native_max_samples(self) -> None:
        """``MetricData::MAX_SAMPLES`` is 600."""

        self.assertEqual(MAX_SAMPLES, 600)

    def test_throttle_window_matches_native(self) -> None:
        """``push_frame_throttled`` triggers on ``frames_in_window >= 6``."""

        self.assertEqual(RECORD_EVERY, 6)


class MetricDataTests(unittest.TestCase):
    """Verify the rolling buffer and its completion throttle."""

    def test_six_measurements_store_one_averaged_sample(self) -> None:
        """One sample is stored per six completions, holding their average."""

        data = _MetricData()
        for ms in (1.0, 2.0, 3.0, 4.0, 5.0):
            data.push_frame_throttled(0, ms)
        self.assertEqual(data.count(), 0, "no sample before the window closes")

        data.push_frame_throttled(11, 6.0)
        self.assertEqual(data.count(), 1)
        self.assertAlmostEqual(data.samples[0], 3.5)

    def test_frame_stamp_is_stored_but_not_used(self) -> None:
        """The stamp lands in ``last_frame_id`` and the trigger ignores it."""

        data = _MetricData()
        for _ in range(RECORD_EVERY - 1):
            data.push_frame_throttled(999, 1.0)
        self.assertEqual(data.count(), 0)
        data.push_frame_throttled(1234, 1.0)
        self.assertEqual(data.count(), 1)
        self.assertEqual(data.last_frame_id, 1234)

    def test_partial_window_is_discarded_by_reset_not_stored(self) -> None:
        """Two completions leave an open window and no sample."""

        data = _MetricData()
        data.push_frame_throttled(0, 5.0)
        data.push_frame_throttled(0, 5.0)
        self.assertEqual(data.count(), 0)

    def test_ring_buffer_wraps_and_marks_full(self) -> None:
        """The buffer keeps the newest 600 samples once it has wrapped."""

        data = _MetricData()
        for index in range(MAX_SAMPLES * RECORD_EVERY + RECORD_EVERY):
            data.push_frame_throttled(0, float(index))
        self.assertTrue(data.full)
        self.assertEqual(data.count(), MAX_SAMPLES)

    def test_history_length_grows_to_the_cap(self) -> None:
        """``count()`` reports the valid prefix until the buffer fills."""

        data = _MetricData()
        self.assertEqual(data.count(), 0)
        for _ in range(RECORD_EVERY * 3):
            data.push_frame_throttled(0, 1.0)
        self.assertEqual(data.count(), 3)
        self.assertFalse(data.full)


class ReportTests(unittest.TestCase):
    """Verify the report formula against ``Profiler::CalculateReport``."""

    def test_unknown_metric_reports_all_zeros(self) -> None:
        """The source returns ``{0,0,0,0,0,0}`` for a missing or empty metric."""

        counter = PerfCounter()
        self.assertEqual(
            counter.calculate_report("missing"),
            MetricSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        )

    def test_summary_field_order_matches_native(self) -> None:
        """The tuple order is ``{ min, avg, p50, p95, p99, max }``."""

        self.assertEqual(
            MetricSummary._fields, ("min", "avg", "p50", "p95", "p99", "max")
        )

    def test_percentiles_use_truncated_n_times_p(self) -> None:
        """``p50`` is ``sorted[int(n * 0.50)]``, which is not the median.

        With ten samples of 1..10 the source returns ``sorted[5]``, i.e. 6.0,
        not the 5.5 a nearest-rank or interpolating implementation would give.
        """

        counter = PerfCounter()
        _seed(counter, "scan", [float(value) for value in range(1, 11)])

        summary = counter.calculate_report("scan")
        self.assertEqual(summary.min, 1.0)
        self.assertEqual(summary.avg, 5.5)
        self.assertEqual(summary.p50, 6.0)
        self.assertEqual(summary.p95, 10.0)
        self.assertEqual(summary.p99, 10.0)
        self.assertEqual(summary.max, 10.0)

    def test_single_sample_reports_that_sample_everywhere(self) -> None:
        """One sample is its own min, average, every percentile, and max."""

        counter = PerfCounter()
        _seed(counter, "one", [7.5])
        summary = counter.calculate_report("one")
        self.assertEqual(summary, MetricSummary(7.5, 7.5, 7.5, 7.5, 7.5, 7.5))

    def test_get_reports_pairs_each_name_with_its_summary(self) -> None:
        """``CalculateReportAll`` bundles the name with the six values."""

        counter = PerfCounter()
        _seed(counter, "alpha", [1.0, 2.0, 3.0])
        _seed(counter, "beta", [4.0])

        reports = dict(counter.get_reports())
        self.assertEqual(set(reports), {"alpha", "beta"})
        self.assertAlmostEqual(reports["alpha"].avg, 2.0)
        self.assertAlmostEqual(reports["beta"].avg, 4.0)

    def test_history_is_oldest_first(self) -> None:
        """A partially filled buffer reads in insertion order."""

        counter = PerfCounter()
        _seed(counter, "scan", [1.0, 2.0, 3.0])
        self.assertEqual(counter.get_history("scan"), [1.0, 2.0, 3.0])

    def test_history_of_an_unknown_metric_is_empty(self) -> None:
        """The source returns ``{}`` for a name it has never seen."""

        self.assertEqual(PerfCounter().get_history("missing"), [])

    def test_history_rotates_a_wrapped_buffer_back_into_order(self) -> None:
        """A wrapped buffer reads oldest-to-newest across the wrap point.

        ``head`` is the next slot to write, so once the buffer is full it holds
        the *oldest* sample. Reading order therefore starts at ``head`` and
        finishes on the slots just before it, which is what puts the seam at the
        end of the returned list.
        """

        counter = PerfCounter()
        data = counter._data_locked("scan")
        data.samples[MAX_SAMPLES - 2] = 98.0
        data.samples[MAX_SAMPLES - 1] = 99.0
        data.samples[0] = 0.0
        data.samples[1] = 1.0
        data.head = 2
        data.full = True

        history = counter.get_history("scan")
        self.assertEqual(len(history), MAX_SAMPLES)
        self.assertEqual(history[:2], [0.0, 0.0], "oldest slots come first")
        self.assertEqual(
            history[-4:], [98.0, 99.0, 0.0, 1.0], "the wrap seam closes the list"
        )


class CounterTests(unittest.TestCase):
    """Verify the counter surface the binding exposes."""

    def test_metric_name_appears_before_any_sample_is_stored(self) -> None:
        """``GetMetricNames`` reads the history map, not the sample count."""

        counter = PerfCounter()
        counter.start("once")
        counter.end("once")
        self.assertEqual(counter.get_metric_names(), ["once"])
        self.assertEqual(counter.get_history("once"), [])

    def test_end_without_a_start_is_a_no_op(self) -> None:
        """A missing start is ignored and creates nothing, as the source does."""

        counter = PerfCounter()
        self.assertIsNone(counter.end("missing"))
        self.assertEqual(counter.get_metric_names(), [])

    def test_start_overwrites_an_active_start(self) -> None:
        """A second start replaces the first rather than queueing it."""

        counter = PerfCounter()
        counter.start("scan")
        counter.start("scan")
        counter.end("scan")
        # The first start was replaced, so only one completion reached the
        # buffer: a second end has nothing left to pair with.
        counter.end("scan")
        self.assertEqual(counter.get_history("scan"), [])
        self.assertEqual(counter.get_metric_names(), ["scan"])

    def test_end_returns_none_like_the_native_void(self) -> None:
        """``Profiler::End`` returns ``void``, so this returns ``None``."""

        counter = PerfCounter()
        counter.start("scan")
        self.assertIsNone(counter.end("scan"))

    def test_six_completions_store_a_non_zero_average(self) -> None:
        """A measured duration survives into the report, unrounded.

        The duration comes from the high-resolution counter, so a fast metric
        is not rounded down to zero by the millisecond tick that stamps the
        frame.
        """

        counter = PerfCounter()
        for _ in range(RECORD_EVERY):
            counter.start("scan")
            counter.end("scan")

        history = counter.get_history("scan")
        self.assertEqual(len(history), 1)
        self.assertGreater(history[0], 0.0)

    def test_any_name_is_accepted(self) -> None:
        """The source validates nothing, so neither does this."""

        counter = PerfCounter()
        counter.start("")
        counter.end("")
        self.assertEqual(counter.get_metric_names(), [""])

    def test_reset_clears_history_and_active_starts(self) -> None:
        """``Profiler::Reset`` clears both maps."""

        counter = PerfCounter()
        counter.start("open")
        counter.start("done")
        counter.end("done")
        counter.reset()

        self.assertEqual(counter.get_metric_names(), [])
        self.assertIsNone(counter.end("open"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
