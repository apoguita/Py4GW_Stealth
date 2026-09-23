"""Guided, read-only preflight for the salvage-session frame route.

The salvage session is published only while the in-game salvage window is
open, so this test is driven by you: it polls the client and reports the
moment the window appears and the moment it closes.  You open and close the
window yourself.

This script writes NOTHING into ``Gw.exe``.  It has no hook, no payload, no
patch, no remote allocation, and no remote thread.  It never clicks, never
sends input, and never opens or closes the in-game window for you.  There is
nothing to roll back because nothing in the client is modified.

How to use it:

1. Start Guild Wars and log a character in.
2. Run this script and pick the client's PID.
3. Open the salvage window in game (use a salvage kit on an item).
4. Watch for ``APPEARED``; the script prints the session fields it read.
5. Close the salvage window and watch for ``CLEARED``.
6. Press Ctrl+C when finished; the collected evidence is written to JSON.

A confirmed result needs both transitions plus a successful structure read.
The frame-id cross-check accepts a candidate only when the frame id stored
inside the session equals the index of the frame that published it, so a
confirmed read is not a coincidence.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from py4gw import (
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    SalvageSessionInfo,
    Win32,
)
from py4gw.ui import FrameArray, FrameTree

_CALLBACK_RESOLVER = "item.salvage_popup_uicallback_func"

# The native record stores its owning frame id right after the vtable pointer.
_SESSION_FIELDS = (
    "vtable",
    "frame_id",
    "item_id",
    "salvagable_1",
    "salvagable_2",
    "salvagable_3",
    "chosen_salvagable",
    "h001c",
    "kit_id",
)


def _section_of(sections: dict[str, Any], address: int) -> str:
    """Return the module section containing an address, or ``outside``."""

    for name, span in sections.items():
        if span.start <= address < span.end:
            return name
    return "outside the module"


def _parse_args() -> argparse.Namespace:
    """Parse the client-selection and watch-timing switches."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pid",
        type=int,
        default=None,
        help="Inspect this PID instead of prompting for one.",
    )
    parser.add_argument(
        "--watch",
        type=float,
        default=180.0,
        help="Seconds to keep sampling before giving up (default 180).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between samples (default 0.5).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write the evidence JSON here instead of the default name.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print state changes, not the periodic heartbeat.",
    )
    return parser.parse_args()


def _select_pid(win32: Win32, requested: int | None) -> int | None:
    """Return the PID to inspect, or ``None`` when the user cancels."""

    clients = win32.find_guild_wars()
    if not clients:
        print("No Guild Wars clients are currently running.")
        return None

    print("Running Guild Wars clients:")
    for process in clients:
        print(f"  PID {process['pid']}: {process['name']} — {process['path']}")

    if requested is not None:
        selected = next(
            (p for p in clients if int(p["pid"]) == requested), None
        )
        if selected is None:
            print(f"PID {requested} is not in the listed Guild Wars clients.")
            return None
        return requested

    raw = input("Enter the PID to inspect (blank to cancel): ").strip()
    if not raw:
        print("Cancelled; no client was opened.")
        return None
    try:
        pid = int(raw, 10)
    except ValueError:
        print("PID must be a decimal number.")
        return None
    if not any(int(p["pid"]) == pid for p in clients):
        print(f"PID {pid} is not in the listed Guild Wars clients.")
        return None
    return pid


def _sample(
    reader: Any,
    scanner: RemoteScanner,
    patterns: PatternCatalog,
    session: SalvageSessionInfo,
    sections: dict[str, Any],
    callback_cache: dict[str, Any],
) -> dict[str, Any]:
    """Take one read-only observation of the salvage route."""

    observation: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": "unknown",
        "detail": "",
        "callback_address": callback_cache.get("address"),
        "callback_section": callback_cache.get("section"),
        "candidates": [],
        "session": None,
    }

    if callback_cache.get("address") is None:
        resolution = patterns.resolve(_CALLBACK_RESOLVER, scanner)
        if not resolution.ok:
            observation["state"] = "error"
            observation["detail"] = (
                f"{_CALLBACK_RESOLVER} failed: "
                f"{resolution.message or 'no address'}"
            )
            return observation
        callback_cache["address"] = resolution.value
        callback_cache["section"] = _section_of(sections, resolution.value)
        observation["callback_address"] = resolution.value
        observation["callback_section"] = callback_cache["section"]

    try:
        candidates = session.candidates()
    except (OSError, ValueError, RuntimeError) as error:
        observation["state"] = "error"
        observation["detail"] = f"frame lookup failed: {error}"
        return observation

    for candidate in candidates:
        observation["candidates"].append(
            {
                "frame_id": candidate.frame_id,
                "frame_address": candidate.frame_address,
                "context_address": candidate.context_address,
                "context_frame_id": candidate.context_frame_id,
                "confirmed": candidate.is_confirmed,
                "rejection": candidate.rejection,
            }
        )

    confirmed = [c for c in candidates if c.is_confirmed]
    if not confirmed:
        observation["state"] = "closed"
        if candidates:
            observation["detail"] = (
                "the salvage frame exists but published no valid session"
            )
        return observation

    observation["state"] = "open"
    address = confirmed[0].context_address
    try:
        snapshot = session.read()
    except (OSError, ValueError) as error:
        observation["state"] = "error"
        observation["detail"] = f"structure read failed: {error}"
        return observation
    if snapshot is None:
        observation["state"] = "error"
        observation["detail"] = "a confirmed candidate read back as nothing"
        return observation

    values: dict[str, Any] = {
        name: int(getattr(snapshot, name)) for name in _SESSION_FIELDS
    }
    values["vtable_section"] = _section_of(sections, int(values["vtable"]))
    observation["session"] = values
    observation["detail"] = f"session at 0x{address:08X}"
    return observation


def _describe(observation: dict[str, Any]) -> str:
    """Render one observation as a readable line."""

    if observation["state"] == "error":
        return f"ERROR: {observation['detail']}"
    if observation["state"] == "closed":
        detail = observation["detail"] or "no salvage frame registers the callback"
        return f"no open salvage session ({detail})"
    if observation["state"] != "open":
        return f"unknown state: {observation['detail']}"

    values = observation["session"] or {}
    return (
        f"session at {observation['detail'].split(' at ')[-1]} — "
        f"frame_id={values.get('frame_id')} item_id={values.get('item_id')} "
        f"salvagable=({values.get('salvagable_1')}, "
        f"{values.get('salvagable_2')}, {values.get('salvagable_3')}) "
        f"chosen={values.get('chosen_salvagable')} "
        f"kit_id={values.get('kit_id')} "
        f"vtable={values.get('vtable_section')}"
    )


def main() -> None:
    """Poll the salvage route until the user stops or the watch expires."""

    args = _parse_args()
    win32 = Win32()
    pid = _select_pid(win32, args.pid)
    if pid is None:
        return

    module = win32.get_main_module(pid)
    evidence: dict[str, Any] = {
        "test": "salvage_session_frame_route",
        "pid": pid,
        "module": module["name"],
        "module_base": int(module["base_address"]),
        "module_size": int(module["size"]),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "callback_resolver": _CALLBACK_RESOLVER,
        "callback_address": None,
        "callback_section": None,
        "transitions": [],
        "samples": 0,
        "observed_open": False,
        "written_to_target": False,
    }

    print()
    print(f"Selected PID {pid}; module {module['name']} at "
          f"0x{int(module['base_address']):08X}")
    print("This test is READ-ONLY: it writes nothing to the client.")
    print()
    print("Now open the salvage window in game (use a salvage kit on an item).")
    print("Watch for APPEARED, then close the window and watch for CLEARED.")
    print("Press Ctrl+C when you are finished.")
    print()

    callback_cache: dict[str, Any] = {}
    previous_state: str | None = None
    opened_once = False
    deadline = time.monotonic() + max(args.watch, 1.0)
    interval = max(args.interval, 0.05)
    heartbeat = 0
    last_state = "unknown"

    try:
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                module_base=int(module["base_address"]),
                module_size=int(module["size"]),
            )
            sections = dict(scanner.initialize())
            patterns = PatternCatalog.from_directory("offsets")

            frame_array = FrameArray(reader, scanner, patterns)
            try:
                frame_array.initialize()
            except (OSError, ValueError, RuntimeError) as error:
                print(f"Frame array resolver failed: {error}")
                print("No frame walk was attempted; nothing was modified.")
                return
            print(
                f"Frame array resolved at "
                f"0x{frame_array.cached_address or 0:08X} "
                f"({frame_array.size()} slots)."
            )

            session = SalvageSessionInfo(
                reader,
                scanner,
                patterns,
                FrameTree(frame_array, scanner.function_from_near_call),
            )

            while time.monotonic() < deadline:
                observation = _sample(
                    reader, scanner, patterns, session, sections, callback_cache
                )
                evidence["samples"] += 1
                evidence["callback_address"] = observation["callback_address"]
                evidence["callback_section"] = observation["callback_section"]

                state = observation["state"]
                last_state = state

                if state == "open":
                    evidence["observed_open"] = True
                    evidence["session"] = observation["session"]

                if state != previous_state:
                    transitions = {
                        "open": "APPEARED",
                        "closed": "CLEARED",
                        "error": "ERROR",
                    }
                    label = transitions.get(state, state.upper())
                    if state == "open" and opened_once:
                        label = "REAPPEARED"
                    if state == "open":
                        opened_once = True
                    evidence["transitions"].append(
                        {
                            "timestamp": observation["timestamp"],
                            "event": label,
                            "detail": _describe(observation),
                            "candidates": observation["candidates"],
                            "session": observation["session"],
                        }
                    )
                    print(f"[{observation['timestamp']}] {label}: "
                          f"{_describe(observation)}")
                    if state == "open":
                        for name in _SESSION_FIELDS:
                            value = (observation["session"] or {}).get(name)
                            print(f"    {name:<20} {value}")
                        print(
                            "    "
                            f"{'vtable_section':<20} "
                            f"{(observation['session'] or {}).get('vtable_section')}"
                        )
                    previous_state = state
                elif not args.quiet and heartbeat % 20 == 0:
                    print(f"  ...{evidence['samples']} samples; "
                          f"state={state}")

                heartbeat += 1
                time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print("Stopped by the user.")

    evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
    evidence["final_state"] = last_state

    out_path = args.out
    if out_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path(f"salvage_preflight_{pid}_{stamp}.json")
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print()
    print(f"Samples taken:            {evidence['samples']}")
    print(f"Salvage session observed: {'yes' if evidence['observed_open'] else 'no'}")
    print(f"Transitions recorded:     {len(evidence['transitions'])}")
    print(f"Evidence written to:      {out_path}")
    print("No bytes were written to the client at any point.")
    if not evidence["observed_open"]:
        print()
        print("No session was confirmed. Check in order:")
        print("  1. the callback resolved inside .text (see the line above)")
        print("  2. the salvage window was actually open during a sample")
        print("  3. the frame's uictl_context is non-null while it is open")
        print("If the callback is registered but never yields a context, this")
        print("route does not work for the salvage context and the callback")
        print("capture in docs/CALLBACK_POINTER_RESEARCH.md is the fallback.")


if __name__ == "__main__":
    main()
