"""Read-only: why does Stealth's observer refuse to install, and where does the resolver land?

Installs nothing, writes nothing, calls no client function. It only resolves
``ui.send_ui_message_func`` against the LIVE process and compares the bytes there with the same
RVA in Gw.exe on disk. That separates two very different causes for the install refusal:

  * the resolver returns a different address live than it does from the file
    -> the client's in-memory .text differs from the file (unpacking / runtime patching), which
       also means Native's own resolution of the same name at injection time is suspect
  * the resolver returns the same address but the bytes differ
    -> something wrote over that function

It also prints every ``send_ui_message`` pattern match site, because ``to_function_start`` walks
back to the NEAREST preceding 55 8b ec, so an extra or moved match silently changes the answer.

USAGE (elevated): python live_reports/_observer_resolve_check.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from pe_image import PeImage  # noqa: E402

from py4gw import ProcessMemoryReader, RemoteScanner, Win32  # noqa: E402
from py4gw.scanner.patterns import PatternCatalog  # noqa: E402

CLIENT = Path(r"F:\GW\GW1\Gw.exe")
EXPECTED = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")
WATCH = (
    "ui.send_ui_message_func",
    "ui.send_frame_ui_message_func",
    "ui.load_settings_func",
    "ui.frame_array_addr",
)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--pattern", default="ui.send_ui_message")
    args = ap.parse_args(argv)

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: reading another process needs an elevated controller.")
        return 3
    pid = args.pid
    if not pid:
        found = win32.find_guild_wars()
        if not found:
            print("no Gw.exe process found.")
            return 2
        pid = int(found[0]["pid"])
    module = win32.get_main_module(pid)
    base, size = int(module["base_address"]), int(module["size"])
    print(f"pid {pid}   module base {base:#010x} + {size:#x}")

    image = PeImage(CLIENT)
    image_base = image.image_base
    text = image.section(".text")
    file_text = image.read_rva(text.virtual_address, text.raw_size)

    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(reader, module_base=base, module_size=size)
        scanner.initialize()
        catalog = PatternCatalog.from_directory(ROOT / "offsets")

        print("\n=== resolved names, LIVE ===")
        for name in WATCH:
            result = catalog.resolve(name, scanner)
            value = int(result.value) if result.value else 0
            live = ""
            if value:
                try:
                    head = reader.read(value, 16)
                    rva = value - base
                    offset = rva - text.virtual_address
                    on_disk = (
                        file_text[offset : offset + 16]
                        if 0 <= offset < len(file_text) - 16
                        else b""
                    )
                    live = f" live {head.hex(' ')}"
                    if on_disk:
                        live += f"\n        on-disk {on_disk.hex(' ')}"
                        live += "   <-- LIVE AND FILE DIFFER" if on_disk != head else "   (same)"
                    if head[:6] == EXPECTED[:6]:
                        live += "\n        >>> matches the expected send_ui_message entry"
                    else:
                        live += "\n        >>> NOT the expected entry (expected " + EXPECTED.hex(" ") + ")"
                except OSError as error:
                    live = f"  unreadable: {error}"
            print(f"  {name:<34} {'ok  ' if result.ok else 'FAIL'} {value:#010x} (rva {value - base:#x}){live}")

        definition = catalog.get_pattern(args.pattern)
        print(f"\n=== pattern '{args.pattern}' ===")
        print(f"  literal {definition.pattern!r}  offset {definition.offset:#x}  section .{definition.section}")
        if definition.pattern is not None:
            hits = scanner.find_all(definition.pattern, section=definition.section or "text")
            print(f"  {len(hits)} match site(s), in scan order (find() takes the FIRST):")
            for hit in hits:
                walked = scanner.to_function_start(hit, 0xFFF)
                head = reader.read(walked, 16) if walked else b""
                print(f"    match {hit:#010x} -> to_function_start {walked:#010x}  {head.hex(' ')}")
                try:
                    on_disk = image.read_rva(walked - base, 16)
                    if on_disk != head:
                        print(f"        on-disk {on_disk.hex(' ')}   <-- LIVE AND FILE DIFFER")
                except Exception:  # noqa: BLE001
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
