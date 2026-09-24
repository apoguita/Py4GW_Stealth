"""Measure the live CharContext read path one stage at a time.

Run this from the project directory while Guild Wars is running::

    python tests/perf_context.py

The script is intentionally a direct harness rather than a unittest. It uses
the same scanner, memory reader, and structure reader as the main UI, then
reports the remote-read count beside each timing so an expensive stage is
visible.
"""

from __future__ import annotations

import argparse
import ctypes
from collections.abc import Callable
from typing import Any

from py4gw import (
    CharContext,
    CharContextStruct,
    PatternCatalog,
    PerfCounter,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class CountingReader:
    """Count calls and bytes while forwarding reads to the real reader."""

    def __init__(self, reader: ProcessMemoryReader) -> None:
        """Wrap one already-open process reader."""

        self._reader = reader
        self.read_count = 0
        self.byte_count = 0

    def read(self, address: int, size: int) -> bytes:
        """Forward one read and record its requested size."""

        self.read_count += 1
        self.byte_count += size
        return self._reader.read(address, size)

    def mark(self) -> tuple[int, int]:
        """Return counters that can be used as the next stage baseline."""

        return self.read_count, self.byte_count

    def since(self, mark: tuple[int, int]) -> tuple[int, int]:
        """Return reads and bytes performed since ``mark``."""

        return self.read_count - mark[0], self.byte_count - mark[1]


def measure_stage(
    counter: PerfCounter,
    reader: CountingReader,
    name: str,
    operation: Callable[[], Any],
    samples: int,
) -> None:
    """Measure one operation repeatedly and print timing/read statistics."""

    reads: list[int] = []
    byte_counts: list[int] = []
    for _ in range(samples):
        mark = reader.mark()
        counter.start(name)
        try:
            operation()
        finally:
            counter.end(name)
        read_count, byte_count = reader.since(mark)
        reads.append(read_count)
        byte_counts.append(byte_count)

    report = counter.calculate_report(name)
    average_reads = sum(reads) / len(reads)
    average_bytes = sum(byte_counts) / len(byte_counts)
    print(
        f"{name:<30} "
        f"min={report.min:8.3f} ms  "
        f"avg={report.avg:8.3f} ms  "
        f"p50={report.p50:8.3f} ms  "
        f"p95={report.p95:8.3f} ms  "
        f"p99={report.p99:8.3f} ms  "
        f"max={report.max:8.3f} ms  "
        f"reads={average_reads:6.1f}  bytes={average_bytes:10.1f}"
    )


def parse_arguments() -> argparse.Namespace:
    """Read optional PID and sample-count arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pid",
        type=int,
        help="Guild Wars PID to measure (defaults to the first discovered client).",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Samples per repeated stage (default: 10).",
    )
    arguments = parser.parse_args()
    if arguments.samples <= 0:
        parser.error("--samples must be positive")
    return arguments


def main() -> int:
    """Run the live context timing harness."""

    arguments = parse_arguments()
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("No Guild Wars clients are currently running.")
        return 1

    process = next(
        (candidate for candidate in clients if int(candidate["pid"]) == arguments.pid),
        None,
    ) if arguments.pid is not None else clients[0]
    if process is None:
        print(f"Guild Wars PID {arguments.pid} was not found.")
        return 1

    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    print(f"PID: {pid}")
    print(f"Path: {process.get('path') or '—'}")
    print(f"Samples per repeated stage: {arguments.samples}")
    print()

    counter = PerfCounter()
    with ProcessMemoryReader(win32, pid) as process_reader:
        reader = CountingReader(process_reader)
        scanner = RemoteScanner(
            reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        measure_stage(
            counter,
            reader,
            "scanner.initialize",
            scanner.initialize,
            1,
        )
        text_section = scanner.get_section_range("text")
        print(
            f".text: 0x{text_section.start:08X}-0x{text_section.end:08X} "
            f"({text_section.size:,} bytes), scan chunk: 65,536 bytes"
        )
        patterns = PatternCatalog.from_directory("offsets")
        context = CharContext(reader, scanner, patterns)

        resolver = patterns.get_resolver("context.base_ptr")
        scan_step = resolver.attempts[0].steps[0]
        scan_pattern = patterns.get_pattern(scan_step.pattern_name).pattern
        if scan_pattern is None:
            raise RuntimeError("context.base_ptr does not define a scan pattern.")

        measure_stage(
            counter,
            reader,
            "context.initialize (connect)",
            context.initialize,
            1,
        )
        address = context.resolve_address()
        print(f"CharContext address: 0x{address:08X}")
        print()
        print(
            f"{'Stage':<30} min/avg/p50/p95/p99/max, remote reads and requested bytes"
        )
        print("-" * 150)
        measure_stage(
            counter,
            reader,
            "resolver.pattern_scan",
            lambda: scanner.find(scan_pattern, scan_step.section),
            arguments.samples,
        )

        scan_address = scanner.find(scan_pattern, scan_step.section)
        if scan_address is None:
            raise RuntimeError("context.base_ptr pattern was not found.")

        def read_context_pointer_chain() -> int:
            base_pointer = scanner.read_uint32(scan_address)
            base_context = scanner.read_uint32(base_pointer)
            game_context = scanner.read_uint32(base_context + 0x18)
            return scanner.read_uint32(game_context + 0x44)

        measure_stage(
            counter,
            reader,
            "resolver.pointer_chain",
            read_context_pointer_chain,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "context.resolve_address",
            context.resolve_address,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "context.read",
            context.read,
            arguments.samples,
        )

        def read_at_cached_address() -> CharContextStruct:
            raw = reader.read(address, ctypes.sizeof(CharContextStruct))
            return CharContextStruct.from_buffer_copy(raw).bind_reader(reader)

        measure_stage(
            counter,
            reader,
            "context.read.cached_address",
            read_at_cached_address,
            arguments.samples,
        )

        snapshot = context.read()
        measure_stage(
            counter,
            reader,
            "snapshot.player_name_str",
            lambda: snapshot.player_name_str,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.h0000_ptrs",
            lambda: snapshot.h0000_ptrs,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.h0014_ptrs",
            lambda: snapshot.h0014_ptrs,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.h0034_ptrs",
            lambda: snapshot.h0034_ptrs,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.h0044_ptrs",
            lambda: snapshot.h0044_ptrs,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.h00EC_ptrs",
            lambda: snapshot.h00EC_ptrs,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.observer_matches",
            lambda: snapshot.observer_matches,
            arguments.samples,
        )
        measure_stage(
            counter,
            reader,
            "snapshot.progress_bar",
            lambda: snapshot.progress_bar,
            arguments.samples,
        )

    print()
    print("The connect row includes the one-time pattern scan.")
    print("The cached resolver rows show the steady-state cost after connection.")
    print("The cached-address row isolates structure decoding from pointer resolution.")
    print("High remote-read counts identify pointer/array properties that may need batching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
