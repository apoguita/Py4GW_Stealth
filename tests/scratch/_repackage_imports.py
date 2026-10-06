"""One-off: repoint imports at the modules moved into ``py4gw/native_src/`` (2026-10-05).

The move is the source-driven one: ``native_src/methods/`` for Reforged's
``native_src/methods/*.py``, and ``native_src/<native dir>/`` for ports of Native's own bindings
(``GW/textures``, ``GW/item``, ``GW/chat``, ``base/``). Everything at ``py4gw/`` root is now Reforged's
root ``Py4GWCoreLib/*.py`` — the user-accessible classes — plus this project's own ``client``.

Three mechanical rules, no judgement left to the script:

1. **The moved files**: every relative import in them points one level higher now, so each gains one
   dot (``from .client import`` -> ``from ..client import``).
2. **The importer files**: one explicit entry per line, because the correct relative form depends on
   where the importer sits (``py4gw/`` root vs ``py4gw/internals/``).
3. **Documentation and paths**: ``py4gw/native_src/chat/chat.py`` -> ``py4gw/native_src/chat/chat.py``, and the dotted
   form likewise.

Run from the repository root: ``python tests/scratch/_repackage_imports.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: moved module -> (new relative path from ``py4gw/``, native directory it mirrors)
MOVED = {
    "map_methods": ("native_src.methods.map_methods", "methods"),
    "ffna_map_methods": ("native_src.methods.ffna_map_methods", "methods"),
    "dat_reader": ("native_src.textures.dat_reader", "textures"),
    "py_inventory": ("native_src.item.py_inventory", "item"),
    "chat": ("native_src.chat.chat", "chat"),
    "timer": ("native_src.base.timer", "base"),
    "perf_counter": ("native_src.base.perf_counter", "base"),
}

MIRRORED = {name: dotted for name, (dotted, _dir) in MOVED.items()}

#: importer file -> the exact replacements to make in it (old, new)
EXPLICIT = {
    "py4gw/client.py": [
        ("from .perf_counter import PerfCounter", "from .native_src.base.perf_counter import PerfCounter"),
        ("from . import chat", "from .native_src.chat import chat"),
    ],
    "py4gw/player.py": [("from . import chat", "from .native_src.chat import chat")],
    "py4gw/party.py": [("from .chat import SendChat", "from .native_src.chat.chat import SendChat")],
    "py4gw/listeners.py": [("from .timer import Timer", "from .native_src.base.timer import Timer")],
    "py4gw/map.py": [
        ("from .map_methods import MapMethods", "from .native_src.methods.map_methods import MapMethods"),
        ("from .ffna_map_methods import", "from .native_src.methods.ffna_map_methods import"),
    ],
    "py4gw/inventory.py": [("from .py_inventory import", "from .native_src.item.py_inventory import")],
    "py4gw/item.py": [("from .py_inventory import", "from .native_src.item.py_inventory import")],
    "py4gw/item_array.py": [("from .py_inventory import", "from .native_src.item.py_inventory import")],
    "py4gw/__init__.py": [
        ("from . import chat, context, ui, win32", "from .native_src.chat import chat\nfrom . import context, ui, win32"),
        ("from .perf_counter import", "from .native_src.base.perf_counter import"),
    ],
    "py4gw/internals/string_table.py": [
        ("from ..dat_reader import", "from ..native_src.textures.dat_reader import"),
    ],
}

#: the moved file that imports another moved file, from one native tree to another
CROSS_MOVED = {
    "py4gw/native_src/methods/ffna_map_methods.py": [
        ("from ..dat_reader import", "from ..textures.dat_reader import"),
    ],
}

RELATIVE_IMPORT = re.compile(r"^(\s*from\s+)(\.+)(\w[\w.]*)(\s+import\b)", re.MULTILINE)
MOVED_NAMES = "|".join(sorted(MOVED, key=len, reverse=True))


def rewrite_moved_file(path: Path) -> int:
    """Rule 1: one more dot on every relative import inside a moved module."""

    text = path.read_text(encoding="utf-8")
    text, count = RELATIVE_IMPORT.subn(lambda m: f"{m.group(1)}{m.group(2)}.{m.group(3)}{m.group(4)}", text)
    path.write_text(text, encoding="utf-8")
    return count


def rewrite_importer(path: Path, pairs: list[tuple[str, str]]) -> int:
    """Rule 2: the explicit replacements for one importer."""

    text = path.read_text(encoding="utf-8")
    total = 0
    for old, new in pairs:
        if old in text:
            total += text.count(old)
            text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    return total


def rewrite_references(path: Path) -> int:
    """Rule 3: any remaining reference to a moved module, in code or prose."""

    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    for name, (dotted, _directory) in MOVED.items():
        # paths first, so the dotted rule cannot eat them
        text = text.replace(f"py4gw/{name}.py", f"py4gw/{dotted.replace('.', '/')}.py")
        text = re.sub(rf"py4gw\.{name}\b(?!_)", f"py4gw.{dotted}", text)
        text = re.sub(rf"(?<![\w./])py4gw/{name}\b(?!\.py)", f"py4gw/{dotted.replace('.', '/')}", text)
        # relative imports anywhere the explicit table did not cover
        text = re.sub(rf"(\sfrom\s+\.+){name}(\s+import\b)", rf"\1{dotted}\2", text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return sum(1 for a, b in zip(original.splitlines(), text.splitlines()) if a != b)
    return 0


def main() -> int:
    moved_files = [ROOT / "py4gw" / f"{dotted.replace('.', '/')}.py" for dotted, _directory in MOVED.values()]
    moved_set = {path.resolve() for path in moved_files}

    for path in moved_files:
        if not path.is_file():
            print(f"  MISSING moved file: {path}")
            continue
        print(f"  rule 1  {path.relative_to(ROOT)}: {rewrite_moved_file(path)} relative import(s) deepened")

    for relative, pairs in EXPLICIT.items():
        path = ROOT / relative
        print(f"  rule 2  {relative}: {rewrite_importer(path, pairs)} replacement(s)")

    for relative, pairs in CROSS_MOVED.items():
        path = ROOT / relative
        print(f"  rule 2b {relative}: {rewrite_importer(path, pairs)} replacement(s)")

    changed = 0
    for path in list((ROOT / "py4gw").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")) + [
        ROOT / "main.py",
    ] + list((ROOT / "docs").glob("*.md")) + list(ROOT.glob("*.md")):
        if "__pycache__" in str(path) or path.resolve() in moved_set:
            continue
        if rewrite_references(path):
            print(f"  rule 3  {path.relative_to(ROOT)}")
            changed += 1
    print(f"\nfiles changed by rule 3: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
