"""Generate ``py4gw/mods_core.py`` from the Reforged source: the body's own bytes, couplings adapted.

Run: ``python live_reports/port_mods_core.py``

``mods_core`` is not a table — it is the decoder: ``decode_item``, ``find``, ``value_of``,
``subtype_of``, ``name_of``, ``is_better``, ``upgrades_on``, ``known_upgrades``, ``slot_of_upgrade``,
``upgrade_is_maxed``, ``effect_name``, ``render_mod``, ``describe_item``, ``raw_dump``, over the
``_EFFECT`` and ``_TEXT`` tables and the two ``mods_upgrades`` tables. Retyping that logic by hand is
the surest way to change it, so the port is the source's bytes with **five** adaptations, each asserted
to occur the exact number of times:

1-4. the four source-package import prefixes become this port's relative ones
     (``Py4GWCoreLib.enums_src.GameData_enums`` -> ``.enums_src.game_data_enums``,
     ``Py4GWCoreLib.enums_src.Item_enums`` -> ``.enums_src.item_enums``,
     ``Py4GWCoreLib import mods_upgrades`` -> ``from . import mods_upgrades``,
     ``Py4GWCoreLib.mods_types`` -> ``.mods_types``);
5.  ``import PyItem`` becomes ``from .client import require_client``, and the single line that used the
    binding — ``py = PyItem.PyItem(item_id)`` / ``mods = py.modifiers or []`` inside ``decode_item`` —
    becomes the port's read of the same words: the item context's ``GetItemById`` and the record's
    ``read_modifiers()``. That is the same mechanism native's binding performs: ``PyItemData::GetContext``
    copies ``mod_struct[i].mod`` into a ``std::vector<ItemModifier>`` (``item_bindings.cpp:263-319``,
    the array at ``context/item.h:95-96``), and the port's ``ItemModifierStruct`` carries the same
    accessors the decode uses (``IsValid``, ``GetIdentifier``, ``GetArg1``, ``GetArg2``, ``GetArg``).
    The difference is recorded in the module's docstring: this port's reader bounds the modifier array
    at 64 entries, where the binding copies whatever the item declares.
"""

from __future__ import annotations

import pathlib

SOURCE = pathlib.Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\mods_core.py")
TARGET = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\mods_core.py")

HEADER = '''"""Port of Reforged's ``Py4GWCoreLib/mods_core.py`` (494 lines).

**What the module is.** The item-modifier decoder: one item id in, its modifier words read, validated
and turned into the ``DecodedMod`` records the rest of the library works with.

- ``Slot`` (6) — Inherent, Prefix, Suffix, Inscription, Rune, Insignia, which ``mods_upgrades``'
  ``UPGRADE_SLOT`` values and ``Item.Mods``' upgrade readers are expressed in;
- ``_Def`` / ``_EFFECT`` (78 entries) — per-identifier metadata: how a modifier's value is read, the
  variable that carries it, whether it applies to a rune or an insignia, whether it is inherent;
- ``DecodedMod`` — ``(identifier, arg1, arg2, upgrade_id, packed)``;
- the readers: ``decode_item``, ``find``, ``value_of``, ``subtype_of``, ``name_of``, ``is_better``,
  ``upgrades_on``, ``known_upgrades``, ``slot_of_upgrade``, ``upgrade_is_maxed``, ``effect_name``;
- the render layer: ``render_mod``, ``describe_item``, ``raw_dump`` and the ``_TEXT``/``_SILENT``
  tables behind them.

**How it is ported.** The body is the source's own bytes. Five things are adapted, and each one is
asserted to occur exactly as often as expected while the file is generated
(``live_reports/port_mods_core.py``):

1. the source-package import prefix on the four ``GameData_enums`` names, the two ``Item_enums`` names,
   ``mods_upgrades`` and the four ``mods_types`` names becomes this port's relative import, because the
   enums live in ``py4gw/enums_src/`` under lower-case file names while every name *inside* a module
   keeps the source's spelling;
2. ``import PyItem`` and the one line that used it — ``py = PyItem.PyItem(item_id)`` /
   ``mods = py.modifiers or []`` in ``decode_item`` — become the port's read of the same words: the
   item context's ``GetItemById`` and the record's ``read_modifiers()``. Native's binding reaches that
   array too (``PyItemData::GetContext`` copies ``mod_struct[i].mod`` over
   ``context/item.h:95-96``), and the port's ``ItemModifierStruct`` carries the accessors the decode
   calls (``IsValid``, ``GetIdentifier``, ``GetArg1``, ``GetArg2``, ``GetArg``).

**One difference, recorded rather than smoothed over.** This port's ``read_modifiers`` bounds an item's
modifier array at 64 entries (``context/item_context.py``), where the binding copies however many the
item declares. An item with more than 64 modifier words would therefore decode to fewer here; no item
in the game carries anywhere near that many, and the bound belongs to the ported reader rather than to
this module.

``tests/test_mods_core_offline.py`` drives both modules over the same synthetic modifier words — through
a ``PyItem`` stand-in for the source and a fake client for the port — and compares every reader's
answer.
"""
'''


def _replace(data: bytes, old: bytes, new: bytes, expected: int, newline: bytes) -> bytes:
    """Replace a pattern, insisting it occurs exactly ``expected`` times."""

    old_bytes = old.replace(b"\n", newline)
    new_bytes = new.replace(b"\n", newline)
    found = data.count(old_bytes)
    if found != expected:
        raise SystemExit(f"pattern {old!r} occurs {found} times, expected {expected}")
    return data.replace(old_bytes, new_bytes)


def main() -> int:
    data = SOURCE.read_bytes()
    newline = b"\r\n" if b"\r\n" in data else b"\n"

    data = _replace(
        data,
        b"from Py4GWCoreLib.enums_src.GameData_enums import ",
        b"from .enums_src.game_data_enums import ",
        4,
        newline,
    )
    data = _replace(
        data,
        b"from Py4GWCoreLib.enums_src.Item_enums import ",
        b"from .enums_src.item_enums import ",
        2,
        newline,
    )
    data = _replace(
        data, b"from Py4GWCoreLib import mods_upgrades", b"from . import mods_upgrades", 1, newline
    )
    data = _replace(
        data, b"from Py4GWCoreLib.mods_types import ", b"from .mods_types import ", 4, newline
    )
    data = _replace(data, b"import PyItem", b"from .client import require_client", 1, newline)
    data = _replace(
        data,
        b"        py = PyItem.PyItem(item_id)\n        mods = py.modifiers or []\n",
        b"        context = require_client().item_context.read()\n"
        b"        item = None if context is None else context.GetItemById(int(item_id))\n"
        b"        mods = item.read_modifiers() if item is not None else []\n",
        1,
        newline,
    )

    header = HEADER.replace("\n", newline.decode()).encode("utf-8")
    if not header.endswith(newline):
        header += newline
    TARGET.write_bytes(header + data)
    print(f"wrote {TARGET} ({len(header + data)} bytes, {len(data.splitlines())} source lines carried)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
