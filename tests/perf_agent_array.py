"""Measure repeated AgentArray view reads and nested agent-record access.

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

    value = counter.calculate_report(name)
    samples = counter.get_history(name)
    if not samples:
        return
    print(
        f"{name:<38} "
        f"min={value.min:8.3f} ms  "
        f"avg={value.avg:8.3f} ms  "
        f"p95={value.p95:8.3f} ms  "
        f"max={value.max:8.3f} ms  "
        f"samples={len(samples):3d}"
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

    counter.start(name)
    try:
        operation()
    finally:
        counter.end(name)


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

    counter = PerfCounter()
    client = ConnectedClient(process, win32=win32, perf_counter=counter)
    try:
        context = client.agent_array.read_context()
        agents = context.GetAgentArray()
        first_record = context.GetAgentByID(int(agents[0])) if agents else None
        if not isinstance(first_record, AgentLivingStruct):
            first_record = None

        for _ in range(arguments.samples):
            measure_nested(
                counter,
                "agent_array.context_read",
                client.agent_array.read_context,
            )
            measure_nested(
                counter,
                "agent_array.category_access",
                context.GetAgentArray,
            )
            if first_record is not None:
                measure_nested(
                    counter,
                    "agent.visible_effects",
                    lambda: first_record.visible_effects,
                )
                measure_nested(counter, "agent.equipment", lambda: first_record.equipment)
                measure_nested(counter, "agent.tags", lambda: first_record.tags)

        print(f"PID: {client.pid}")
        print(f"Samples: {arguments.samples}")
        print(f"Agent array address: 0x{client.agent_array.get_ptr():08X}")
        print(
            "Last view: "
            f"buffer=0x{int(context.agent_array.m_buffer):08X}, "
            f"size={int(context.agent_array.m_size)}, "
            f"capacity={int(context.agent_array.m_capacity)}, "
            f"raw_slots={len(context.raw_agents)}"
        )
        if first_record is not None:
            print(
                "Last living record: "
                f"agent_id={int(first_record.agent_id)}, "
                f"effects=0x{int(first_record.effects):08X}"
            )
        print()
        for name in (
            "agent_array.resolver",
            "agent_array.context_read",
            "agent_array.category_access",
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
