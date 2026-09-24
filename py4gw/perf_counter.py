"""Port of Reforged Native's performance counters (the ``PyProfiler`` module).

Sources:

* ``Py4GW_Reforged_Native/include/profiler/profiler.h``
* ``Py4GW_Reforged_Native/src/profiler/profiler.cpp``
* ``Py4GW_Reforged_Native/src/profiler/profiler_bindings.cpp``

This is the **timing** instrument: named stopwatches held in a rolling history
and reported as ``(min, avg, p50, p95, p99, max)``. The separate flow and
callstack instrument is :mod:`py4gw.profiler`.

The Python-facing surface is the binding's, not the C++ class's, because that is
what a Python caller in Reforged actually reaches: ``start``, ``end``,
``get_metric_names``, ``get_reports``, ``get_history``, ``reset``.
``calculate_report`` is the C++ ``Profiler::CalculateReport`` that
``get_reports`` calls per name.

Behaviour carried over exactly:

* one averaged sample is stored every **6** completed measurements
  (``MetricData::push_frame_throttled``); the average is
  ``accumulator / frames_in_window``;
* the history is the fixed ``MAX_SAMPLES = 600`` rolling buffer, and until it
  fills only the valid prefix participates in a report;
* percentiles come from a sorted copy at ``int(n * p)`` with no clamp, and
  ``max`` is the last element of that copy;
* a metric name enters ``get_metric_names`` on its first completed measurement,
  before it has accumulated enough samples to store one.

Deviations, and there is exactly one:

* the native ``Profiler`` is a static namespace over process-global maps,
  because the injected runtime is one process. This is an instance, because the
  controller can hold more than one client -- the same reason every ported
  context reader is an instance.

Nothing else is added. In particular:

* ``end`` returns nothing, because the native ``Profiler::End`` returns
  ``void``; a single measurement's own time is not recoverable from the
  counter, since stored samples are averages of six;
* there is no context manager over ``start``/``end``, because the source has
  none -- a caller that needs one builds it from those two members;
* names are not validated, because the source does not validate them; and
* the frame stamp the binding supplies internally
  (``PY4GW::System::GetTickCount64()``) is supplied internally here too, from a
  monotonic millisecond tick. ``MetricData::last_frame_id`` stores it and
  nothing in the source reads it.
"""

from __future__ import annotations

import time
from threading import RLock
from typing import NamedTuple

MAX_SAMPLES = 600
"""Native ``MetricData::MAX_SAMPLES``: the rolling history length per metric."""

RECORD_EVERY = 6
"""Native throttle: store one averaged sample every six completed measurements.

``MetricData::push_frame_throttled`` accumulates and stores
``accumulator / frames_in_window`` once ``frames_in_window >= 6``. Its
``current_frame`` argument is written to ``last_frame_id`` and never read, so
the trigger counts completions rather than comparing frames.
"""


class MetricSummary(NamedTuple):
    """Native ``MetricSummary``: ``{ min, avg, p50, p95, p99, max }``.

    A ``std::tuple<double, double, double, double, double, double>`` in the
    source, and every value is in milliseconds.
    """

    min: float
    avg: float
    p50: float
    p95: float
    p99: float
    max: float


class _MetricData:
    """Native ``MetricData``: a rolling buffer behind a completion throttle."""

    __slots__ = (
        "samples",
        "head",
        "full",
        "last_frame_id",
        "accumulator",
        "frames_in_window",
    )

    def __init__(self) -> None:
        """Create an empty buffer, zero-filled as the source's array is."""

        self.samples: list[float] = [0.0] * MAX_SAMPLES
        self.head = 0
        self.full = False
        self.last_frame_id = 0
        self.accumulator = 0.0
        self.frames_in_window = 0

    def count(self) -> int:
        """Return how many entries are valid, as the source's ``count()`` does."""

        return MAX_SAMPLES if self.full else self.head

    def push_frame_throttled(self, current_frame: int, ms: float) -> None:
        """Accumulate one measurement and store an average every sixth."""

        self.accumulator += ms
        self.frames_in_window += 1

        if self.frames_in_window >= RECORD_EVERY:
            self.samples[self.head] = self.accumulator / self.frames_in_window
            self.head = (self.head + 1) % MAX_SAMPLES
            if self.head == 0:
                self.full = True
            self.accumulator = 0.0
            self.frames_in_window = 0
            self.last_frame_id = current_frame


class PerfCounter:
    """Named stopwatches with a rolling history, ported from ``PyProfiler``."""

    def __init__(self) -> None:
        """Create an empty counter."""

        self._active: dict[str, int] = {}
        self._history: dict[str, _MetricData] = {}
        self._lock = RLock()

    # ── the binding's surface ─────────────────────────────────────────────

    def start(self, name: str) -> None:
        """Begin timing a named metric, replacing an older active start.

        Native ``Profiler::Start``: the start point is overwritten, so a
        ``start`` without a matching ``end`` is discarded rather than leaked.
        The stored value is a high-resolution counter reading, matching
        ``QueryPerformanceCounter``.
        """

        with self._lock:
            self._active[name] = time.perf_counter_ns()

    def end(self, name: str) -> None:
        """End a named metric.

        Native ``Profiler::End`` returns ``void``, and so does this. A missing
        matching ``start`` is silently ignored, which is also the source's
        behaviour.
        """

        end_ns = time.perf_counter_ns()
        with self._lock:
            start_ns = self._active.pop(name, None)
            if start_ns is None:
                return
            elapsed_ms = (end_ns - start_ns) / 1_000_000.0
            self._data_locked(name).push_frame_throttled(_tick(), elapsed_ms)

    def get_metric_names(self) -> list[str]:
        """Return every metric that has completed at least one measurement.

        Native ``GetMetricNames`` walks its history map, so a name appears as
        soon as one measurement completes -- before six have accumulated and a
        sample is stored.
        """

        with self._lock:
            return list(self._history)

    def get_reports(self) -> list[tuple[str, MetricSummary]]:
        """Return ``(name, min, avg, p50, p95, p99, max)`` for every metric.

        Native ``CalculateReportAll``, which the binding exposes as
        ``get_reports``.
        """

        with self._lock:
            names = list(self._history)
        return [(name, self.calculate_report(name)) for name in names]

    def get_history(self, name: str) -> list[float]:
        """Return a metric's stored samples, oldest first.

        Native ``GetMetricHistory`` returns ``{}`` for an unknown name and
        rotates the ring buffer back into insertion order when it has wrapped.
        """

        with self._lock:
            data = self._history.get(name)
            if data is None:
                return []
            if not data.full:
                return list(data.samples[: data.head])
            return list(data.samples[data.head :]) + list(data.samples[: data.head])

    def reset(self) -> None:
        """Clear active starts and all history, as native ``Reset`` does."""

        with self._lock:
            self._active.clear()
            self._history.clear()

    # ── the C++ surface behind get_reports ────────────────────────────────

    def calculate_report(self, name: str) -> MetricSummary:
        """Return one metric's summary, or all zeros when it has no samples.

        Native ``Profiler::CalculateReport``. The minimum and average are taken
        over the valid prefix in insertion order; the percentiles and maximum
        come from a sorted copy at ``int(n * p)`` and ``back()``.
        """

        with self._lock:
            data = self._history.get(name)
            if data is None:
                return MetricSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            count = data.count()
            if count == 0:
                return MetricSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            samples = list(data.samples[:count])

        total = 0.0
        minimum = samples[0]
        for value in samples:
            total += value
            if value < minimum:
                minimum = value

        ordered = sorted(samples)
        return MetricSummary(
            minimum,
            total / count,
            ordered[_percentile_index(count, 0.50)],
            ordered[_percentile_index(count, 0.95)],
            ordered[_percentile_index(count, 0.99)],
            ordered[-1],
        )


    def _data_locked(self, name: str) -> _MetricData:
        """Return a metric's buffer, creating it on first use."""

        data = self._history.get(name)
        if data is None:
            data = _MetricData()
            self._history[name] = data
        return data



def _percentile_index(sample_count: int, percentile: float) -> int:
    """Return the native percentile index: ``static_cast<size_t>(n * p)``.

    The source applies no clamp, and none is needed: ``n * p`` is below ``n``
    for every ``p < 1``, so truncation can never reach past the last element.
    """

    return int(sample_count * percentile)


def _tick() -> int:
    """Return a monotonic millisecond tick.

    Stands in for ``PY4GW::System::GetTickCount64()``, which the binding passes
    as the frame stamp on the caller's behalf. Nothing reads the stored stamp,
    so the source of the tick does not affect any report.
    """

    return time.monotonic_ns() // 1_000_000
