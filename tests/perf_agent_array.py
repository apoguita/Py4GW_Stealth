"""Measure repeated complete AgentArray and living-agent access.

Run from the project directory while Guild Wars is running::

    python tests/perf_agent_array.py --samples 10
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

from py4gw import AgentLivingStruct, ConnectedClient, PerfCounter, Win32


def report(counter: PerfCounter, name: str) -> None:
    """Print one timing report when the metric has completed samples."""

    value = counter.report(name)
    if value.count == 0:
        return
    print(
        f"{name:<38} "
        f"min={value.minimum_ms:8.3f} ms  "
        f"avg={value.average_ms:8.3f} ms  "
        f"p95={value.p95_ms:8.3f} ms  "
        f"max={value.maximum_ms:8.3f} ms  "
        f"samples={value.count:3d}"
    )


def parse_arguments() -> argparse.Namespace:
    """Read the optional PID and sample count."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Guild Wars PID to measure.")
    parser.add_argument(
        "--samples", type=int, default=10, help="Refresh samples (default: 10)."
    )
    arguments = parser.parse_args()
    if arguments.samples <= 0:
        parser.error("--samples must be positive")
    return arguments


def measure_nested(
    counter: PerfCounter, name: str, operation: Callable[[], Any]
) -> None:
    """Measure one nested living-record operation."""

    with counter.measure(name):
        operation()


def main() -> int:
    """Run the repeated live AgentArray measurement."""

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

    counter = PerfCounter(history_size=max(arguments.samples * 300, 32))
    client = ConnectedClient(process, win32=win32, perf_counter=counter)
    try:
        last_snapshot = None
        last_living = None
        for _ in range(arguments.samples):
            last_living = client.refresh_living_agents(counter)
            if last_living is None:
                continue
            last_snapshot = client.agent_array.living_snapshot
            first = last_living.records[0] if last_living.records else None
            if first is not None:
                record: AgentLivingStruct = first
                measure_nested(
                    counter,
                    "agent.visible_effects",
                    lambda: record.visible_effects,
                )
                measure_nested(counter, "agent.equipment", lambda: record.equipment)
                measure_nested(counter, "agent.tags", lambda: record.tags)

        print(f"PID: {client.pid}")
        print(f"Samples: {arguments.samples}")
        print(
            f"Safety limits: pointer_slots={client.agent_array.max_pointer_slots}, "
            f"references={client.agent_array.max_references}"
        )
        if last_snapshot is not None:
            print(
                "Last living snapshot: "
                f"records={last_snapshot.count}, "
                f"generation={last_snapshot.generation}, "
                f"stale={last_snapshot.stale_count}, "
                f"unreadable={last_snapshot.unreadable_count}"
            )
        if last_living is not None:
            print(f"Last snapshot age: {last_living.age_ms:.3f} ms")
        print()
        for name in (
            "agent_array.resolver",
            "agent_array.read",
            "agent_array.pointer_table",
            "agent_array.context_read",
            "agent_array.movement_table",
            "agent_array.classification",
            "agent_array.living_refresh",
            "agent_array.reference_validation",
            "agent_array.agent_record",
            "agent.visible_effects",
            "agent.equipment",
            "agent.tags",
        ):
            report(counter, name)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
