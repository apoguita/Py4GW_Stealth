"""Generate ``py4gw/mods_upgrades.py`` from the Reforged source, body byte for byte.

Run: ``python live_reports/port_mods_upgrades.py``

The source has no imports, no functions and no computed values — four dictionaries (``UPGRADE_SLOT``
279 entries, ``UPGRADE_VAR`` 102, ``UPGRADE_RANGE`` 60, ``UPGRADE_DESC`` 263) and its own comments.
There is therefore nothing to adapt and nothing that could differ, so the port carries the source's
bytes and prepends the port's header docstring. The parity test
(``tests/test_mods_upgrades_offline.py``) loads the source and compares every entry.
"""

from __future__ import annotations

import pathlib

SOURCE = pathlib.Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\mods_upgrades.py")
TARGET = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\mods_upgrades.py")

HEADER = '''"""Port of Reforged's ``Py4GWCoreLib/mods_upgrades.py`` (727 lines).

The upgrade catalog, as four tables:

- ``UPGRADE_SLOT`` (279) — upgrade name to slot value (0 Inherent, 1 Prefix, 2 Suffix, 3 Inscription,
  4 Rune, 5 Insignia);
- ``UPGRADE_VAR`` (102) — upgrade name to the variable identifier its roll is measured with;
- ``UPGRADE_RANGE`` (60) — upgrade name to its ``(minimum, maximum)`` roll range;
- ``UPGRADE_DESC`` (263) — modifier identifier to the game-style description line.

**How it is ported.** The body is the source's own bytes. The file has no imports, no functions and no
computed values — four dictionaries and the source's own comments — so there is nothing to adapt and
nothing that could differ. ``mods_core`` reads these tables for ``value_of``, ``subtype_of``,
``is_better``, ``upgrades_on``, ``known_upgrades``, ``slot_of_upgrade``, ``upgrade_is_maxed`` and
``render_mod``; ``tests/test_mods_upgrades_offline.py`` compares every entry against the source.
"""
'''


def main() -> int:
    data = SOURCE.read_bytes()
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    header = HEADER.replace("\n", newline.decode()).encode("utf-8")
    if not header.endswith(newline):
        header += newline
    TARGET.write_bytes(header + data)
    print(
        f"wrote {TARGET} ({len(header + data)} bytes, "
        f"{len(data.splitlines())} source lines carried, no adaptation needed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
