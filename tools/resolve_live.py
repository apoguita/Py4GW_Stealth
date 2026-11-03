"""Resolve ``offsets/*.json`` against the *running* client — the live counterpart of
``resolve_offline.py``.

``resolve_offline.py`` answers a claim about a *build*: it reads ``Gw.exe`` from disk and
evaluates every resolver against that snapshot. That is enough to catch a pattern that a
client update invalidated, but it is not the same image the client actually runs. The
loader relocates the module (this client sits at ``0x00220000``, not the linked
``0x00400000``) and rewrites every absolute operand the assert macro embeds, so a resolver
that reads those operands can only be proved against live memory.

This tool therefore resolves the same tables through the same ``PatternCatalog``, once
against a read-only view of the running process and once against the file on disk, and
reports whether the two agree *by RVA*. Agreement means the table describes the build the
client is running; a disagreement names exactly which resolver moved.

It reads and never writes: no connect, no hook install, no client call.

Usage:
    python tools/resolve_live.py                        # every ui resolver
    python tools/resolve_live.py ui chat                # only these namespaces
    python tools/resolve_live.py -v ui.get_child_frame_id_func   # full step trace
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(Path(__file__).resolve().parent), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gw_scan import is_entry  # noqa: E402
from pe_image import PeImage  # noqa: E402
from py4gw.memory.memory import ProcessMemoryReader  # noqa: E402
from py4gw.scanner.patterns import PatternCatalog  # noqa: E402
from py4gw.scanner.remote import RemoteScanner  # noqa: E402
from py4gw.win32 import Win32  # noqa: E402
from resolve_offline import (  # noqa: E402
    DEFAULT_CLIENT,
    HEAD_BYTES,
    FileModule,
    expected_kind,
    resolver_names,
)

DEFAULT_NAMESPACES = "ui"


def pick_client(clients: list[dict[str, object]], wanted_pid: int) -> dict[str, object] | None:
    """Return the requested client, or the only one running."""

    if wanted_pid:
        for client in clients:
            if int(client["pid"]) == wanted_pid:  # type: ignore[arg-type]
                return client
        return None
    return clients[0] if len(clients) == 1 else clients[0] if clients else None


def main(argv: list[str]) -> int:
    verbose = "-v" in argv
    wanted_pid = 0
    wanted: list[str] = []
    for item in argv:
        if item.startswith("-"):
            continue
        if item.isdigit():
            wanted_pid = int(item)
        else:
            wanted.append(item)
    if not wanted:
        wanted = [DEFAULT_NAMESPACES]

    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no running Gw.exe was found")
        return 2
    client = pick_client(clients, wanted_pid)
    if client is None:
        print(f"pid {wanted_pid} is not a running Gw.exe; running: "
              f"{[int(c['pid']) for c in clients]}")
        return 2

    pid = int(client["pid"])  # type: ignore[arg-type]
    module = win32.get_main_module(pid)
    live_base = int(module["base_address"])  # type: ignore[arg-type]
    live_size = int(module["size"])  # type: ignore[arg-type]

    exe_path = client.get("path") or DEFAULT_CLIENT
    path = Path(str(exe_path))
    if not path.is_file():
        print(f"the running client's file is not readable at {path}")
        return 2

    image = PeImage(path)
    offline_reader = FileModule(image)
    offline = RemoteScanner(offline_reader, image.image_base, image.size_of_image)
    offline.initialize()

    catalog = PatternCatalog.from_directory(ROOT / "offsets")
    names = resolver_names(ROOT / "offsets", wanted)

    print(f"=== live pid {pid}  module {live_base:#010x} size {live_size:#x}")
    print(f"=== file {path}  image base {image.image_base:#010x}")
    print(f"    {len(names)} resolver(s)")
    print()

    agree = 0
    disagree: list[str] = []
    failed: list[str] = []

    with ProcessMemoryReader(win32, pid) as reader:
        live = RemoteScanner(reader, live_base, live_size)
        live.initialize()
        text = live.get_section_range("text")

        for name in names:
            kind = expected_kind(catalog, name)
            live_result = catalog.resolve(name, live)
            offline_result = catalog.resolve(name, offline)

            if not live_result.ok or not live_result.value:
                failed.append(name)
                print(
                    f"  FAIL {name:<42} live step {live_result.failed_step or '-'} "
                    f"{live_result.message or ''}".rstrip()
                )
                if verbose:
                    for step in live_result.trace:
                        print(
                            f"        {step.name:<18} {step.operation:<18} "
                            f"in {step.input_value:#010x} -> out {step.output_value:#010x} "
                            f"{'ok' if step.ok else 'FAILED'} {step.detail or ''}".rstrip()
                        )
                continue

            live_value = int(live_result.value)
            live_rva = live_value - live_base
            offline_value = int(offline_result.value) if offline_result.ok else 0
            offline_rva = offline_value - image.image_base if offline_value else -1

            try:
                head = reader.read(live_value, HEAD_BYTES)
            except OSError as error:
                failed.append(name)
                print(f"  FAIL {name:<42} live {live_value:#010x}: {error}")
                continue

            inside = text.start <= live_value < text.end
            entry = is_entry(head) if kind == "code" else False
            if kind == "code" and offline_value and live_rva == offline_rva and inside and entry:
                agree += 1
                print(
                    f"  ok   {name:<42} live {live_value:#010x} rva {live_rva:#08x} "
                    f"entry  {head.hex(' ')}"
                )
            elif kind == "code" and offline_value and live_rva == offline_rva:
                agree += 1
                print(
                    f"  ok   {name:<42} live {live_value:#010x} rva {live_rva:#08x} "
                    f"(address, not an entry point)  {head.hex(' ')}"
                )
            elif kind == "code":
                disagree.append(name)
                detail = (
                    f"live rva {live_rva:#08x} != file rva {offline_rva:#08x}"
                    if offline_value
                    else "the file does not resolve this name"
                )
                print(f"  DIFF {name:<42} live {live_value:#010x} {detail}")
            else:
                agree += 1
                print(f"  ok   {name:<42} live {live_value:#010x} rva {live_rva:#08x} ({kind})")

            if verbose:
                for step in live_result.trace:
                    print(
                        f"        {step.name:<18} {step.operation:<18} "
                        f"in {step.input_value:#010x} -> out {step.output_value:#010x} "
                        f"{'ok' if step.ok else 'FAILED'} {step.detail or ''}".rstrip()
                    )

    print()
    print(f"{agree} agree with the file by rva; {len(disagree)} differ; {len(failed)} did not resolve")
    for name in disagree:
        print(f"    differs: {name}")
    for name in failed:
        print(f"    unresolved: {name}")
    return 0 if not disagree and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
