"""Live probe: the disconnect sequence the 11:19 crash followed, replayed exactly.

**Why this exists.** The owner reported that the client crashed the moment they selected it and moved the
character, on an input-path assertion (`FrMouse.cpp:529`), against the client pid that this project's
11:02:48 run had installed hooks into. The suspected mechanism is in the teardown:
`Hooker.remove(name, free_code=True)` restores the target's own bytes, sleeps a fixed
`FREE_WAIT_SECONDS = 0.25`, and then frees the stub, trampoline and state block
(`py4gw/game_thread/hooker.py:734-757`) — where native waits on a **counter** instead, polling
`g_active_render_hooks` to zero (`render.cpp:61-73`). This run does exactly what the 11:02:48 run did and
nothing else, so that whatever happens next can be attributed without argument.

**What it does, in order:**

1. reads the four hook targets' own first bytes **before touching anything** — a prologue means the client is
   clean, a leading `E9` means some controller's patch is still in place (this is a read, on the read-only
   connection, so step 1 cannot itself leave anything behind);
2. connects with the write connection, which installs the game-thread hook, the message observer, the effects
   observer and the render capture;
3. reads the capture's slot the way the earlier run did, and records the hit counters;
4. disconnects — which is the step under suspicion: `ConnectedClient.close` passes
   `free_allocations=True`, so that is where generated code is unmapped;
5. records what the bridge says about its own hooks **after** the disconnect, and how long teardown took.

Then it prints the one thing it needs from the owner, and exits. **Nothing else should be run against the
client afterwards**; the whole point is that the next thing to touch it is a human moving the character.

Usage: (elevated) python tests/probe_crash_repro.py [report-path]
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The four functions this project hooks, by their catalog names.
TARGETS = (
    "game_thread.leave_game_thread_func",
    "ui.send_ui_message_func",
    "effects.post_process_effect_func",
    "render.end_scene_func",
)

#: How many bytes of each target to read in the pre-flight.
HEAD_BYTES = 8

#: A prologue is what an unpatched function starts with; a jump is a controller's patch.
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")

#: How long to wait for the capture to have seen a frame.
WAIT_SECONDS = 8.0


def main() -> int:
    report: dict[str, Any] = {"started_at": datetime.now().isoformat(timespec="seconds")}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    # 1. Pre-flight, read-only: is anything patched right now?
    with py4gw.connect(process, game_thread=False) as probe_client:
        scanner = probe_client._scanner  # type: ignore[attr-defined]
        before = []
        for name in TARGETS:
            row: dict[str, Any] = {"name": name}
            try:
                result = probe_client._patterns.resolve(name, scanner)  # type: ignore[attr-defined]
                row["address"] = hex(int(result.value))
                head = probe_client.reader.read(int(result.value), HEAD_BYTES)
                row["head"] = head.hex(" ")
                row["patched"] = head[:1] == b"\xe9"
                row["looks_like_a_prologue"] = any(
                    head.startswith(prefix) for prefix in ENTRY_PREFIXES
                )
            except Exception as error:  # noqa: BLE001 - reported, not raised
                row["error"] = f"{type(error).__name__}: {error}"
            before.append(row)
        report["before_install"] = before
        report["any_patched_before"] = any(row.get("patched") for row in before)

    # 2. The same install the 11:02:48 run made.
    bridge: Any = None
    with py4gw.connect(process) as client:
        bridge = client._bridge
        hooker = bridge.require_hooker()
        report["installed_hooks"] = sorted(hooker.installed)
        report["observing"] = bool(bridge.observing)
        report["observing_effects"] = bool(bridge.observing_effects)
        report["observing_render"] = bool(bridge.observing_render)

        # 3. The read the earlier run made, so the two runs match step for step.
        deadline = time.time() + WAIT_SECONDS
        context = 0
        while time.time() < deadline:
            context = int(bridge.render_context_address())
            if context:
                break
            time.sleep(0.02)
        report["render_context"] = hex(context)
        report["hits"] = {name: hooker.hits(name) for name in hooker.installed}
        report["context_before_disconnect"] = bool(bridge.render_context_address())

    # 4. The disconnect has run by here -- this is the step under suspicion.
    removed_at = datetime.now().isoformat(timespec="seconds")
    report["disconnected_at"] = removed_at
    if bridge is not None:
        report["after_disconnect"] = {
            "installed_hooks": sorted(bridge.require_hooker().installed),
            "observing": bool(bridge.observing),
            "observing_effects": bool(bridge.observing_effects),
            "observing_render": bool(bridge.observing_render),
        }
    report["finished_at"] = datetime.now().isoformat(timespec="seconds")
    report["next"] = (
        "NOW: click into the client and move the character. Nothing else is running and the four hooks are "
        "out, so whatever happens next is attributable. Report what the client does."
    )

    code = write_report(report)
    print("\n" + report["next"], flush=True)
    return code


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
