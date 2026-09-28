"""Generate ``py4gw/frame_tree/``'s table modules from Reforged's ``FrameTree`` package.

Run: ``python live_reports/port_frame_tree_tables.py``

Reforged's ``Py4GWCoreLib/FrameTree/`` is a package of 5,444 lines. Five of its seven modules are **pure
data with no imports at all** — ``frame_window_keys`` (20), ``frame_names`` (538), ``frame_aliases``
(1216), ``frame_registry`` (1588), ``frame_ids`` (1648) — and the two that are not are the logic: the
package's ``__init__`` (70) and ``frame.py`` (1620, which imports the injected ``PyOverlay``/``PyUIManager``
and the tables). This generator carries the five table modules' bytes, each with the port's header, so the
tables cannot drift; ``frame.py`` is ported by hand, later, because it is logic.

The source package's own file names are kept, because inside a module every name is the source's and the
package's modules are reached by those names (``from .frame_ids import FrameId`` and the like).
"""

from __future__ import annotations

import pathlib

SOURCE = pathlib.Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\FrameTree")
TARGET = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\frame_tree")

HEADERS = {
    "frame_window_keys": '''"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_window_keys.py`` (20 lines).

The window frame keys: the window names this library reaches frames by. A verbatim transcription — the
source file has no imports, no functions and no computed values, so the body is its own bytes.
"""''',
    "frame_names": '''"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_names.py`` (538 lines).

The frame name tables: the confirmed, observed, harvested and reconstructed name maps, the merged
``FRAME_NAMES`` and the reversed ``NAME_TO_HASH``. A verbatim transcription — the source file has no
imports and no functions, so the body is its own bytes.
"""''',
    "frame_aliases": '''"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_aliases.py`` (1216 lines).

The frame aliases: the readable alias for each frame path this library addresses frames by. A verbatim
transcription — the source file has no imports, no functions and no computed values, so the body is its own
bytes.
"""''',
    "frame_registry": '''"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_registry.py`` (1588 lines).

The frame registry: the known frames and their paths, and the set of keys that are resolved dynamically
rather than from a fixed path. A verbatim transcription — the source file has no imports and no functions,
so the body is its own bytes.
"""''',
    "frame_ids": '''"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_ids.py`` (1648 lines).

``FrameId``: the frame-id constants the rest of the package addresses frames by. A verbatim transcription —
the source file has no imports and no functions, so the body is its own bytes.
"""''',
}


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, header in HEADERS.items():
        source = SOURCE / f"{name}.py"
        data = source.read_bytes()
        newline = b"\r\n" if b"\r\n" in data else b"\n"
        prepared = header.replace("\n", newline.decode()).encode("utf-8")
        if not prepared.endswith(newline):
            prepared += newline
        if not prepared.endswith(newline + newline):
            prepared += newline
        (TARGET / f"{name}.py").write_bytes(prepared + data)
        print(f"wrote {name}.py ({len(data.splitlines())} source lines carried)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
