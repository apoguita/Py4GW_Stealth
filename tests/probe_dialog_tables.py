"""Read-only probe: do the dialog metadata tables resolve against the live client?

The port of ``dialog_patterns.cpp`` turns five hardcoded client virtual addresses into
live ones, validates 58 table rows, and falls back to a heuristic ``.rdata`` scan when
they do not validate. Nothing about that is provable offline: the addresses come from
the source, and only the running client can say whether they are the right ones for
*this* build.

This probe answers that and nothing else. It reads; it patches nothing, hooks nothing and
sends nothing, so it connects with ``game_thread=False``.

What a pass looks like, and why each part is evidence:

- the five bases land at ``module_base + (0x00913920 - 0x400000)`` and its neighbours,
  which is ``ToRuntimeAddress`` applied to ``DialogMemory`` — if the module were linked
  against a different base, this is where it would show;
- the validation pass accepts the rows: every ``flags`` word at or below ``0xFFFF``,
  every nonzero event handler inside ``.text``, and at least one row enabled. That pass
  is the source's own check, so it is the source's definition of "these are the tables";
- the enabled rows are then readable as dialogs, with the columns the source names.

Run it from an elevated shell: ``py4gw.connect()`` asserts elevation because connecting
is a write by default, and the assertion is made before the read-only path is chosen.
"""

from __future__ import annotations

import os
import sys


class _Tee:
    """Write to the console and to a report file at once.

    The probe runs elevated, and an elevated child started from a normal shell cannot
    have its output redirected by the caller on this machine: the redirect is set up by
    the shell that is not elevated, and the file never appears. So the probe writes its
    own report when a path is given on the command line.
    """

    def __init__(self, stream: object, path: str) -> None:
        self._stream = stream
        self._file = open(path, "w", encoding="utf-8")

    def write(self, text: str) -> int:
        self._stream.write(text)  # type: ignore[attr-defined]
        self._file.write(text)
        return len(text)

    def flush(self) -> None:
        self._stream.flush()  # type: ignore[attr-defined]
        self._file.flush()

    def close(self) -> None:
        self._file.close()


import py4gw
from py4gw import dialog
from py4gw.map import Map


def main() -> int:
    """Run the probe, writing the report to the path given as the first argument.

    An elevated child does not inherit the environment of the shell that started it, and
    its console is not the one the caller can read, so the report path is an argument:
    ``python -m tests.probe_dialog_tables <report-path>``.
    """

    report = sys.argv[1] if len(sys.argv) > 1 else ""
    tee = _Tee(sys.stdout, report) if report else None
    if tee is not None:
        sys.stdout = tee  # type: ignore[assignment]
    try:
        return _run()
    finally:
        if tee is not None:
            sys.stdout = sys.__stdout__
            tee.close()


def _run() -> int:
    processes = [
        process
        for process in py4gw.win32.list_processes()
        if str(process.get("name", "")).lower().endswith("gw.exe")
    ]
    if not processes:
        print("no Gw.exe found. Start the client and run this again.")
        return 1

    process = processes[0]
    pid = int(process["pid"])
    print(f"connecting read-only to pid {pid} ({process.get('name')})")

    client = py4gw.connect(pid, game_thread=False)
    try:
        tables = client.dialog_tables
        resolved = tables.get()

        module_base = int(py4gw.win32.Win32().get_main_module(pid)["base_address"])
        raw = {
            "event_handler_base": 0x00913918,
            "frame_type_base": 0x0091391C,
            "flags_base": 0x00913920,
            "content_id_base": 0x00913924,
            "property_id_base": 0x00913928,
        }
        print(f"\nmodule base 0x{module_base:08X}")

        # Which stage supplied the bases is the question this probe exists to answer, and
        # it is answered by arithmetic: the static stage can only produce one of the
        # rebasings of the five DialogMemory addresses, and anything else came from the
        # .rdata scan. Both candidate rebasings are printed so the answer is visible
        # rather than asserted.
        matched_static = True
        for name, va in raw.items():
            actual = getattr(resolved, name)
            at_400000 = module_base + (va - 0x00400000)
            at_module_base = module_base + (va - module_base)
            is_static = actual in (at_400000, at_module_base)
            matched_static = matched_static and is_static
            print(
                f"  {name:<20} resolved 0x{actual:08X}   "
                f"static candidates 0x{at_400000:08X} / 0x{at_module_base:08X}"
                f"   {'static' if is_static else 'NOT static'}"
            )

        print(f"\ntables resolved: {resolved.resolved}")
        print(f"map ready: {Map.IsMapReady()}")
        print(
            "\nstage: "
            + (
                "the hardcoded DialogMemory addresses validated"
                if matched_static
                else "the static addresses did NOT validate on this build, so the "
                ".rdata fallback scan supplied the bases (dialog_patterns.cpp:199-225)"
            )
        )

        if not resolved.flags_base:
            print(
                "\nno table resolved: the validation pass refused every stage, so "
                "every reader returns its documented zero."
            )
            return 2

        print("\nthe five columns, for the rows the client has enabled:")
        enabled = 0
        for dialog_id in range(dialog.MAX_DIALOG_ID + 1):
            flags = dialog.PyDialog.read_dialog_flags(dialog_id)
            if not (flags & 0x1):
                continue
            enabled += 1
            print(
                f"  id {dialog_id:>3}   flags 0x{flags:04X}"
                f"  frame_type {dialog.PyDialog.read_dialog_frame_type(dialog_id):>3}"
                f"  handler 0x{dialog.PyDialog.read_dialog_event_handler(dialog_id):08X}"
                f"  content_id {dialog.PyDialog.read_dialog_content_id(dialog_id):>6}"
                f"  property_id {dialog.PyDialog.read_dialog_property_id(dialog_id):>6}"
                f"  available {dialog.PyDialog.is_dialog_available(dialog_id)}"
            )
        print(f"\n{enabled} of {dialog.MAX_DIALOG_ID + 1} rows are enabled")

        loader = tables.resolve_loader_get_text()
        print(f"DialogLoader_GetText rebased to 0x{loader:08X}")
        return 0
    finally:
        client.close()
        print("\nclosed; nothing was written to the client.")


if __name__ == "__main__":
    sys.exit(main())
