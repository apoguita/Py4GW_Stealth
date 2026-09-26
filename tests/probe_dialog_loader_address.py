"""Read-only probe: what the port rebases `DialogLoader_GetText` to, and what is there.

The 2026-09-25 crash put the port's call at `0x0079EEF0`, the sources' **unrebased** constant.
The PE header says the client was linked at `0x400000` and it is loaded at `0x610000`, so the
rebased address should be `0x9AEEF0`. This probe prints what the live client reports for both —
the scanner's image base, what the resolver returns, and the bytes at each address — and calls
nothing.

Usage: (elevated) python tests/probe_dialog_loader_address.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The sources' constant (``DialogMemory::DIALOG_LOADER_GETTEXT``) and the addresses around it
#: that are worth looking at: the unrebased value, the value rebased by the PE image base, and
#: the value rebased as if the image base were the module base.
CONSTANT = 0x0079EEF0
LINK_IMAGE_BASE = 0x00400000

#: How many bytes to read at each address.
HEAD = 16


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    with py4gw.connect(clients[0], game_thread=False) as client:
        module = win32.get_main_module(client.pid)
        module_base = int(module["base_address"])
        scanner = client._scanner  # type: ignore[attr-defined]
        report["pid"] = client.pid
        report["module_base"] = hex(module_base)
        report["scanner_image_base"] = hex(scanner.image_base)
        report["pe_image_base_from_file"] = hex(LINK_IMAGE_BASE)

        addresses = {
            "constant_unrebased": CONSTANT,
            "rebased_by_pe_image_base": module_base + (CONSTANT - LINK_IMAGE_BASE),
            "rebased_by_module_base": module_base + (CONSTANT - module_base),
            "scanner_to_module_address": scanner.to_module_address(CONSTANT),
        }
        address = scanner.to_module_address(CONSTANT)
        report["addresses"] = {name: hex(value) for name, value in addresses.items()}
        report["linked_address"] = hex(address)

        # The header the port reads, field by field, so "the live header disagrees with the
        # file" can be a measurement rather than a guess: ImageBase is OptionalHeader+0x1C,
        # SizeOfImage +0x38, AddressOfEntryPoint +0x10.
        coff_offset = int.from_bytes(client.reader.read(module_base + 0x3C, 4), "little") + 4
        optional_offset = coff_offset + 20
        header_fields = {}
        for name, offset in (
            ("magic", 0x00),
            ("address_of_entry_point", 0x10),
            ("base_of_code", 0x14),
            ("base_of_data", 0x18),
            ("image_base", 0x1C),
            ("section_alignment", 0x20),
            ("size_of_image", 0x38),
        ):
            value = int.from_bytes(
                client.reader.read(module_base + optional_offset + offset, 4), "little"
            )
            header_fields[name] = hex(value)
        report["live_header"] = header_fields
        report["live_header_optional_offset"] = hex(optional_offset)

        # What the correctly rebased address is, when it is rebased by the constant the source
        # uses rather than by the live header. The live header of this client has been rewritten
        # to the load address (0x610000) while the file's says 0x400000, so reading the header
        # makes the rebase a no-op.
        rebased = module_base + (CONSTANT - LINK_IMAGE_BASE)
        report["correct_rebase"] = hex(rebased)
        try:
            window = client.reader.read(rebased - 0x40, 0x60)
            report["window_before_and_at"] = window.hex(" ")
        except OSError as error:
            report["window_before_and_at"] = f"unreadable: {error}"
        try:
            start = scanner.to_function_start(rebased)
            report["to_function_start"] = hex(start) if start else "none"
        except (OSError, ValueError) as error:
            report["to_function_start"] = f"refused: {error}"
        try:
            report["is_valid_ptr_text"] = scanner.is_valid_ptr(rebased, "text")
        except (OSError, ValueError) as error:
            report["is_valid_ptr_text"] = f"refused: {error}"

        heads = {}
        for name, address in addresses.items():
            try:
                heads[name] = client.reader.read(address, HEAD).hex(" ")
            except OSError as error:
                heads[name] = f"unreadable: {error}"
        report["bytes"] = heads

        # What the port's own resolver answers, and whether the entry check accepts it.
        tables = client.dialog_tables
        tables.invalidate()
        resolved = tables.resolve_loader_get_text()
        report["resolve_loader_get_text"] = hex(resolved)
        report["resolver_catalog_value"] = hex(
            client._patterns.resolve(  # type: ignore[attr-defined]
                dialog.DialogTables._LOADER_RESOLVER, scanner
            ).value
        )

        # The same addresses the source's own table carries, for comparison: the five data
        # columns, which the port resolves with the .rdata fallback.
        addrs = tables.get()
        report["data_bases"] = {
            "event_handler": hex(addrs.event_handler_base),
            "flags": hex(addrs.flags_base),
            "static_flags_rebased": hex(
                scanner.to_module_address(0x00913920)
            ),
        }

    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
