"""Live probe: consume one **Hard Apple Cider** through ``Inventory.UseItem``.

The owner's experiment, and it proves itself: the stack holds 223, so one use must leave **222**.

That single number is the whole test, and it is a good one — it exercises the chain end to end:

- ``Inventory.UseItem`` (``Inventory.py:1212-1220``) → ``inventory_instance()`` → the binding's
  ``PyInventory.UseItem`` (``inventory_bindings.cpp:90-93``) → ``GW::item::UseItem``
  (``item_methods.cpp:114-121``), which is where round 57's interact guard lives
  (``CanInteractWithItem`` → ``IsStorageItem`` → ``IsStorageBag`` → ``CanAccessXunlaiChest``) and where
  ``item.use_item_func`` is called with the item's own id.

The reads either side of the call are the port's too: the stack is found with
``ItemArray.GetItemArray`` over ``ItemArray.GetAllBags()``, the total is ``Inventory.GetModelCount``,
and the id's own quantity is ``Item.Properties.GetQuantity``. A change in the model total after the call
is the client having consumed the drink.

Connecting is a write (the call acts on the client); ``Effects.GetAlcoholLevel`` is read as a second,
independent sign that the drink landed, and disconnect removes the hooks afterwards.

Usage: (elevated) python tests/probe_use_item_live.py [report-path]
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import py4gw
from py4gw.effect import Effects
from py4gw.inventory import Inventory
from py4gw.item import Item
from py4gw.item_array import ItemArray
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: ``ModelID.Hard_Apple_Cider`` (``enums_src/model_enums.py:1350``).
CIDER_MODEL = 28435

#: The owner counted 223 in the stack; the probe reads it rather than trusting it, and reports both.
EXPECTED_BEFORE = 223

#: How long the client may take to apply the drink.
WAIT_SECONDS = 12.0


def _ask(label: str, call: Any) -> Any:
    """One ported read; an exception is reported, never hidden."""

    try:
        return call()
    except Exception as error:
        return f"{type(error).__name__}: {error}"


def _read_state() -> dict[str, Any]:
    """Everything the experiment compares, read the ported way."""

    found: list[dict[str, Any]] = []
    bags = _ask("GetAllBags", ItemArray.GetAllBags)
    item_ids = _ask("GetItemArray", lambda: ItemArray.GetItemArray(bags)) if isinstance(bags, list) else []
    if isinstance(item_ids, list):
        for item_id in item_ids:
            plain = int(item_id.value) if hasattr(item_id, "value") else int(item_id)
            model = _ask("GetModelID", lambda i=plain: Item.GetModelID(i))
            if model == CIDER_MODEL:
                found.append(
                    {
                        "item_id": plain,
                        "quantity": _ask(
                            "GetQuantity", lambda i=plain: Item.Properties.GetQuantity(i)
                        ),
                        "slot": _ask("GetSlot", lambda i=plain: Item.GetSlot(i)),
                    }
                )
    return {
        "model_total": _ask(
            "GetModelCount", lambda: Inventory.GetModelCount(CIDER_MODEL)
        ),
        "stacks": found,
        "alcohol_level": _ask("GetAlcoholLevel", Effects.GetAlcoholLevel),
    }


def _run(report: dict[str, Any]) -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())
    report["cider_model"] = CIDER_MODEL

    with py4gw.connect(process) as client:
        bridge: Any = client._bridge
        report["hooks_installed"] = sorted(bridge.require_hooker().installed)

        before = _read_state()
        report["before"] = before
        report["expected_before"] = EXPECTED_BEFORE
        total_before = before["model_total"]
        stacks = before["stacks"]
        if not stacks:
            report["error"] = (
                f"no item with model {CIDER_MODEL} (Hard Apple Cider) is in the bags; nothing to use"
            )
            return write_report(report)

        item_id = int(stacks[0]["item_id"])
        report["used_item_id"] = item_id

        started = time.time()
        report["call"] = _ask("Inventory.UseItem", lambda: Inventory.UseItem(item_id))
        report["call_returned_after_s"] = round(time.time() - started, 3)

        deadline = started + WAIT_SECONDS
        after = _read_state()
        while time.time() < deadline:
            if isinstance(total_before, int) and after["model_total"] == total_before - 1:
                break
            time.sleep(0.25)
            after = _read_state()

        report["after"] = after
        report["seconds_to_consume"] = round(time.time() - started, 3)
        report["consumed"] = (
            isinstance(total_before, int)
            and after["model_total"] == total_before - 1
        )
        report["note"] = (
            "the write connection was used: `Inventory.UseItem` ran the source's whole chain into the "
            "client. Disconnecting removed the hooks and freed what was placed."
        )

    report["hooks_after_disconnect"] = sorted(bridge.require_hooker().installed)
    return write_report(report)


def main() -> int:
    """Run the probe and report even if the connection or a handler fails on the way out."""

    report: dict[str, Any] = {}
    try:
        return _run(report)
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
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
