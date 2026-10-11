"""GwAu3's ``Merchant_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Two of the seven are routed and five refuse, and this module is the clearest case in the layer of
"the port has the members but not the sequence".** GwAu3's merchant functions are long procedures built
on two layers this project does not have -- its own memory reads (``Memory_Read($p + 0x2C)`` for a model
id, ``+0x4C`` for a quantity) and its injected assembler stub (``Core_Enqueue``) -- wrapped around a
**quote dance**: request a quote, poll one of GwAu3's own memory slots until it changes, read the cost
from another, then buy or sell.

**The port holds every value that dance moves between.** ``py4gw/merchant.py`` has
`Trading.Trader.RequestQuote`, `RequestSellQuote`, `GetQuotedItemID` and `GetQuotedValue` -- the same
two slots GwAu3 polls as ``$g_i_TraderCostID`` and ``$g_f_TraderCostValue`` -- and
`Trading.Merchant.BuyItem`, `SellItem`, `Trading.Crafter.CraftItem` and `Trading.Collector.ExchangeItem`
for the transactions themselves. What is missing is the *sequence*, and reproducing it exactly is the
work: GwAu3's loops carry a per-item selling threshold, a two-second timeout with its own log line, and
a quantity negotiation a caller depends on. Naming that is more useful than a sequence written here
that differs from the source's in the places that matter, so each refusal names the members the route
will be built from.
"""

from __future__ import annotations

from typing import Any

from ..item import Item
from ..merchant import Trading

__all__ = [
    "Merchant_BuyItem",
    "Merchant_CollectorExchange",
    "Merchant_CraftItem",
    "Merchant_GetMerchantItemPtr",
    "Merchant_GetMerchantItemsBase",
    "Merchant_GetMerchantItemsSize",
    "Merchant_SellItem",
]

#: GwAu3's two item-search modes for `Merchant_GetMerchantItemPtr` (``GwAu3_Cmd_Merchant.au3:18``):
#: ``0`` searches by model id and ``1`` by the item's one-based slot in the merchant's list.
_MODE_MODEL_ID = 0
_MODE_SLOT = 1


def Merchant_GetMerchantItemsSize() -> int:
    """How many items the open merchant is offering (``GwAu3_Cmd_Merchant.au3:11-14``).

    GwAu3 reads a count out of its own pointer chain (``BasePointer[0x18][0x2C][0x28]``); the ported
    member returns the offered items as a list, so the count is the list's length. The number means the
    same thing in both: how many entries the merchant's array holds.
    """

    return len(Trading.Merchant.GetOfferedItems())


def Merchant_GetMerchantItemPtr(value: Any, mode: Any = _MODE_MODEL_ID) -> int:
    """Find one of the merchant's offered items (``GwAu3_Cmd_Merchant.au3:18-40``).

    GwAu3's two modes are kept, and so is its walk: it reads the merchant's item ids one at a time,
    skips a zero, resolves each to a record, and answers on the first match -- by **model id** in mode
    ``0`` and by **one-based slot** in mode ``1``, with anything else answering ``0``.

    **The shape differs and the divergence is already recorded for `Agent_GetAgentPtr`.** GwAu3 answers
    a client *pointer*; this answers the item's **id**, because a client address is of no use to a
    caller here. A GwAu3 script that passes the result straight back into another ``Item_*`` function is
    passing something those functions resolve, and an id is what this layer's do.
    """

    mode = int(mode)
    if mode not in (_MODE_MODEL_ID, _MODE_SLOT):
        return 0

    offered = Trading.Merchant.GetOfferedItems()
    for index, item_id in enumerate(offered):
        if not item_id:
            continue
        if mode == _MODE_SLOT:
            if index + 1 == int(value):
                return int(item_id)
            continue
        if int(Item.GetModelID(int(item_id))) == int(value):
            return int(item_id)
    return 0


def Merchant_GetMerchantItemsBase() -> int:
    """**REFUSED: GwAu3 answers a client address, and this layer hands out none.**

    ``GwAu3_Cmd_Merchant.au3:4-9`` walks ``BasePointer[0x18][0x2C][0x24]`` and answers the merchant
    array's **base address** -- a raw client pointer a caller then reads with ``Memory_Read``. This
    project does not hand out client addresses: its own reads go through the ported classes, and an
    address would be of no use to a Python caller or, through the bridge, to an AutoIt one. The
    equivalent value is the offered-items list, which `Merchant_GetMerchantItemsSize` and
    `Merchant_GetMerchantItemPtr` already expose -- and `Trading.Merchant.GetOfferedItems` is the member
    both use.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Merchant.au3:4-9 answers the merchant array's **base address** from "
        "`BasePointer[0x18][0x2C][0x24]` -- a raw client pointer for a caller to read with "
        "`Memory_Read`. This project hands out no client addresses (`Agent_GetAgentPtr` records the same "
        "divergence and answers a record instead), and an address is useless across the bridge. The "
        "values a caller wants are already routed: `Trading.Merchant.GetOfferedItems` "
        "(`py4gw/merchant.py:558-562`) is the list this module's two other readers use."
    )


def Merchant_BuyItem(
    model_id: Any,
    quantity: Any = 1,
    trader: Any = False,
    mod_string: Any = "",
    extra_id: Any = -1,
) -> bool:
    """**REFUSED: the quote dance has no route yet, though every value it moves does.**

    ``GwAu3_Cmd_Merchant.au3:42-160`` is a long procedure with two arms. The **trader** arm walks
    GwAu3's item array for an entry whose model id matches and which is neither in the player's bags
    (``+0xC``) nor on the ground (``+0x4``), optionally matching a mod string or a dye extra id; then
    for each unit it requests a quote, polls ``$g_i_TraderQuoteID`` until it changes or two seconds
    pass, reads the cost, and buys. The **merchant** arm does the same against the merchant's own array.

    **What is missing is the sequence, not the capability.** The port holds the quote members
    (`Trading.Trader.RequestQuote`, `RequestSellQuote`, `GetQuotedItemID`, `GetQuotedValue` -- the same
    two slots GwAu3 polls) and the transaction (`Trading.Merchant.BuyItem`, `Trading.Trader.BuyItem`,
    each taking the id and the cost). Reproducing GwAu3's loop exactly -- its per-unit request, its
    two-second timeout, its quantity handling, and the item search's three-way filter -- is the work,
    and it is named rather than approximated: a sequence written here that differed in the timeout or
    the filter would buy the wrong item or the wrong number of them while answering `True`.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Merchant.au3:42-160 searches for the item (trader arm: GwAu3's item array filtered "
        "by model id, `+0xC` bag pointer and `+0x4` agent id, optionally by mod string or dye extra "
        "id), then per unit requests a quote and polls `$g_i_TraderQuoteID` with a two-second timeout "
        "before buying. The members the route needs are all ported -- `Trading.Trader.RequestQuote`, "
        "`GetQuotedItemID`, `GetQuotedValue` and `Trading.Merchant.BuyItem`/`Trading.Trader.BuyItem` in "
        "`py4gw/merchant.py` -- and the work is reproducing the loop exactly, including its timeout, its "
        "quantity handling and the three-way item filter. Answering True from a different sequence "
        "would buy the wrong item with nothing to show for it."
    )


def Merchant_SellItem(item: Any, quantity: Any = 0, trader: Any = False) -> bool:
    """**REFUSED: as `Merchant_BuyItem`, with a selling threshold the route must keep.**

    ``GwAu3_Cmd_Merchant.au3:161-244`` reads the stack count at ``+0x4C``, treats a quantity of ``0``
    as "sell all", **divides by ten for common materials** and sells those in tens
    (``:180-183``), then sells one unit at a time, requesting a sell quote and polling
    ``$g_i_TraderCostID`` before each. Its per-iteration timeout logs a warning and *breaks the loop*
    rather than failing the call, so a partial sale still answers success -- all of which a route has to
    reproduce rather than tidy up.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Merchant.au3:161-244 reads the stack count (`+0x4C`), treats `$a_i_Quantity = 0` as "
        "'sell all', **divides the count by ten for common materials** (`:180-183`) and sells those in "
        "tens, then sells unit by unit after a sell quote polled on `$g_i_TraderCostID` with a "
        "two-second timeout that `ExitLoop`s and still answers success on a partial sale. The ported "
        "members are `Trading.Trader.RequestSellQuote`, `GetQuotedItemID`, `GetQuotedValue` and "
        "`Trading.Merchant.SellItem` (`py4gw/merchant.py`); the work is the loop, threshold and partial-"
        "sale semantics included."
    )


def Merchant_CraftItem(
    crafted_item_model_id: Any,
    price: Any,
    req_materials: Any,
    quantity: Any = 1,
) -> bool:
    """**REFUSED: the material list is a `ByRef` 2-D AutoIt array on the way in.**

    ``GwAu3_Cmd_Merchant.au3:245-370`` takes ``$a_ai2_ReqMaterials`` -- the requirements as a two-column
    table -- and walks it, asking the crafter for a quote and then crafting per unit. The ported
    `Trading.Crafter.CraftItem` (`py4gw/merchant.py:564-572`) takes the same information as **two
    parallel lists** plus an item id and a cost, so the shape is close; what a faithful route has to
    settle is GwAu3's own table-walking (which entry is the material, which the quantity) and its
    per-unit quote poll. Named rather than guessed, because a mis-read column would craft the wrong
    item from the wrong materials.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Merchant.au3:245-370 walks `$a_ai2_ReqMaterials` -- the crafting requirements as a "
        "2-D table -- quoting and crafting per unit. This project's route exists in shape: "
        "`Trading.Crafter.CraftItem(item_id, cost, item_list, item_quantities)` "
        "(`py4gw/merchant.py:564-572`) takes two parallel lists for the same information "
        "(`Trading.Crafter.GetOfferedItems` supplies the item ids). The work is reproducing GwAu3's "
        "table walk and its per-unit quote poll exactly; a mis-read column crafts the wrong item."
    )


def Merchant_CollectorExchange(
    item_recv_model_id: Any,
    exchange_req: Any,
    item_give_model_id: Any,
) -> bool:
    """**REFUSED: no ported sequence for a collector exchange.**

    ``GwAu3_Cmd_Merchant.au3:371-479`` resolves both items through GwAu3's own pointer chain, writes
    the give-list into its own struct, enqueues it through the injected stub and polls for the
    transaction. The port holds the destination -- `Trading.Collector.ExchangeItem(item_id, cost,
    item_list, item_quantities)` (`py4gw/merchant.py:586`) and `Trading.Collector.GetOfferedItems`
    -- but not the resolution GwAu3 performs first (model id to item id for both sides) nor its
    transaction poll. The work is the sequence, and the members it will be built from are named here.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Merchant.au3:371-479 resolves the received and given items through GwAu3's own "
        "pointer chain, writes its give-list struct and enqueues it through the injected stub, then "
        "polls for the transaction. The port's destination exists -- "
        "`Trading.Collector.ExchangeItem(item_id, cost, item_list, item_quantities)` "
        "(`py4gw/merchant.py:586`) over `Trading.Collector.GetOfferedItems` -- but the item resolution "
        "and the transaction poll are the work, and they are named rather than approximated."
    )
