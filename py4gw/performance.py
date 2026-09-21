"""Small, thread-safe execution-time counters for external scripts."""

from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock
from typing import Iterator


@dataclass(frozen=True)
class PerformanceReport:
    """Summary statistics for one named metric, expressed in milliseconds."""

    name: str
    count: int
    minimum_ms: float
    average_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    maximum_ms: float


class PerfCounter:
    """Measure named operations and retain a bounded rolling history.

    ``PerfCounter`` is the external equivalent of Reforged's native profiler
    plus its Python ``ProfileScope`` helper. It measures the controller's own
    execution; it does not measure code running inside Guild Wars.

    By default every completed measurement is stored. Set
    ``samples_per_record=6`` to use the native profiler's six-sample averaging
    behavior. The history is bounded to ``history_size`` entries per metric.
    """

    def __init__(self, history_size: int = 600, samples_per_record: int = 1) -> None:
        """Create a counter with bounded history and optional averaging."""

        if history_size <= 0:
            raise ValueError("history_size must be positive.")
        if samples_per_record <= 0:
            raise ValueError("samples_per_record must be positive.")
        self._history_size = history_size
        self._samples_per_record = samples_per_record
        self._active: dict[str, int] = {}
        self._accumulators: dict[str, list[float]] = {}
        self._history: dict[str, deque[float]] = {}
        self._lock = RLock()

    @property
    def history_size(self) -> int:
        """Return the maximum stored samples per metric."""

        return self._history_size

    @property
    def samples_per_record(self) -> int:
        """Return how many measurements are averaged into one stored sample."""

        return self._samples_per_record

    def start(self, name: str) -> None:
        """Start timing a named metric, replacing an older active start."""

        metric_name = self._validate_name(name)
        with self._lock:
            self._active[metric_name] = time.perf_counter_ns()

    def end(self, name: str) -> float | None:
        """Stop a metric and return its elapsed milliseconds.

        ``None`` is returned when no matching ``start`` is active. The elapsed
        value is returned even when averaging delays storing the sample.
        """

        metric_name = self._validate_name(name)
        end_ns = time.perf_counter_ns()
        with self._lock:
            start_ns = self._active.pop(metric_name, None)
            if start_ns is None:
                return None
            elapsed_ms = (end_ns - start_ns) / 1_000_000.0
            self._record_locked(metric_name, elapsed_ms)
            return elapsed_ms

    def record(self, name: str, elapsed_ms: float) -> None:
        """Add a measured duration directly, primarily for adapters and tests."""

        metric_name = self._validate_name(name)
        if elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative.")
        with self._lock:
            self._record_locked(metric_name, float(elapsed_ms))

    @contextmanager
    def measure(self, name: str) -> Iterator[PerfCounter]:
        """Measure a ``with`` block and preserve exceptions raised inside it."""

        self.start(name)
        try:
            yield self
        finally:
            self.end(name)

    def history(self, name: str) -> list[float]:
        """Return stored samples in oldest-to-newest order."""

        metric_name = self._validate_name(name)
        with self._lock:
            return list(self._history.get(metric_name, ()))

    def metric_names(self) -> list[str]:
        """Return names that have at least one completed stored sample."""

        with self._lock:
            return list(self._history)

    def report(self, name: str) -> PerformanceReport:
        """Calculate min, average, percentile, and max values for one metric."""

        metric_name = self._validate_name(name)
        with self._lock:
            samples = list(self._history.get(metric_name, ()))
        if not samples:
            return PerformanceReport(metric_name, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        ordered = sorted(samples)
        return PerformanceReport(
            name=metric_name,
            count=len(samples),
            minimum_ms=ordered[0],
            average_ms=sum(samples) / len(samples),
            p50_ms=ordered[self._percentile_index(len(ordered), 0.50)],
            p95_ms=ordered[self._percentile_index(len(ordered), 0.95)],
            p99_ms=ordered[self._percentile_index(len(ordered), 0.99)],
            maximum_ms=ordered[-1],
        )

    def reports(self) -> list[PerformanceReport]:
        """Return reports for every metric with stored samples."""

        return [self.report(name) for name in self.metric_names()]

    def reset(self) -> None:
        """Clear active timers, pending averages, and recorded history."""

        with self._lock:
            self._active.clear()
            self._accumulators.clear()
            self._history.clear()

    def _record_locked(self, name: str, elapsed_ms: float) -> None:
        pending = self._accumulators.setdefault(name, [])
        pending.append(elapsed_ms)
        if len(pending) < self._samples_per_record:
            return
        average = sum(pending) / len(pending)
        self._history.setdefault(name, deque(maxlen=self._history_size)).append(average)
        pending.clear()

    @staticmethod
    def _percentile_index(sample_count: int, percentile: float) -> int:
        return min(sample_count - 1, int(sample_count * percentile))

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Metric name must be a non-empty string.")
        return name.strip()
