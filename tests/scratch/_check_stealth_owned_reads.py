"""Ad-hoc check (not a unittest) for the members re-answered in this batch.

Run: python tests/scratch/_check_stealth_owned_reads.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

import py4gw  # noqa: E402
from py4gw.gwa3 import data_item, data_map_context, data_merchant, data_ui  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "FAIL"), name, detail)
    if not condition:
        failures.append(name)


# --- the derived quote change detector ------------------------------------------------------
# It is advanced by what this layer reads (the port's MerchantListener), not by any hook into the
# library: the peer of these checks is that `py4gw/merchant.py` carries no gwa3 import at all.
from py4gw.listeners import Merchant as _MerchantListener  # noqa: E402

listener = _MerchantListener()
listener.ResetQuote()

first = data_merchant.Merchant_GetTraderQuoteID()
check("no quote stands at the start", first == 0, f"value={first}")
check(
    "a second read of the same no-quote state does not move it",
    data_merchant.Merchant_GetTraderQuoteID() == first,
)

listener.OnPriceReceived(0x1234, 250)
second = data_merchant.Merchant_GetTraderQuoteID()
check("a standing quote moves it", second == first + 1, f"{first} -> {second}")
check(
    "reading the same standing quote again does not move it",
    data_merchant.Merchant_GetTraderQuoteID() == second,
)

listener.ResetQuote()
check(
    "the reset sentinel (-1) does not move it",
    data_merchant.Merchant_GetTraderQuoteID() == second,
)

listener.OnPriceReceived(0x1234, 400)
third = data_merchant.Merchant_GetTraderQuoteID()
check("a changed price on the same item moves it", third == second + 1, f"{second} -> {third}")

# --- the array that carries it -------------------------------------------------------------
info = data_merchant.Merchant_GetTraderQuoteInfo()
check("quote info is three ints", len(info) == 3 and all(isinstance(v, int) for v in info), str(info))
check("element 0 is the detector", info[0] == data_merchant.Merchant_GetTraderQuoteID())

# --- the library carries no trace of the layer ----------------------------------------------
import py4gw.client as client_module  # noqa: E402
from py4gw.merchant import MerchantQuoteInfo, _request_quote  # noqa: E402


class _FakeBridge:
    def write_data(self, offset: int, payload: bytes) -> int:
        return 0x1000 + offset


class _FakeClient:
    bridge = _FakeBridge()

    def resolves(self, name: str) -> bool:
        return True

    def call_function(self, *args, **kwargs) -> None:
        return None


original = client_module.require_client
client_module.require_client = lambda: _FakeClient()
try:
    before = data_merchant.Merchant_GetTraderQuoteID()
    answered = _request_quote(8, MerchantQuoteInfo(0, 0, 0), MerchantQuoteInfo(0, 1, 0x10))
    after = data_merchant.Merchant_GetTraderQuoteID()
finally:
    client_module.require_client = original

check("the ported quote request still answers True", answered is True)
check(
    "the ported quote request does not touch the layer's counter (no library-side hook)",
    after == before,
    f"{before} -> {after}",
)
check(
    "the ported merchant module imports no gwa3",
    "gwa3" not in Path("py4gw/merchant.py").read_text(encoding="utf-8"),
)

# --- the two refusals that stay refusals ----------------------------------------------------
for name, callable_ in (
    ("Ui_GetRenderDisabled", data_ui.Ui_GetRenderDisabled),
    ("Ui_GetRenderEnabled", data_ui.Ui_GetRenderEnabled),
):
    try:
        callable_()
    except NotImplementedError as error:
        check(f"{name} still refuses, with its rule", "NOT APPLICABLE" in str(error))
    else:
        check(f"{name} still refuses", False, "it answered")

for key in ("Terrain", "Zones"):
    try:
        data_map_context.Map_GetMapContextInfo(key)
    except NotImplementedError as error:
        check(
            f"Map_GetMapContextInfo({key!r}) refuses before the client, naming the read",
            "missing read, named exactly" in str(error),
        )
    else:
        check(f"Map_GetMapContextInfo({key!r}) refuses", False, "it answered")

try:
    data_merchant.Merchant_GetBuyItemBase()
except NotImplementedError as error:
    check(
        "Merchant_GetBuyItemBase names its missing read",
        "BuyItemBase` address and a named record" in str(error),
    )
else:
    check("Merchant_GetBuyItemBase refuses", False, "it answered")

# --- the item helpers' own guards (no client needed for the zero address) --------------------
check("_bag_at_address(0) is None", data_item._bag_at_address(0) is None)
check("_inventory_at_address(0) is None", data_item._inventory_at_address(0) is None)
check(
    "the item members exist and are exported",
    all(
        hasattr(data_item, name)
        for name in (
            "Item_GetItemInventoryID",
            "Item_GetInventoryIDByAgentID",
            "Item_GetMaxItems",
        )
    ),
)

# --- the item chain, over a stand-in client ------------------------------------------------
import ctypes  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from py4gw.context import BagStruct, GWArray, InventoryStruct  # noqa: E402

BAG = 0x2000
INVENTORY = 0x3000


def _bag_bytes() -> bytes:
    bag = BagStruct()
    bag.bag_type = 1
    bag.index = 1
    bag.bag_array = INVENTORY
    return bytes(bag)


def _inventory_bytes() -> bytes:
    inventory = InventoryStruct()
    inventory.bags[0] = 0xABCD1234
    return bytes(inventory)


class _ItemReader:
    def read(self, address: int, size: int) -> bytes:
        if address == BAG:
            return _bag_bytes()
        if address == INVENTORY:
            return _inventory_bytes()
        raise OSError(f"unexpected read at 0x{address:X} ({size} bytes)")


ITEM_CONTEXT_ARRAY = GWArray()
ITEM_CONTEXT_ARRAY.m_buffer = 0x4000
ITEM_CONTEXT_ARRAY.m_capacity = 4096
ITEM_CONTEXT_ARRAY.m_size = 341

HERO_LEVEL = 20
HERO_AGENT = 9


class _ItemClient:
    reader = _ItemReader()

    def read_item_context(self):
        return SimpleNamespace(item_array=ITEM_CONTEXT_ARRAY)

    def read_world_context(self):
        return SimpleNamespace(
            hero_flags=[SimpleNamespace(agent_id=HERO_AGENT, level=HERO_LEVEL)]
        )


item_client = _ItemClient()
original_item_require = data_item.require_client
original_get_ptr = data_item.Item_GetItemPtr
original_get_inventory = data_item.Item_GetInventoryPtr
original_convert = data_item.Agent_ConvertID
original_mine = data_item.Agent_GetMyID
data_item.require_client = lambda: item_client
data_item.Item_GetItemPtr = lambda item: SimpleNamespace(bag=BAG, bag_equipped=0)
data_item.Item_GetInventoryPtr = lambda: SimpleNamespace(unused_bag=0x5555)
try:
    check(
        "Item_GetItemInventoryID answers the inventory record's first dword",
        data_item.Item_GetItemInventoryID(1) == 0xABCD1234,
        hex(data_item.Item_GetItemInventoryID(1)),
    )
    check(
        "Item_GetMaxItems answers the item array's own m_size word",
        data_item.Item_GetMaxItems() == 341,
        str(data_item.Item_GetMaxItems()),
    )
    data_item.Agent_ConvertID = lambda agent: int(agent)
    data_item.Agent_GetMyID = lambda: 7
    check(
        "an agent that is not mine reads the hero flag array's +0x8 word",
        data_item.Item_GetInventoryIDByAgentID(HERO_AGENT) == HERO_LEVEL,
    )
    check(
        "an agent with no flag entry answers 0",
        data_item.Item_GetInventoryIDByAgentID(1234) == 0,
    )
    data_item.Agent_GetMyID = lambda: HERO_AGENT
    check(
        "my own id answers the inventory record instead",
        data_item.Item_GetInventoryIDByAgentID(HERO_AGENT) == 0x5555,
    )
    check(
        "a zero agent id answers 0 before anything is read",
        data_item.Item_GetInventoryIDByAgentID(0) == 0,
    )
finally:
    data_item.require_client = original_item_require
    data_item.Item_GetItemPtr = original_get_ptr
    data_item.Item_GetInventoryPtr = original_get_inventory
    data_item.Agent_ConvertID = original_convert
    data_item.Agent_GetMyID = original_mine

check(
    "the item records' sizes are what the reads bind",
    ctypes.sizeof(BagStruct) == 0x28 and ctypes.sizeof(InventoryStruct) == 0x98,
)

# --- the salvage-session answer -------------------------------------------------------------
SALVAGE_ITEM = 4242


class _SalvageClient:
    def read_salvage_session(self):
        return SimpleNamespace(item_id=SALVAGE_ITEM)


original_require = client_module.require_client
client_module.require_client = lambda: _SalvageClient()
try:
    check(
        "Merchant_GetSalvageGlobal answers the session's item id",
        data_merchant.Merchant_GetSalvageGlobal() == SALVAGE_ITEM,
    )
finally:
    client_module.require_client = original_require

client_module.require_client = lambda: SimpleNamespace(read_salvage_session=lambda: None)
try:
    check(
        "no open salvage session answers 0",
        data_merchant.Merchant_GetSalvageGlobal() == 0,
    )
finally:
    client_module.require_client = original_require

print()
print(f"{len(failures)} failure(s)" + (": " + ", ".join(failures) if failures else ""))
sys.exit(1 if failures else 0)
