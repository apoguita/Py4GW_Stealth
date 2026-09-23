"""Read-only inspection of the UI frame route to the frame-published contexts.

Three contexts are published only through a UI frame callback: the world map,
the mission map, and the salvage session.  This script resolves the client's
UI frame array, finds the frame that registered each context's callback, and
reports the candidate that frame publishes.

It writes nothing: no hook, no payload, no patch, no remote allocation, and no
map or popup control.  The operator opens and closes the in-game surface
manually between samples.

The frame-id cross-check is the evidence that matters.  A candidate is only
confirmed when the frame id stored inside the context equals the index of the
frame that published it.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any, Callable

from py4gw import (
    MissionMapContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    SalvageSessionInfo,
    Win32,
    WorldMapContext,
)
from py4gw.ui import FrameArray, FrameTree

_STATE_RESOLVER = "ui.world_map_state_addr"
_WORLD_MAP_SHOWING_BIT = 0x80000


@dataclass(frozen=True)
class _route:
    """One frame-published context and how to report its snapshot."""

    label: str
    callback_resolver: str
    reader: Any
    summarize: Callable[[Any], str]


def _read_u32(reader: Any, address: int) -> int | None:
    """Read one target dword, returning ``None`` when it is unreadable."""

    try:
        return int.from_bytes(reader.read(address, 4), "little")
    except OSError:
        return None


def _world_map_showing(
    reader: Any, patterns: PatternCatalog, scanner: RemoteScanner
) -> str:
    """Report the independent world-map visibility flag, if it resolves."""

    result = patterns.resolve(_STATE_RESOLVER, scanner)
    if not result.ok:
        return f"unresolved ({_STATE_RESOLVER}: {result.message or 'no address'})"
    value = _read_u32(reader, result.value)
    if value is None:
        return f"unreadable at 0x{result.value:08X}"
    showing = (value & _WORLD_MAP_SHOWING_BIT) != 0
    return f"0x{value:08X} -> WorldMap {'showing' if showing else 'not showing'}"


def _summarize_world(snapshot: Any) -> str:
    return (
        f"frame_id={snapshot.frame_id} zoom={snapshot.zoom:.4f} "
        f"top_left=({snapshot.top_left.x:.2f}, {snapshot.top_left.y:.2f}) "
        f"bottom_right=({snapshot.bottom_right.x:.2f}, "
        f"{snapshot.bottom_right.y:.2f})"
    )


def _summarize_mission(snapshot: Any) -> str:
    return (
        f"frame_id={snapshot.frame_id} "
        f"size=({snapshot.size.x:.2f}, {snapshot.size.y:.2f}) "
        f"last_mouse=({snapshot.last_mouse_location.x:.2f}, "
        f"{snapshot.last_mouse_location.y:.2f}) "
        f"h003c=0x{int(snapshot.h003c):08X}"
    )


def _summarize_salvage(snapshot: Any) -> str:
    return (
        f"frame_id={snapshot.frame_id} item_id={snapshot.item_id} "
        f"salvagable=({snapshot.salvagable_1}, {snapshot.salvagable_2}, "
        f"{snapshot.salvagable_3}) "
        f"chosen={snapshot.chosen_salvagable} kit_id={snapshot.kit_id}"
    )


def _build_routes(
    reader: Any,
    scanner: RemoteScanner,
    patterns: PatternCatalog,
    tree: FrameTree,
) -> tuple[_route, ...]:
    """Construct the three frame-published context readers."""

    world = WorldMapContext(reader, scanner, patterns, tree)
    mission = MissionMapContext(reader, scanner, patterns, tree)
    salvage = SalvageSessionInfo(reader, scanner, patterns, tree)

    return (
        _route(
            "WorldMapContext",
            world.callback_resolver,
            world,
            _summarize_world,
        ),
        _route(
            "MissionMapContext",
            mission.callback_resolver,
            mission,
            _summarize_mission,
        ),
        _route(
            "SalvageSessionInfo",
            salvage.callback_resolver,
            salvage,
            _summarize_salvage,
        ),
    )


def _section_of(sections: dict[str, Any], address: int) -> str:
    """Return the module section containing an address, or ``unknown``."""

    for name, span in sections.items():
        if span.start <= address < span.end:
            return name
    return "outside the module"


def _report_route(
    route: _route,
    patterns: PatternCatalog,
    scanner: RemoteScanner,
    sections: dict[str, Any],
    verbose: bool = True,
) -> bool:
    """Report one route and return whether a candidate was confirmed."""

    resolution = patterns.resolve(route.callback_resolver, scanner)
    if not resolution.ok:
        if verbose:
            print(f"  {route.label}")
            print(
                f"    callback:            unresolved "
                f"({route.callback_resolver}: "
                f"{resolution.message or 'no address'})"
            )
        return False

    try:
        candidates = route.reader.candidates()
    except (OSError, ValueError, RuntimeError) as error:
        if verbose:
            print(f"  {route.label}")
            print(f"    frames:              lookup failed ({error})")
        return False

    confirmed = [c for c in candidates if c.is_confirmed]

    if not verbose and not candidates:
        return False

    print(f"  {route.label}")
    section = _section_of(sections, resolution.value)
    warning = "" if section == ".text" else "  <-- NOT .text; resolver suspect"
    print(f"    callback:            0x{resolution.value:08X} in {section}{warning}")

    if not candidates:
        print("    frames:              no frame registers this callback")
        return False

    for candidate in candidates:
        state = "CONFIRMED" if candidate.is_confirmed else "rejected"
        print(
            f"    frame {candidate.frame_id}: context "
            f"0x{candidate.context_address:08X} [{state}]"
        )
        if candidate.rejection:
            print(f"      reason: {candidate.rejection}")

    if not confirmed:
        return False

    try:
        snapshot = route.reader.read()
    except (OSError, ValueError) as error:
        print(f"    structure read failed: {error}")
        return False
    if snapshot is None:
        print("    structure read returned nothing for a confirmed candidate")
        return False
    print(f"    values:              {route.summarize(snapshot)}")
    return True


def _report_sample(
    reader: Any,
    scanner: RemoteScanner,
    patterns: PatternCatalog,
    frame_array: FrameArray,
    routes: tuple[_route, ...],
    sections: dict[str, Any],
    verbose: bool = True,
) -> tuple[str, ...]:
    """Print one read-only sample and return the confirmed route labels."""

    if verbose:
        print(
            f"  World-map state flag:   "
            f"{_world_map_showing(reader, patterns, scanner)}"
        )

    try:
        header = frame_array.read_header()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"  Frame array:            unreadable ({error})")
        return ()

    if header is None:
        print("  Frame array:            empty")
        return ()

    if verbose:
        print(
            f"  Frame array:            header "
            f"0x{frame_array.cached_address or 0:08X}, "
            f"{int(header.m_size)} slots (capacity {int(header.m_capacity)})"
        )
        print()

    confirmed: list[str] = []
    for route in routes:
        if _report_route(route, patterns, scanner, sections, verbose):
            confirmed.append(route.label)
    return tuple(confirmed)


def _parse_args() -> argparse.Namespace:
    """Parse the optional non-interactive switches."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pid",
        type=int,
        default=None,
        help="Inspect this PID instead of prompting for one.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Take a single sample and exit instead of prompting to repeat.",
    )
    parser.add_argument(
        "--watch",
        type=float,
        default=0.0,
        help=(
            "Poll for this many seconds instead of prompting between samples. "
            "Use this when a surface is only open for a short time."
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between samples in --watch mode (default 0.5).",
    )
    return parser.parse_args()


def main() -> None:
    """Sample the read-only frame routes for one selected client."""

    args = _parse_args()
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("No Guild Wars clients are currently running.")
        return

    print("Running Guild Wars clients:")
    for process in clients:
        print(f"  PID {process['pid']}: {process['name']} — {process['path']}")

    if args.pid is None:
        raw_pid = input("Enter the PID to inspect (blank to cancel): ").strip()
        if not raw_pid:
            print("Cancelled; no client was opened.")
            return
    else:
        raw_pid = str(args.pid)

    try:
        selected_pid = int(raw_pid, 10)
    except ValueError:
        print("PID must be a decimal number.")
        return

    selected = next(
        (process for process in clients if int(process["pid"]) == selected_pid),
        None,
    )
    if selected is None:
        print(f"PID {selected_pid} is not in the listed Guild Wars clients.")
        return

    module = win32.get_main_module(selected_pid)
    with ProcessMemoryReader(win32, selected_pid) as reader:
        scanner = RemoteScanner(
            reader,
            module_base=int(module["base_address"]),
            module_size=int(module["size"]),
        )
        scanner.initialize()
        sections = dict(scanner.initialize())
        patterns = PatternCatalog.from_directory("offsets")

        frame_array = FrameArray(reader, scanner, patterns)
        try:
            frame_array.initialize()
        except (OSError, ValueError, RuntimeError) as error:
            print(f"Frame array resolver failed: {error}")
            print("No frame walk was attempted.")
            return

        routes = _build_routes(
            reader,
            scanner,
            patterns,
            FrameTree(frame_array, scanner.function_from_near_call),
        )

        print()
        print(f"Selected PID: {selected_pid}")
        print(f"Module: {module['name']} at 0x{int(module['base_address']):08X}")
        if args.watch > 0:
            print(
                f"Polling for {args.watch:.0f}s every {args.interval:.1f}s. Open the "
                "world map, the mission map, or the salvage window now."
            )
        else:
            print("Read-only samples follow. Open or close the map or the salvage")
            print("popup, then sample again. The script never controls the client.")

        previous_confirmed: tuple[str, ...] | None = None
        deadline = time.monotonic() + args.watch
        interval = max(args.interval, 0.05)
        samples = 0

        while True:
            print()
            if args.watch > 0:
                # Poll quietly and print route detail only when a surface
                # actually publishes a context, so the loop stays readable.
                confirmed = _report_sample(
                    reader,
                    scanner,
                    patterns,
                    frame_array,
                    routes,
                    sections,
                    verbose=False,
                )
                samples += 1
                if confirmed != previous_confirmed:
                    if confirmed:
                        print(f"  [{samples}] CONFIRMED: {', '.join(confirmed)}")
                    else:
                        print(f"  [{samples}] confirmed now: none")
                    previous_confirmed = confirmed
                if time.monotonic() >= deadline:
                    break
                time.sleep(interval)
                continue

            _report_sample(
                reader, scanner, patterns, frame_array, routes, sections
            )
            if args.once:
                break
            answer = input(
                "Press Enter to sample again, or type q to finish: "
            ).strip().lower()
            if answer == "q":
                break

    print()
    print("Read-only frame-route inspection complete; no bytes were written.")
    print(
        "A confirmed candidate means the frame-id cross-check passed. It does not "
        "prove the callback dereferences the same slot; that stays inferred until "
        "confirmed against a hook or the surface's open/close transition."
    )


if __name__ == "__main__":
    main()
