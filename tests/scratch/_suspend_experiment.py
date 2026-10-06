"""Attribute the client's device-lost counters to a specific step of a capability-layer connect.

The client's own log filled with Reforged's ``ImGui initialized on Guild Wars render device.`` line, which
is **one per D3D9 device-lost-and-recovered frame** (``imgui_manager.cpp:449-456``; the teardown line
``Shutting down ImGui.`` never appears, so the runtime is not restarting). The owner reports the line is
rare until this project connects, and the counts agree: 111 lines, with bursts that line up with connect
attempts and nothing at all while this project is idle.

So this runs the connect in phases, counting the client's own log around each one, to say which phase the
device notices:

    0. idle, to show the client is quiet on its own;
    1. opening and closing the write handle, which is what makes connecting a write at all;
    2. ``ConnectedClient._count_suspended_threads`` — the real method, which suspends and resumes **every**
       thread of the client once per sweep, and exists only to report a dead controller's leftovers;
    3. a whole capability-layer connect attempt, which on this client refuses before writing anything.

Nothing is patched by this script: phase 3 refuses (the entries are held by Reforged), and phases 1-2 touch
no code at all. Run it elevated, with the client running::

    python tests/scratch\1_suspend_experiment.py
"""

from __future__ import annotations

import pathlib
import time

import py4gw
from py4gw import Win32
from py4gw.client import ConnectedClient
from py4gw.win32.write_access import WriteAccess

#: Reforged's own log, and the line that counts a lost-and-recovered device.
LOG = pathlib.Path(r"F:\GW\GW1\Py4GW_injection_log.txt")
MARKER = "ImGui initialized on Guild Wars render device"

#: How long each phase waits for the client to react.
SETTLE_SECONDS = 10.0
SWEEPS = 5


def count() -> int:
    """How many device-lost-and-recovered lines the client has logged so far."""

    try:
        text = LOG.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"    (the log could not be read: {error})")
        return -1
    return sum(1 for line in text.splitlines() if MARKER in line)


def report(label: str, before: int) -> None:
    after = count()
    print(f"{label}: {after - before:+d} line(s)  (total {after})")


def main() -> int:
    clients = Win32().find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
        return 1
    pid = int(clients[0]["pid"])
    print(f"pid {pid}; every phase below counts Reforged's own device-lost line around it\n")

    before = count()
    print(f"phase 0: idle {SETTLE_SECONDS:.0f} s, nothing touching the client")
    time.sleep(SETTLE_SECONDS)
    report("phase 0", before)

    print(f"\nphase 1: open and close the write handle {SWEEPS} times (no thread is suspended)")
    before = count()
    for index in range(SWEEPS):
        access = WriteAccess(pid)
        access.close()
        time.sleep(1.0)
    time.sleep(SETTLE_SECONDS)
    report("phase 1", before)

    print(f"\nphase 2: the real _count_suspended_threads, {SWEEPS} sweeps")
    before = count()
    connection = object.__new__(ConnectedClient)
    connection._pid = pid
    access = WriteAccess(pid)
    try:
        for index in range(SWEEPS):
            previously_suspended = connection._count_suspended_threads(access)
            print(f"    sweep {index + 1}: {previously_suspended} thread(s) were already suspended")
            time.sleep(1.0)
    finally:
        access.close()
    time.sleep(SETTLE_SECONDS)
    report("phase 2", before)

    print("\nphase 3: one whole capability-layer connect attempt (refuses on this client)")
    before = count()
    try:
        py4gw.connect(pid)
        print("    connected: the entries were free on this attempt")
    except BaseException as error:  # noqa: BLE001 - the phase is the subject
        print(f"    refused: {type(error).__name__}: {str(error)[:160]}")
    finally:
        py4gw.disconnect()
    time.sleep(SETTLE_SECONDS)
    report("phase 3", before)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
