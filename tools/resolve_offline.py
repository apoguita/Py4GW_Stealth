"""Run this port's own resolvers against ``Gw.exe`` on disk — no client, no elevation.

**Why this is possible.** A resolver in ``offsets/*.json`` is a claim about a *build*, and the
engine that evaluates it is pure: it searches a byte snapshot for a pattern, follows pointers
through a reader, and walks to a function start. Nothing in that needs a process. The reader the
engine asks for answers *virtual addresses*, and a PE file is the same image with the sections at
their file offsets — so a file answers the same reads, and every named target can be checked
offline, deterministically, before anything is called.

That is the method the crashed call needed. On 2026-09-25 the client died with ``eip=462fd617`` while
this port was calling ``chat.send_chat_func``: the host had written an address that is not code into
the call table, and the address came from a resolver. The port now refuses such a target
(``ConnectedClient._descriptor_slot``), but a refusal is not a diagnosis — this is the diagnosis,
and it costs nothing to run.

**What it does not do.** It never calls a client function, never writes, never connects. A target is
reported with the bytes at it and whether they begin like a function; that is a reading, not a
verdict about what the function *is*.

Usage:
    python tools/resolve_offline.py                        # every resolver, one line each
    python tools/resolve_offline.py chat dialog ui         # only these namespaces
    python tools/resolve_offline.py -v chat.send_chat_func # full step trace
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(Path(__file__).resolve().parent), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gw_scan import is_entry, preceding_entry  # noqa: E402
from pe_image import PeImage  # noqa: E402
from py4gw.scanner.patterns import PatternCatalog  # noqa: E402
from py4gw.scanner.remote import RemoteScanner  # noqa: E402

DEFAULT_CLIENT = r"F:\GW\GW1\Gw.exe"
HEAD_BYTES = 16


class FileModule:
    """A PE file read the way the scanner reads a loaded module: by virtual address.

    Three regions, and the difference between them matters:

    - the **headers**, where a file's offsets are already its virtual addresses;
    - a section's **file bytes**, at ``raw_offset + (rva - virtual_address)``;
    - a section's **uninitialised tail**, which the loader zero-fills — reported as zeros because
      that is what the client's own memory holds there, not because the file does.
    """

    def __init__(self, image: PeImage) -> None:
        self.image = image
        self._first_section_rva = min(
            (section.virtual_address for section in image.sections), default=0x1000
        )

    def read(self, address: int, size: int) -> bytes:
        """Return ``size`` bytes at the virtual address ``address``, or raise ``OSError``."""

        rva = address - self.image.image_base
        if rva < 0 or size <= 0:
            raise OSError(f"{address:#010x} is below the image base")
        if rva < self._first_section_rva:
            data = self.image.data[rva : rva + size]
            if len(data) < size:
                raise OSError(f"header read of {size:#x} at {address:#010x} leaves the file")
            return data
        section = self.image.section_for_rva(rva)
        if section is None:
            raise OSError(f"{address:#010x} is outside every section")
        offset = rva - section.virtual_address
        if offset >= section.raw_size:
            if offset + size <= max(section.virtual_size, section.raw_size):
                return bytes(size)  # the loader's zero fill, not the file's
            raise OSError(f"{address:#010x} is past {section.name}")
        available = min(size, section.raw_size - offset)
        data = self.image.data[
            section.raw_offset + offset : section.raw_offset + offset + available
        ]
        return data + bytes(size - len(data))


def resolver_names(offsets: Path, wanted: list[str]) -> list[str]:
    """Every ``namespace.name`` in the offsets directory, or the ones asked for."""

    names: list[str] = []
    for file_path in sorted(offsets.glob("*.json")):
        root = json.loads(file_path.read_text(encoding="utf-8"))
        namespace = str(root.get("namespace", ""))
        for name in sorted(root.get("resolvers", {})):
            full = f"{namespace}.{name}" if namespace else name
            if not wanted or any(full == item or namespace == item for item in wanted):
                names.append(full)
    return names


def expected_kind(catalog: PatternCatalog, name: str) -> str:
    """What kind of address this resolver is *supposed* to answer with: ``code`` or ``data``.

    The last step decides. ``to_function_start`` and ``function_from_near_call`` are function
    resolvers and must answer with a function; a resolver whose last step is ``validate_section``
    over ``data``, or a patch-site scan, is answering with an address that is *not* a function — so
    reporting it as one would be the tool's mistake, not the resolver's.
    """

    definition = catalog.get_resolver(name)
    last = definition.attempts[-1].steps[-1]
    if last.operation in ("to_function_start", "function_from_near_call"):
        return "code"
    if last.operation in ("dereference", "validate_section"):
        return "data"
    if last.operation == "scan":
        pattern = catalog.get_pattern(last.pattern_name) if last.pattern_name else None
        return "code" if pattern is not None and "func" in last.pattern_name else "address"
    return "address"


def main(argv: list[str]) -> int:
    verbose = "-v" in argv
    wanted = [item for item in argv if not item.startswith("-")]
    path = Path(DEFAULT_CLIENT)
    if not path.is_file():
        print(f"no client file at {path}")
        return 2

    image = PeImage(path)
    reader = FileModule(image)
    scanner = RemoteScanner(reader, image.image_base, image.size_of_image)
    scanner.initialize()
    catalog = PatternCatalog.from_directory(ROOT / "offsets")
    text = scanner.get_section_range("text")

    print(f"=== {path}  ({len(image.data):#x} bytes, image base {image.image_base:#010x})")
    print(f"    .text {text.start:#010x} .. {text.end:#010x}")
    names = resolver_names(ROOT / "offsets", wanted)
    print(f"    {len(names)} resolver(s)")
    print()

    resolved = 0
    problems: list[str] = []
    for name in names:
        result = catalog.resolve(name, scanner)
        kind = expected_kind(catalog, name)
        if not result.ok or not result.value:
            print(
                f"  FAIL {name:<44} step {result.failed_step or '-'} "
                f"action {result.action or '-'} {result.message or ''}".rstrip()
            )
            if kind == "code":
                problems.append(name)
            if verbose:
                for step in result.trace:
                    print(
                        f"        {step.name:<20} {step.operation:<18} "
                        f"in {step.input_value:#010x} -> out {step.output_value:#010x} "
                        f"{'ok' if step.ok else 'FAILED'} {step.detail or ''}".rstrip()
                    )
            continue
        value = int(result.value)
        rva = value - image.image_base
        try:
            head = reader.read(value, HEAD_BYTES)
        except OSError as error:
            print(f"  FAIL {name:<44} {value:#010x}: {error}")
            if kind == "code":
                problems.append(name)
            continue
        inside = text.start <= value < text.end
        section = image.section_for_va(value)
        where = f"{section.name}" if section is not None else "no section"

        if kind != "code":
            print(f"  ok   {name:<44} {value:#010x} ({kind}, {where})")
            continue

        entry = is_entry(head)
        thunk_target = 0
        if not entry and head[:1] == b"\xe9":
            thunk_target = value + 5 + int.from_bytes(head[1:5], "little", signed=True)
            if text.start <= thunk_target < text.end:
                try:
                    entry = is_entry(reader.read(thunk_target, 5))
                except OSError:
                    entry = False
        if inside and entry:
            resolved += 1
            shape = "entry" if is_entry(head) else f"thunk -> {thunk_target:#010x}"
            print(f"  ok   {name:<44} {value:#010x} (rva {rva:#08x}) {shape}  {head.hex(' ')}")
        else:
            reason = (
                "outside .text"
                if not inside
                else "a jmp whose target is not an entry"
                if head[:1] == b"\xe9"
                else "not a function entry"
            )
            print(f"  ODD  {name:<44} {value:#010x} (rva {rva:#08x}) {reason}: {head.hex(' ')}")
            problems.append(name)
            nearest = preceding_entry(image, rva) if inside else None
            if nearest is not None:
                print(f"        nearest entry before it: {image.image_base + nearest:#010x}")
        if verbose:
            for step in result.trace:
                print(
                    f"        {step.name:<20} {step.operation:<18} "
                    f"in {step.input_value:#010x} -> out {step.output_value:#010x} "
                    f"{'ok' if step.ok else 'FAILED'} {step.detail or ''}".rstrip()
                )

    print()
    print(
        f"{resolved} of the function resolvers answer with something that begins like a function; "
        f"{len(problems)} do not"
    )
    for name in problems:
        print(f"    {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
