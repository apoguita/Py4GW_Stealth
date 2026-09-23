"""Read-only survey of live UI frames and the contexts they publish.

The frame-array route assumes three things about live data:

1. frames register interaction callbacks in ``Frame.frame_callbacks``;
2. a frame's registered ``uictl_context`` is a real object the client owns;
3. that slot, not a neighbouring field, is the context a callback receives.

This script fetches the live evidence for those assumptions.  It does not need
any particular in-game window to be open, because many frames are always
present and always keep callbacks registered.  It writes nothing to the client.

Reported per frame that registers callbacks: the callback addresses, the
``uictl_context`` slot, the ``h0008`` neighbour written from the same argument,
and the frame's own user-param field.  It then reports whether each live
callback address is one the offsets catalog can resolve, which shows how many
of the resolvable UI callbacks are genuinely registered.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from py4gw import PatternCatalog, ProcessMemoryReader, RemoteScanner, Win32
from py4gw.ui import FrameArray, FrameStruct

# Frame.field105_0x1c4 is the field Reforged reads as GetFrameUserParam.
_FRAME_USER_PARAM_OFFSET = 0x1C4


def _section_of(sections: dict[str, Any], address: int) -> str:
    """Return the module section containing an address, or a short label."""

    if address < 0x10000:
        return "null"
    for name, span in sections.items():
        if span.start <= address < span.end:
            return name
    return "outside module"


def _resolvable_callback_names() -> list[str]:
    """Return every offsets resolver name that looks like a callback target."""

    import json as _json

    names: list[str] = []
    for path in sorted(Path("offsets").glob("*.json")):
        root = _json.loads(path.read_text(encoding="utf-8"))
        namespace = str(root.get("namespace", ""))
        for name in root.get("resolvers", {}):
            if not str(name).endswith("_func"):
                continue
            qualified = f"{namespace}.{name}" if namespace else str(name)
            names.append(qualified)
    return names


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write the survey JSON here instead of the default name.",
    )
    parser.add_argument(
        "--match-timeout",
        type=int,
        default=40,
        help="Maximum resolvers to attempt to resolve (default 40).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("No Guild Wars clients are currently running.")
        return
    for process in clients:
        print(f"  PID {process['pid']}: {process['name']} — {process['path']}")

    pid = args.pid
    if pid is None:
        raw = input("Enter the PID to survey (blank to cancel): ").strip()
        if not raw:
            return
        pid = int(raw, 10)

    module = win32.get_main_module(pid)
    report: dict[str, Any] = {
        "test": "live_frame_context_survey",
        "pid": pid,
        "module": module["name"],
        "module_base": int(module["base_address"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "written_to_target": False,
    }

    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(
            reader,
            module_base=int(module["base_address"]),
            module_size=int(module["size"]),
        )
        sections = dict(scanner.initialize())
        patterns = PatternCatalog.from_directory("offsets")

        frame_array = FrameArray(reader, scanner, patterns)
        frame_array.initialize()
        header = frame_array.read_header()
        if header is None:
            print("Frame array is empty.")
            return

        slots = list(frame_array.iter_slots())
        print()
        print(f"Frame array 0x{frame_array.cached_address or 0:08X}: "
              f"{int(header.m_size)} slots, {len(slots)} valid frames")
        report["slots"] = int(header.m_size)
        report["valid_frames"] = len(slots)

        frames: list[dict[str, Any]] = []
        for frame_id, pointer in slots:
            callbacks = frame_array.read_callbacks_at(pointer)
            if not callbacks:
                continue
            entries = []
            for callback in callbacks:
                entries.append(
                    {
                        "callback": int(callback.callback),
                        "callback_section": _section_of(
                            sections, int(callback.callback)
                        ),
                        "uictl_context": int(callback.uictl_context),
                        "uictl_context_section": _section_of(
                            sections, int(callback.uictl_context)
                        ),
                        "h0008": int(callback.h0008),
                        "uictl_equals_h0008": int(callback.uictl_context)
                        == int(callback.h0008),
                    }
                )
            frames.append(
                {
                    "frame_id": frame_id,
                    "frame_address": pointer,
                    "frame_state": frame_array.read_u32(
                        pointer + FrameStruct.frame_state.offset
                    ),
                    "frame_user_param": frame_array.read_u32(
                        pointer + _FRAME_USER_PARAM_OFFSET
                    ),
                    "entries": entries,
                }
            )

        report["frames_with_callbacks"] = len(frames)
        print(f"Frames registering callbacks: {len(frames)}")

        # --- live callback addresses, grouped -------------------------------
        callback_counts: Counter[int] = Counter()
        context_counts: Counter[int] = Counter()
        for frame in frames:
            for entry in frame["entries"]:
                callback_counts[entry["callback"]] += 1
                if entry["uictl_context"] >= 0x10000:
                    context_counts[entry["uictl_context"]] += 1

        report["distinct_callbacks"] = [
            {"callback": cb, "frames": n, "section": _section_of(sections, cb)}
            for cb, n in callback_counts.most_common()
        ]
        report["distinct_contexts"] = [
            {"context": ctx, "frames": n, "first_dword_section":
                _section_of(sections, frame_array.read_u32(ctx))}
            for ctx, n in context_counts.most_common()
        ]

        print()
        print(f"Distinct registered callbacks: {len(callback_counts)}")
        for cb, n in callback_counts.most_common(20):
            print(f"  0x{cb:08X} in {_section_of(sections, cb):<16} on {n} frame(s)")

        print()
        print(f"Distinct non-null uictl_context values: {len(context_counts)}")
        for ctx, n in context_counts.most_common(20):
            first = frame_array.read_u32(ctx)
            print(
                f"  0x{ctx:08X} on {n} frame(s); first dword 0x{first:08X} "
                f"in {_section_of(sections, first)}"
            )

        # --- the +4 versus +8 question --------------------------------------
        total_entries = sum(len(f["entries"]) for f in frames)
        equal = sum(
            1
            for f in frames
            for e in f["entries"]
            if e["uictl_equals_h0008"]
        )
        both_non_null = sum(
            1
            for f in frames
            for e in f["entries"]
            if e["uictl_context"] >= 0x10000 and e["h0008"] >= 0x10000
        )
        report["entries_total"] = total_entries
        report["entries_uictl_equals_h0008"] = equal
        report["entries_both_non_null"] = both_non_null
        print()
        print(f"Callback entries:                 {total_entries}")
        print(f"  uictl_context == h0008:         {equal}")
        print(f"  both non-null:                  {both_non_null}")

        context_matches_user_param = sum(
            1
            for f in frames
            for e in f["entries"]
            if e["uictl_context"] >= 0x10000
            and e["uictl_context"] == f["frame_user_param"]
        )
        report["entries_context_equals_user_param"] = context_matches_user_param
        print(
            f"  uictl_context == frame user param: "
            f"{context_matches_user_param}"
        )

        # --- which live callbacks the catalog can name ----------------------
        names = _resolvable_callback_names()
        matched: dict[str, Any] = {}
        attempted = 0
        for name in names:
            if attempted >= args.match_timeout:
                break
            attempted += 1
            try:
                result = patterns.resolve(name, scanner)
            except (OSError, ValueError, KeyError):
                continue
            if not result.ok or result.value < 0x10000:
                continue
            if result.value in callback_counts:
                matched[name] = {
                    "address": result.value,
                    "section": _section_of(sections, result.value),
                    "frames": callback_counts[result.value],
                }

        report["resolvers_attempted"] = attempted
        report["live_callbacks_matched"] = matched
        print()
        print(f"Resolvers attempted: {attempted}; live callbacks matched: "
              f"{len(matched)}")
        for name, info in matched.items():
            print(
                f"  {name} -> 0x{info['address']:08X} in {info['section']} "
                f"on {info['frames']} frame(s)"
            )

        # --- full per-frame detail -----------------------------------------
        report["frames"] = frames
        print()
        print("Frames with at least one registered callback:")
        for frame in frames:
            entries = ", ".join(
                f"0x{e['callback']:08X}/ctx=0x{e['uictl_context']:08X}"
                for e in frame["entries"]
            )
            print(
                f"  frame {frame['frame_id']:<6} state=0x{frame['frame_state']:08X} "
                f"user_param=0x{frame['frame_user_param']:08X}  {entries}"
            )

    out_path = args.out
    if out_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path(f"live_frame_survey_{pid}_{stamp}.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print()
    print(f"Survey written to: {out_path}")
    print("No bytes were written to the client.")


if __name__ == "__main__":
    main()
