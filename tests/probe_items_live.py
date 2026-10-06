"""Live probe, read-only: the item trio against the client's own bags.

The first live exercise of ``Item``, ``ItemArray`` and ``Inventory``. Everything else about those three has
been checked against fixtures; this reads the **client's** bags and asks the ported classes what they hold:

1. ``ItemArray.CreateBagList`` / ``GetAllBags`` — the bags the source's own tables name;
2. ``ItemArray.GetItemArray(bags)`` — the item ids in them;
3. per item, the reads ``Item`` answers (model, type, quantity, rarity, weapon/salvageable, slot, agent);
4. the counts ``Inventory`` reports, cross-checked against what the walk found;
5. whether the character carries an ID kit and an unidentified item — what a later **write** test
   (``IdentifyItem``) needs, reported here without doing it.

It connects with ``game_thread=False``: no hook, no patch, no call. Nothing is written to the client.

Usage: (elevated) python tests/probe_items_live.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw.native_src.item import py_inventory
from py4gw.inventory import Inventory
from py4gw.item import Item
from py4gw.item_array import ItemArray
from py4gw.map import Map
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How many items to describe in full; the counts below still cover every one of them.
SAMPLE = 12


def _ids(values: Any) -> Any:
    """The plain numbers behind a list of ``Bag``/``Item`` values, or the value as it came."""

    if not isinstance(values, list):
        return values
    out: list[Any] = []
    for value in values:
        out.append(int(value.value) if hasattr(value, "value") else value)
    return out


def _ask(label: str, call: Any) -> Any:
    """Run one ported read and record what it answered — an exception is reported, never hidden."""

    try:
        return call()
    except Exception as error:
        return f"{type(error).__name__}: {error}"


def _describe(item_id: int) -> dict[str, Any]:
    """What ``Item`` answers for one id."""

    return {
        "item_id": int(item_id),
        "model_id": _ask("GetModelID", lambda: Item.GetModelID(item_id)),
        "item_type": _ask("GetItemType", lambda: Item.GetItemType(item_id)),
        "quantity": _ask("GetQuantity", lambda: Item.Properties.GetQuantity(item_id)),
        "rarity": _ask("GetRarity", lambda: Item.Rarity.GetRarity(item_id)),
        "is_weapon": _ask("IsWeapon", lambda: Item.Type.IsWeapon(item_id)),
        "is_salvageable": _ask("IsSalvageable", lambda: Item.Usage.IsSalvageable(item_id)),
        "is_identified": _ask("IsIdentified", lambda: Item.Usage.IsIdentified(item_id)),
        "slot": _ask("GetSlot", lambda: Item.GetSlot(item_id)),
        "agent_id": _ask("GetAgentID", lambda: Item.GetAgentID(item_id)),
        "value": _ask("GetValue", lambda: Item.Properties.GetValue(item_id)),
    }


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())
    report["game_thread"] = False

    with py4gw.connect(process, game_thread=False) as client:
        report["map_id"] = _ask("Map.GetMapID", Map.GetMapID)

        bags = _ask("CreateBagList", ItemArray.CreateBagList)
        report["create_bag_list"] = _ids(bags)
        all_bags = _ask("GetAllBags", ItemArray.GetAllBags)
        report["all_bags"] = _ids(all_bags)
        report["create_bag_names"] = (
            [str(bag) for bag in bags] if isinstance(bags, list) else bags
        )

        item_ids = _ask("GetItemArray", lambda: ItemArray.GetItemArray(all_bags))
        if not isinstance(item_ids, list):
            report["items_error"] = item_ids
            return write_report(report)
        report["items_found"] = len(item_ids)
        report["items"] = [
            _describe(int(item_id.value) if hasattr(item_id, "value") else int(item_id))
            for item_id in item_ids[:SAMPLE]
        ]

        # The counts `Inventory` reports, next to what the walk actually found.
        report["inventory_space"] = _ask("GetInventorySpace", Inventory.GetInventorySpace)
        report["free_slots"] = _ask("GetFreeSlotCount", Inventory.GetFreeSlotCount)
        report["character_gold"] = _ask(
            "GetGoldAmount", py_inventory.PyInventory().GetGoldAmount
        )
        report["storage_gold"] = _ask(
            "GetGoldAmountInStorage", py_inventory.PyInventory().GetGoldAmountInStorage
        )
        report["is_storage_open"] = _ask(
            "GetIsStorageOpen", py_inventory.PyInventory().GetIsStorageOpen
        )
        if item_ids:
            first = int(item_ids[0])
            report["count_of_first_model"] = _ask(
                "GetItemCount",
                lambda: Inventory.GetItemCount(first),
            )

        # What a later write test (IdentifyItem) would need — read here, not acted on.
        report["first_id_kit"] = _ask("GetFirstIDKit", Inventory.GetFirstIDKit)
        report["first_unidentified"] = _ask(
            "GetFirstUnidentifiedItem", Inventory.GetFirstUnidentifiedItem
        )
        report["first_salvage_kit"] = _ask("GetFirstSalvageKit", Inventory.GetFirstSalvageKit)
        report["note"] = (
            "read-only: game_thread=False installed no hook and no patch, and no call into the client was "
            "made. The writes that would identify or salvage are a separate, explicitly scoped run."
        )

    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
