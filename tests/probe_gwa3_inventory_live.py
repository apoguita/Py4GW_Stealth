"""Read-only, elevated: what the weapon-set pointers in the inventory struct hold.

This is the evidence behind two members of `py4gw/gwa3/data_item.py` that
``UtilityAI_WeaponSets.au3`` reads -- ``Item_GetInventoryInfo`` and ``Item_GetModStruct`` -- and
behind one factual question the source raises: GwAu3's ``Item_GetModStruct($a_v_Item)`` hands its
argument straight to ``Item_GetItemInfoByPtr`` (``GwAu3_Data_Item.au3:776-781``), which reads it as
an **address**; the weapon-set caller passes an **item id** (``UtilityAI_WeaponSets.au3:107-119``).
So this probe prints, per weapon set: the pointer, the record's id/type at that pointer, the id at
``+0``, and whether ``id + 0x10`` is readable at all.

Nothing is written: ``game_thread=False``, no hook, no patch, no call into the client.
"""

from __future__ import annotations

import ctypes
import sys

import py4gw
from py4gw.context import ItemStruct
from py4gw.win32 import Win32

PID = 0
READER: object = None


def _try_read(address: int, size: int) -> bytes | None:
    """Read or answer ``None`` -- an unreadable address is a result here, not an error."""

    try:
        return READER.read(address, size)  # type: ignore[attr-defined]
    except Exception as error:  # noqa: BLE001 - the failure is the measurement
        print(f"      read at 0x{address:08X} failed: {type(error).__name__}: {error}")
        return None


def main() -> int:
    global PID, READER

    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client")
        return 1
    PID = int(clients[0]["pid"])
    if not win32.is_elevated():
        print("this probe must run elevated: connecting asserts it")
        return 2

    client = py4gw.connect(clients[0], game_thread=False)
    print(f"--- connected read-only to pid {PID} ---")

    inventory = client.read_inventory()
    if inventory is None:
        print("no inventory struct: this client has no character in a map")
        return 3

    print(
        f"inventory: active_weapon_set={int(inventory.active_weapon_set)} "
        f"gold_character={int(inventory.gold_character)} gold_storage={int(inventory.gold_storage)}"
    )

    records = client.read_item_records()
    by_address = {
        int(record.address): record
        for record in records
        if record.address is not None
    }
    by_id = {int(record.item_id): record for record in records}
    print(f"read_item_records(): {len(records)} records, {len(by_address)} with an address")

    reader = client.reader
    READER = reader
    for index in range(4):
        weapon_set = inventory.weapon_sets[index]
        for label, address in (
            ("weapon", int(weapon_set.weapon)),
            ("offhand", int(weapon_set.offhand)),
        ):
            print(f"--- set {index + 1} {label}: pointer 0x{address:08X} ---")
            if address == 0:
                print("      null pointer")
                continue
            try:
                raw = reader.read(address, ctypes.sizeof(ItemStruct))
            except Exception as error:  # noqa: BLE001 - the failure is the measurement
                print(f"      cannot read an ItemStruct there: {type(error).__name__}: {error}")
                continue
            record = ItemStruct.from_buffer_copy(raw).bind_reader(reader, address)
            item_id = int(record.item_id)
            print(
                f"      record: item_id={item_id} type={int(record.type)} "
                f"model_id={int(record.model_id)} agent_id={int(record.agent_id)} "
                f"bag={int(record.bag)} equipped={int(record.equipped)}"
            )
            print(
                f"      mod_struct=0x{int(record.mod_struct):08X} "
                f"mod_struct_size={int(record.mod_struct_size)}"
            )
            mod_address = int(record.mod_struct)
            size = int(record.mod_struct_size)
            if mod_address and size:
                raw_mods = _try_read(mod_address, size * 4)
                if raw_mods is not None:
                    print(f"      mod bytes: 0x{raw_mods.hex().upper()}")
            print(f"      id {item_id} in read_item_records(): {item_id in by_id}")
            print(f"      address 0x{address:08X} in read_item_records(): {address in by_address}")

            # The source's own arithmetic: Item_GetModStruct hands this argument to a reader that
            # treats it as an address, so `id + 0x10` is what GwAu3 reads for the mod pointer.
            print(f"      is id + 0x10 = 0x{item_id + 0x10:08X} readable?")
            _try_read(item_id + 0x10, 4)

    print("--- done ---")
    py4gw.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
