"""Read-only probe: the client's StoC handler array, which the packet capability replaces entries in.

Native reaches the client's server-to-client handler table through one resolver —
``stoc.handler_table_addr`` (``offsets/stoc.json``) — and then walks it by hand:

```c
auto** game_server = reinterpret_cast<GameServer**>(g_handler_table_addr);
if (!(game_server && *game_server && (*game_server)->gs_codec)) return false;
g_game_server_handlers = &(*game_server)->gs_codec->handlers;   // stoc_patterns.cpp:43-50
```

``GameServer.gs_codec`` is at ``+0x8`` of that structure and ``handlers`` at ``+0x2C`` of the codec
(``stoc.cpp:26-41``: ``h0010[12]``, ``client_codec_array[4]``, then ``handlers``), and each entry is
``{packet_template: u32*, field_count: u32, handler_func: u32}`` (``stoc_patterns.cpp:9-13``) inside a
``GW::GWArray`` whose buffer, capacity and size sit at ``+0``, ``+4`` and ``+8``
(``GW/common/gw_array.h:61-64``).

**What this probe answers, and why it must be asked of the running client rather than assumed:** what
the resolver's value actually *is*. Native casts it to ``GameServer**`` and dereferences it once more
before reading ``gs_codec``, so the resolver's last step (``deref_ptr``) does not hand back the
structure itself. Both readings are walked here and each is judged by its own evidence — a ``GWArray``
whose size is a plausible header count and whose buffer is readable memory, with handler pointers
inside the client's ``.text`` — because guessing between them is how a write lands at the wrong
address.

**Read-only**: it reads the client's memory directly through a ``ProcessMemoryReader`` and a
``RemoteScanner`` — the route ``tests/probe_ui_manager_reads_live.py`` established — so no connection
is made at all, nothing can be patched and nothing can be written, elevated or not. Nothing is called.

Usage: python tests/probe_stoc_handlers.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The resolver, as the catalog names it.
RESOLVER = "stoc.handler_table_addr"

#: Where native reads each piece, from ``stoc.cpp:26-41``.
GS_CODEC_OFFSET = 0x8
HANDLERS_OFFSET = 0x2C

#: ``GW::GWArray``: the buffer, then the capacity, then the size (``gw_array.h:61-64``).
ARRAY_BUFFER_OFFSET = 0x0
ARRAY_CAPACITY_OFFSET = 0x4
ARRAY_SIZE_OFFSET = 0x8
ARRAY_SIZE = 0x10

#: One ``StoCHandler``: where its template is, how many descriptors, and the handler itself.
ENTRY_SIZE = 0xC
ENTRY_TEMPLATE_OFFSET = 0x0
ENTRY_FIELD_COUNT_OFFSET = 0x4
ENTRY_HANDLER_OFFSET = 0x8

#: The five headers the merchant listener replaces, and what each of its callbacks reads. The
#: counts are the packet's own declared fields plus its header word, which is what the port's
#: per-header stub copies (``stoc.h:356-359``, ``:546-548``, ``:599-602``, ``listeners.cpp:99-119``).
MERCHANT_HEADERS = (
    ("GAME_SMSG_WINDOW_ADD_ITEMS", 0x0084, 18),
    ("GAME_SMSG_WINDOW_ITEMS_END", 0x0085, 1),
    ("GAME_SMSG_WINDOW_ITEM_STREAM_END", 0x0086, 2),
    ("GAME_SMSG_TRANSACTION_DONE", 0x00CC, 1),
    ("GAME_SMSG_ITEM_PRICE_QUOTE", 0x00F7, 3),
)

#: A handler pointer below this is not code, and the array's size is a header count: a client that
#: reports one outside this range is not describing the table this project thinks it is.
MINIMUM_CODE_ADDRESS = 0x10000
PLAUSIBLE_HEADER_COUNT = 4096


class _LiveClient:
    """The surface this probe uses: the catalog, the scanner and the reader."""

    def __init__(
        self,
        reader: ProcessMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        self._reader = reader
        self.reader = reader
        self._scanner = scanner
        self._patterns = patterns

    def resolves(self, name: str) -> bool:
        return bool(self._patterns.resolve(name, self._scanner).ok)


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    pid = int(process["pid"])
    report["pid"] = pid
    report["elevated"] = bool(win32.is_elevated())
    report["connect"] = "not used: this probe reads directly, so no elevation is required"

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        client = _LiveClient(reader, scanner, patterns)
    except Exception as error:  # noqa: BLE001 - reported, then closed
        report["error"] = f"{type(error).__name__}: {error}"
        reader.close()
        return write_report(report)

    try:
        text = scanner.get_section_range("text")
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}

        result = patterns.resolve(RESOLVER, scanner)
        report["resolver"] = {
            "name": result.name,
            "ok": bool(result.ok),
            "value": hex(int(result.value)),
            "trace": [
                {
                    "step": step.name,
                    "op": step.operation,
                    "in": hex(step.input_value),
                    "out": hex(step.output_value),
                    "ok": bool(step.ok),
                    "detail": step.detail,
                }
                for step in result.trace
            ],
        }
        if not result.value:
            report["note"] = "the resolver did not answer; nothing can be walked"
            return write_report(report)

        resolved = int(result.value)
        report["resolved_head"] = reader.read(resolved, 16).hex(" ")

        # Both readings of the resolver's value, walked and judged.
        report["as_game_server_pointer_pointer"] = _walk(
            reader, text, _read_u32(reader, resolved)
        )
        report["as_game_server_pointer"] = _walk(reader, text, resolved)

        report["note"] = (
            "read-only: nothing was written, no entry was replaced and no code was placed. The "
            "reading whose array has a plausible size and code handlers is the one native's cast "
            "describes; the other one is reported so the difference is visible rather than assumed."
        )
    finally:
        reader.close()

    return write_report(report)


def _walk(reader: Any, text: Any, game_server: int) -> dict[str, Any]:
    """Follow native's own walk from one reading of the resolver's value."""

    walked: dict[str, Any] = {"game_server": hex(game_server)}
    if not game_server:
        walked["error"] = "the value is null, so nothing points anywhere"
        return walked

    try:
        codec = _read_u32(reader, game_server + GS_CODEC_OFFSET)
    except Exception as error:  # noqa: BLE001 - reported, not raised
        walked["error"] = f"gs_codec is not readable: {type(error).__name__}: {error}"
        return walked

    walked["gs_codec"] = hex(codec)
    if not codec:
        walked["error"] = "gs_codec is null: the game server has no codec yet"
        return walked

    handlers = codec + HANDLERS_OFFSET
    walked["handlers"] = hex(handlers)
    try:
        raw = reader.read(handlers, ARRAY_SIZE)
    except Exception as error:  # noqa: BLE001 - reported, not raised
        walked["error"] = f"the handler array is not readable: {type(error).__name__}: {error}"
        return walked

    buffer = int.from_bytes(raw[ARRAY_BUFFER_OFFSET : ARRAY_BUFFER_OFFSET + 4], "little")
    capacity = int.from_bytes(
        raw[ARRAY_CAPACITY_OFFSET : ARRAY_CAPACITY_OFFSET + 4], "little"
    )
    size = int.from_bytes(raw[ARRAY_SIZE_OFFSET : ARRAY_SIZE_OFFSET + 4], "little")
    walked["array"] = {
        "buffer": hex(buffer),
        "capacity": capacity,
        "size": size,
        "looks_like_a_header_table": bool(
            buffer and size and size <= capacity and size < PLAUSIBLE_HEADER_COUNT
        ),
    }
    if not (buffer and size and size <= capacity and size < PLAUSIBLE_HEADER_COUNT):
        walked["error"] = "the fields at that address are not an array of handlers"
        return walked

    merchant = []
    for name, header, words in MERCHANT_HEADERS:
        row: dict[str, Any] = {"name": name, "header": hex(header), "words": words}
        if header >= size:
            row["error"] = f"the client's array has {size} entries; this header is past it"
            merchant.append(row)
            continue
        entry = _read_entry(reader, buffer + header * ENTRY_SIZE)
        row.update(entry)
        merchant.append(row)
    walked["merchant_headers"] = merchant
    return walked


def _read_entry(reader: Any, address: int) -> dict[str, Any]:
    """Read one ``StoCHandler`` and say whether its handler looks like code."""

    try:
        raw = reader.read(address, ENTRY_SIZE)
    except Exception as error:  # noqa: BLE001 - reported, not raised
        return {"error": f"the entry is not readable: {type(error).__name__}: {error}"}

    template = int.from_bytes(raw[ENTRY_TEMPLATE_OFFSET : ENTRY_TEMPLATE_OFFSET + 4], "little")
    field_count = int.from_bytes(
        raw[ENTRY_FIELD_COUNT_OFFSET : ENTRY_FIELD_COUNT_OFFSET + 4], "little"
    )
    handler = int.from_bytes(raw[ENTRY_HANDLER_OFFSET : ENTRY_HANDLER_OFFSET + 4], "little")
    return {
        "entry": hex(address),
        "packet_template": hex(template),
        "field_count": field_count,
        "handler_func": hex(handler),
        "handler_is_code": handler >= MINIMUM_CODE_ADDRESS,
        "handler_head": (
            reader.read(handler, 16).hex(" ") if handler >= MINIMUM_CODE_ADDRESS else ""
        ),
    }


def _read_u32(reader: Any, address: int) -> int:
    """Read one word, letting an unreadable address raise for the caller to report."""

    return int.from_bytes(reader.read(address, 4), "little")


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
