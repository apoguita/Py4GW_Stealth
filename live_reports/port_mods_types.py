"""Generate ``py4gw/mods_types.py`` from the Reforged source, body byte for byte.

Run: ``python live_reports/port_mods_types.py``

The source is a declaration file — five enums (``ModifierIdentifier`` 80 members, ``ItemUpgradeId``
467, ``ItemUpgrade`` 283 with four methods), one ``TypeAlias`` and one function — and the only
executable statement at module level is ``any_of``. Retyping 1230 lines of tables would introduce
transcription errors for no gain, so the body is the source's own bytes and the **one** thing changed
is the import that names the source package: ``from Py4GWCoreLib.enums_src.Item_enums import ItemType``
becomes ``from .enums_src.item_enums import ItemType``, because this port keeps the enums in
``py4gw/enums_src/`` (the port's lower-case module names) while a script still imports every name
*inside* a module by the source's spelling.

Nothing else is touched: no member renamed, reordered, added or dropped, comments included. The parity
test (``tests/test_mods_types_offline.py``) loads the source and compares the two, so a transcription
error cannot pass unnoticed.
"""

from __future__ import annotations

import pathlib

SOURCE = pathlib.Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\mods_types.py")
TARGET = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\mods_types.py")

SOURCE_IMPORT = b"from Py4GWCoreLib.enums_src.Item_enums import ItemType"
PORT_IMPORT = b"from .enums_src.item_enums import ItemType"

HEADER = '''"""Port of Reforged's ``Py4GWCoreLib/mods_types.py`` (1230 lines).

**What the module is.** The item-modifier vocabulary and the upgrade catalog, declared as tables:

- ``ModifierType`` (4), ``ItemBaneSpecies`` (12), ``ItemModifierParam`` (2), ``ItemUpgradeType`` (7);
- ``ModifierIdentifier`` (80) — the modifier ids an item's modifier words carry, which is what
  ``Item.Mods`` and four of ``Item.Properties``' readers are built on;
- ``ModifierIdentifierSpec`` and :func:`any_of`, the two spellings a spec may take;
- ``ItemUpgradeId`` (467) — the upgrade ids, by weapon and armour type;
- ``ItemUpgrade`` (283) — the upgrade names, each carrying either one id or the `{ItemType: id}` map
  the item type selects from, with the four members ``item_type_id_map``, ``upgrade_ids``,
  ``get_item_type`` and ``has_id`` that read it.

**How it is ported.** The body is the source's own bytes. The only change is the one import that names
the source package — ``from Py4GWCoreLib.enums_src.Item_enums import ItemType`` became
``from .enums_src.item_enums import ItemType``, because this port keeps the enums in
``py4gw/enums_src/`` under the port's lower-case file names, while every name *inside* a module keeps
the source's spelling. No member is renamed, reordered, added or dropped, and the source's comments
are kept. ``tests/test_mods_types_offline.py`` compares this module against the source itself.
"""
'''


def main() -> int:
    data = SOURCE.read_bytes()
    if data.count(SOURCE_IMPORT) != 1:
        raise SystemExit(
            f"the source import appears {data.count(SOURCE_IMPORT)} times, expected once"
        )

    newline = b"\r\n" if b"\r\n" in data else b"\n"
    header = HEADER.replace("\n", newline.decode()).encode("utf-8")
    if not header.endswith(newline):
        header += newline

    body = data.replace(SOURCE_IMPORT, PORT_IMPORT)
    TARGET.write_bytes(header + body)
    print(f"wrote {TARGET} ({len(header + body)} bytes, {len(body.splitlines())} source lines carried)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
