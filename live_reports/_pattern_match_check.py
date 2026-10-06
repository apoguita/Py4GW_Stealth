"""Enumerate every match site of a named pattern on a build, using this port's own engine.

Read-only against ``Gw.exe`` on disk: no client, no elevation, no writes. It exists because a
resolver that resolves is not a resolver that resolved *correctly* — when a pattern matches more
than once, ``RemoteScanner.find`` answers with the first site, and the project has no way to see
that from the resolver output alone.

Usage:
    python live_reports/_pattern_match_check.py render.get_transform_target
    python live_reports/_pattern_match_check.py ui.load_settings --pattern "\\x83\\xFE\\x05..."
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT / "tools"), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from pe_image import PeImage  # noqa: E402
from resolve_offline import FileModule  # noqa: E402

from py4gw.scanner.patterns import Pattern, PatternCatalog  # noqa: E402
from py4gw.scanner.remote import RemoteScanner  # noqa: E402

CLIENT = Path(r"F:\GW\GW1\Gw.exe")


def sweep(scanner: RemoteScanner, catalog: PatternCatalog) -> int:
    """Every named byte pattern in ``offsets/`` that now matches more than once on this build.

    A pattern that matches once is unambiguous. A pattern that matches twice is a resolver whose
    answer depends on scan order, and the engine takes the first — which is exactly the failure
    mode the 2026-09-30 client update introduced for two of this port's patterns.
    """

    rows: list[tuple[str, int, list[int]]] = []
    ambiguous = 0
    checked = 0
    # The catalog exposes named lookups, not an iteration: the loaded definitions are its own map, and
    # this tool is a scratch diagnostic, so it reads that map rather than adding an accessor to the
    # library for it.
    for name, definition in sorted(catalog._patterns.items()):
        pattern = definition.pattern
        if pattern is None:
            continue
        checked += 1
        try:
            hits = scanner.find_all(pattern, section=definition.section or "text")
        except Exception as error:  # noqa: BLE001 - a sub-pattern may be text-only
            rows.append((definition.name, -1, []))
            print(f"  ERROR {definition.name:<48} {error}")
            continue
        if len(hits) > 1:
            ambiguous += 1
            rows.append((definition.name, len(hits), hits))
    print()
    print(f"{checked} named byte pattern(s) scanned; {ambiguous} match more than once:")
    for name, count, hits in sorted(rows, key=lambda row: -row[1]):
        print(f"  {name:<48} {count} matches  {' '.join(f'{hit:#010x}' for hit in hits[:6])}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--assertion"]:
        # ``--assertion <file> <message> <line>`` — does the assertion sequence still exist on
        # this build at that line number? A game update that inserts source lines moves it, and
        # the resolver then answers nothing (or something else) without saying so.
        assertion_file, assertion_message, line = argv[1], argv[2], int(argv[3], 0)
        image = PeImage(CLIENT)
        reader = FileModule(image)
        scanner = RemoteScanner(reader, image.image_base, image.size_of_image)
        scanner.initialize()
        found = scanner.find_assertion(assertion_file, assertion_message, line)
        print(
            f"find_assertion({assertion_file!r}, {assertion_message!r}, {line:#x}) -> "
            f"{'None' if found is None else hex(found)}"
        )
        return 0

    if "--sweep" in argv:
        image = PeImage(CLIENT)
        reader = FileModule(image)
        scanner = RemoteScanner(reader, image.image_base, image.size_of_image)
        scanner.initialize()
        catalog = PatternCatalog.from_directory(ROOT / "offsets")
        print(f"=== {CLIENT}  image base {image.image_base:#010x}")
        return sweep(scanner, catalog)

    override: str | None = None
    if "--pattern" in argv:
        index = argv.index("--pattern")
        override = argv[index + 1]
        del argv[index : index + 2]
    if len(argv) != 1:
        print(__doc__)
        return 2

    image = PeImage(CLIENT)
    reader = FileModule(image)
    scanner = RemoteScanner(reader, image.image_base, image.size_of_image)
    scanner.initialize()
    catalog = PatternCatalog.from_directory(ROOT / "offsets")

    name = argv[0]
    if override is None:
        definition = catalog.get_pattern(name)
        pattern = definition.pattern
        if pattern is None:
            print(f"{name} is not a byte pattern on this build.")
            return 2
        print(
            f"{name}: literal {definition.pattern!r}  offset {definition.offset:#x}  "
            f"section .{definition.section}"
        )
    else:
        parts = override.split(":", 1)
        raw = parts[0]
        mask = parts[1] if len(parts) > 1 else None
        pattern = Pattern.from_literal(raw, mask)
        print(f"{name} (override): {raw!r}  mask {pattern.mask}  section .text")

    section = "text"
    if override is None:
        section = definition.section or "text"
    hits = scanner.find_all(pattern, section=section)
    print(f"matches: {len(hits)}")
    for hit in hits:
        head = reader.read(hit, 16)
        section = image.section_for_va(hit)
        print(f"  {hit:#010x}  ({section.name if section else '?'})  {head.hex(' ')}")
    if len(hits) > 1:
        print()
        print(
            "MORE THAN ONE MATCH: ``RemoteScanner.find`` answers with the first site, so a resolver "
            "built on this pattern is answering with whichever of these the scan reaches first."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
