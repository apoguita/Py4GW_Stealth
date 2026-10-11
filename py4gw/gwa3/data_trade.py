"""GwAu3's `Trade_GetTradeInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's trade window state -- the flags word, both sides' gold and item counts, and the pending operation. GwAu3 reads the record its own ``Trade_GetTradePtr`` resolves; this project reads the same record as `TradeContextStruct` through `py4gw/client.py:1593`'s `read_trade_context`, whose offsets match GwAu3's exactly.

**GwAu3's four state cases compare the whole flags word and this port's properties test bits, so the whole-word comparison is what is wire here.** With ``flags = 3`` (initiated and an offer submitted) GwAu3 answers `IsTradeInitiated` **False** while `TradeContextStruct.is_trade_initiated` answers True -- different questions, and the source's is the one a migrating script asks. `IsSubmitted` and `IsConfirmed` do agree with the port's ``is_trade_offered``/``is_trade_accepted`` (the same bits 2 and 4), and they are answered by mask.

**Three keys refuse rather than answer an address**: both item-array pointers and the partner's name. The item readers that would use the pointers walk the port's own `TradePlayerStruct.offered_items` instead, and the partner's name has no field here to read.

`Trade_GetTradeInfo` is one ``Switch`` over 17 keys in GwAu3
(``GwAu3_Data_Trade.au3``). 6 of the 17 field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct

from typing import Any

from ..client import require_client
from ..context import TradeContextStruct

_UNIMPLEMENTED: dict[str, str] = {'PlayerItemsPtr': 'GwAu3_Data_Trade.au3:29 answers the client address at ``+0x14``. This layer hands out no address; `Trade_GetPlayerTradeItemsInfo` and `Trade_GetArrayPlayerTradeItems` walk the same array through `TradePlayerStruct.offered_items` (`py4gw/context/trade_context.py:52`).', 'PartnerItemsPtr': 'GwAu3_Data_Trade.au3:36 answers the client address at ``+0x28``. Refused for the same reason; the partner item readers walk `partner_offer` (`py4gw/context/trade_context.py:142`).', 'PartnerName': "GwAu3_Data_Trade.au3:51-54 reads a pointer at ``+0x38`` and then a ``wchar[32]`` at that address. This project's `TradeContextStruct` is exactly ``0x38`` bytes (asserted at `py4gw/context/trade_context.py:200`), so it names no field there and this port has no partner-name read to route to."}

_COMPUTED: frozenset[str] = frozenset(['IsBusy', 'IsPlayerTradeAccepted', 'IsPlayerTradeOffered', 'IsTradeClosed', 'IsTradeInitiated', 'PartnerItemCount', 'PendingOp', 'PlayerItemCount'])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


def _read_isconfirmed(record: Any) -> bool:
    """``GwAu3_Data_Trade.au3`` -- the ``IsConfirmed`` case: ``BitAND(flags, 0x4) <> 0``."""

    return bool(record.flags & 0x4)


def _read_issubmitted(record: Any) -> bool:
    """``GwAu3_Data_Trade.au3`` -- the ``IsSubmitted`` case: ``BitAND(flags, 0x2) <> 0``."""

    return bool(record.flags & 0x2)


def _read_partneritemsptr(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartnerItemsPtr"])


def _read_partnername(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartnerName"])


def _read_playeritemsptr(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PlayerItemsPtr"])



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Flags": lambda record: record.flags,
        "IsBusy": lambda record, record_id: int(record.h0004[0]) != 0,
        "IsConfirmed": _read_isconfirmed,
        "IsPlayerTradeAccepted": lambda record, record_id: int(record.flags) == 7,
        "IsPlayerTradeOffered": lambda record, record_id: int(record.flags) == 3,
        "IsSubmitted": _read_issubmitted,
        "IsTradeClosed": lambda record, record_id: int(record.flags) == 0,
        "IsTradeInitiated": lambda record, record_id: int(record.flags) == 1,
        "PartnerGold": lambda record: record.partner.gold,
        "PartnerItemCount": lambda record, record_id: int(record.partner.items.m_size),
        "PartnerItemsPtr": _read_partneritemsptr,
        "PartnerName": _read_partnername,
        "PendingOp": lambda record, record_id: int(record.h0004[0]),
        "PlayerGold": lambda record: record.player.gold,
        "PlayerItemCount": lambda record, record_id: int(record.player.items.m_size),
        "PlayerItemsPtr": _read_playeritemsptr,
        "State": lambda record: record.flags,
    }
)


def Trade_GetTradeInfo(info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Trade.au3``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record(info)
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, info)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``client.read_trade_context()`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return client.read_trade_context()

"""``GwAu3_Data_Trade.au3``'s **offered-item** readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism `data_party`'s member accessors and `data_map`'s character and instance readers use:
``data_trade.py`` is rewritten whole on every run, so a function written straight into it would be lost
the next time the generator ran.

**What this file carries, and what it deliberately does not.** ``GwAu3_Data_Trade.au3`` declares five
readers. The first, ``Trade_GetTradeInfo`` (``:10-59``), is one ``Switch`` over a string key reading
fields of the trade record at fixed offsets -- which is the shape `tools/generate_gwa3_family.py` exists
to express -- so it is the **family's generated accessor** and is not defined here: a second definition
under the same name would obscure the generated one, the defect the generator's own comment records for
the item family's record lookup. Its keys, and the field of this project's record that answers each, are
the family's `masks` / `equalities` / `computed` / `unimplemented` tables; the three keys that answer a
client address refuse there rather than here.

The four *derived* readers below resolve the trade record's arrays and walk them, which is the
hand-written part:

* ``Trade_GetPlayerTradeItemsInfo`` (``:61-81``) and ``Trade_GetPartnerTradeItemsInfo`` (``:83-103``) --
  one column of one offered slot;
* ``Trade_GetArrayPlayerTradeItems`` (``:105-127``) and ``Trade_GetArrayPartnerTradeItems``
  (``:129-151``) -- a whole offer as ``(ModelID, Quantity)`` rows behind a header row carrying the count.

``Trade_GetTradePtr`` (``:4-8``) is carried below, and it answers **the record**: GwAu3's body resolves
the trade context and answers its client *address*, which this layer never hands out, so the member
answers the `TradeContextStruct` that address holds -- read on demand by
`client.read_trade_context` (``py4gw/client.py:1593``) -- or ``0``, which is GwAu3's own answer for a
null pointer.

**The records are this project's own, and their offsets are GwAu3's.** The trade root is read on demand
by `py4gw.client.RemoteClient.read_trade_context` (``py4gw/client.py:1593``) as `TradeContextStruct`
(``py4gw/context/trade_context.py:100``) -- a fixed ``0x38``-byte record whose ``flags`` sits at
``+0x0``, whose player ``gold`` sits at ``+0x10`` and partner ``gold`` at ``+0x24``, and whose two
offered-item arrays sit at ``+0x14`` and ``+0x28``. Each array is a `GWArray`
(``py4gw/context/gw_array.py:35-44``) whose ``m_buffer`` is the word GwAu3 reads as ``PlayerItemsPtr`` /
``PartnerItemsPtr`` and whose ``m_size`` is the count it reads at ``+0x1C`` / ``+0x30``; the elements are
`TradeItemStruct` (``py4gw/context/trade_context.py:22-26``), two dwords at the very ``0x08`` stride
GwAu3 multiplies by. `TradePlayerStruct.offered_items` (``py4gw/context/trade_context.py:52``) is the
port's own walk of that array, and it is the walk these readers use.

**Two of the source's own keys answer an address, so these readers do not go through them.**
``Trade_GetTradeInfo("PlayerItemsPtr")`` and ``("PartnerItemsPtr")`` return the array's address, which
this layer refuses; each reader therefore makes the source's own ``If $l_p_ItemsPtr = 0`` test on the
port's own ``items.m_buffer`` field -- the same word of the same record.

**``py4gw/trade.py`` does not exist.** The port's trade state is read in exactly one place,
`py4gw/context/trade_context.py`, through `client.read_trade_context()`
(``py4gw/client.py:1593``); nothing here keeps a copy of it, and every reader reads the record when it
is called.
"""


def Trade_GetTradePtr() -> Any:
    """The trade context record (``GwAu3_Data_Trade.au3:4-8``).

    GwAu3 resolves ``BasePointer[0][0x18][0x58]`` with its own ``Memory_ReadPtr`` and answers that
    client *address*; this answers **the record** the same slot holds, read through this project's own
    member: `py4gw.client.ConnectedClient.read_trade_context` (``py4gw/client.py:1593``) over
    `TradeContextStruct` (`py4gw/context/trade_context.py:100`, its ``0x38`` size asserted at ``:200``)
    -- the record every reader in this module and every key of `Trade_GetTradeInfo` reads, and the
    ``0x58`` is that structure's own offset in the game context (`GameContextStruct.trade_context`,
    `py4gw/context/game_context.py:52`).

    ``0`` when no trade is open, which is GwAu3's own answer for a null pointer -- and the value its own
    callers test (`If $l_p_Ptr = 0 ... Then Return 0`, `:12`).

    **The divergence, in one sentence:** GwAu3 hands back a client address and this hands back the record
    that address holds, the substitution `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`) and
    `Agent_GetAgentPtr` already record.
    """

    deal = require_client().read_trade_context()
    return 0 if deal is None else deal


def Trade_GetPlayerTradeItemsInfo(a_i_TradeSlot: Any = 0, a_s_Info: Any = "") -> Any:
    """One column of one item the player has offered (``GwAu3_Data_Trade.au3:61-81``).

    The source's guard order is kept: an empty column name answers ``0`` (``:63``), a trade the client
    is not holding answers ``0`` (the same guard's other arm -- its ``$l_p_ItemsPtr = 0``), a count of
    zero or a slot at or past the count answers ``0`` (``:66``), and a name outside the three it
    recognises answers ``0``, which is its ``Switch`` with no ``Case Else`` falling through to the same
    ``Return 0`` (``:80``).

    ``ItemID`` and ``Quantity`` are the two dwords of the slot's `TradeItemStruct`
    (``py4gw/context/trade_context.py:22-26``) at GwAu3's own ``0x08`` stride, and ``ModelID`` is the
    source's own second call, `Item_GetItemInfoByItemID(item_id, "ModelID")` (``:77``) -- the ported item
    table, called with the id the slot carries.

    **One divergence, and it is the address.** ``:62`` resolves the array through
    ``Trade_GetTradeInfo("PlayerItemsPtr")`` and tests it for zero; this layer hands out no address, so
    that key refuses here and the test is made on ``items.m_buffer`` -- the same word. The count is
    ``items.m_size``, the dword ``Trade_GetTradeInfo("PlayerItemCount")`` answers at ``+0x1C``
    (``py4gw/context/gw_array.py:42``), read from the record already in hand rather than by a second
    resolution of the trade pointer, so the count and the array come from one read of one record.
    """

    if a_s_Info == "":
        return 0

    deal = require_client().read_trade_context()
    if deal is None:
        return 0

    offer = deal.player_offer
    items = offer.offered_items

    # `:63` -- `If $l_p_ItemsPtr = 0`: the array has no buffer (or the port's own walk declines a header
    # it cannot trust), which is the source's own "there is no array here".
    if int(offer.items.m_buffer) == 0 or not items:
        return 0

    # `:65-66` -- the count guard, then the slot's own bound.
    count = int(offer.items.m_size)
    if count == 0 or int(a_i_TradeSlot) >= count:
        return 0

    item = items[int(a_i_TradeSlot)]

    if a_s_Info == "ItemID":
        return int(item.item_id)
    if a_s_Info == "Quantity":
        return int(item.quantity)
    if a_s_Info == "ModelID":
        from .data_item import Item_GetItemInfoByItemID

        return Item_GetItemInfoByItemID(int(item.item_id), "ModelID")

    # Anything else: GwAu3's own `Return 0` after its `Switch` (`:80`).
    return 0


def Trade_GetPartnerTradeItemsInfo(a_i_TradeSlot: Any = 0, a_s_Info: Any = "") -> Any:
    """One column of one item the **partner** has offered (``GwAu3_Data_Trade.au3:83-103``).

    The player form's twin, over the partner side of the same record: the source repeats its body
    verbatim with ``PartnerItemsPtr`` (``:84``) and ``PartnerItemCount`` (``:87``), and so does this --
    the partner ``gold``/array pair sits at ``+0x24``/``+0x28`` and its count at ``+0x30``, which is
    `TradeContextStruct.partner` (``py4gw/context/trade_context.py:113``) reached through
    `TradeContextStruct.partner_offer` (``py4gw/context/trade_context.py:142``).

    The divergence is the player form's: the address GwAu3 tests is answered here by the port's own
    ``items.m_buffer`` field, and the count by ``items.m_size``.
    """

    if a_s_Info == "":
        return 0

    deal = require_client().read_trade_context()
    if deal is None:
        return 0

    offer = deal.partner_offer
    items = offer.offered_items

    # `:85` -- `If $l_p_ItemsPtr = 0`, on the partner array.
    if int(offer.items.m_buffer) == 0 or not items:
        return 0

    # `:87-88` -- the partner count guard, then the slot's own bound.
    count = int(offer.items.m_size)
    if count == 0 or int(a_i_TradeSlot) >= count:
        return 0

    item = items[int(a_i_TradeSlot)]

    if a_s_Info == "ItemID":
        return int(item.item_id)
    if a_s_Info == "Quantity":
        return int(item.quantity)
    if a_s_Info == "ModelID":
        from .data_item import Item_GetItemInfoByItemID

        return Item_GetItemInfoByItemID(int(item.item_id), "ModelID")

    # Anything else: GwAu3's own `Return 0` after its `Switch` (`:102`).
    return 0


def Trade_GetArrayPlayerTradeItems() -> Any:
    """Every item the player has offered, as ``(ModelID, Quantity)`` rows
    (``GwAu3_Data_Trade.au3:105-127``).

    **The return shape is GwAu3's, including both of its shapes.** A count of zero answers a
    **one-element** array holding ``0`` (``:108-111``); otherwise the answer is a two-dimensional array
    of ``count + 1`` rows whose row ``0`` carries the count in its first cell and whose remaining rows
    are ``(ModelID, Quantity)`` (``:113-124``), answered here as a list of rows -- the same substitution
    `UAI_GetAgentVisibleEffectInfo` makes for its AutoIt array. When the count is non-zero but the
    array's own buffer is zero, the source returns that array with its item rows still zero
    (``:116-117``), and this answers the same rows.

    **One divergence, and it is the second call.** ``:121`` reads the slot's dword and asks
    ``Item_GetItemInfoByPtr`` for its ``ModelID``; that member takes a **record** in this port rather
    than the id GwAu3 hands it (``py4gw/gwa3/data_item.py:330``, which routes to the id-keyed table), so
    the ``ModelID`` comes from `Item_GetItemInfoByItemID` -- the same table and the same answer, and the
    very call this file's other spelling makes at ``:77``. The count and the address test are the player
    info form's: ``items.m_size`` and ``items.m_buffer``, the two words ``Trade_GetTradeInfo`` answers
    for ``PlayerItemCount`` and ``PlayerItemsPtr``.
    """

    deal = require_client().read_trade_context()
    if deal is None:
        # `:106` -- `Trade_GetTradeInfo("PlayerItemCount")` answers 0 when there is no trade record,
        # which is the source's own `If $l_i_ItemCount = 0 Then Return [0]` (`:108-111`).
        return [0]

    offer = deal.player_offer
    count = int(offer.items.m_size)
    if count == 0:
        return [0]

    if int(offer.items.m_buffer) == 0:
        # `:116-117` -- `If $l_p_ItemsPtr = 0 Then Return $l_ai2_Items`: the header row the source
        # already filled in, with the item rows it never wrote still zero.
        return [[count, 0]] + [[0, 0] for _ in range(count)]

    from .data_item import Item_GetItemInfoByItemID

    rows: list[Any] = [[count, 0]]
    for item in offer.offered_items:
        rows.append(
            [
                Item_GetItemInfoByItemID(int(item.item_id), "ModelID"),
                int(item.quantity),
            ]
        )
    return rows


def Trade_GetArrayPartnerTradeItems() -> Any:
    """Every item the **partner** has offered, as ``(ModelID, Quantity)`` rows
    (``GwAu3_Data_Trade.au3:129-151``).

    The player form's twin, over the partner side: the source repeats its body verbatim with
    ``PartnerItemCount`` (``:130``) and ``PartnerItemsPtr`` (``:140``), and so does this -- the count is
    the partner array's ``m_size`` at ``+0x30`` and the buffer its ``m_buffer`` at ``+0x28``. The return
    shapes are the player form's two, unchanged.
    """

    deal = require_client().read_trade_context()
    if deal is None:
        # `:130` -- no trade record answers a count of 0, which is `:132-135`.
        return [0]

    offer = deal.partner_offer
    count = int(offer.items.m_size)
    if count == 0:
        return [0]

    if int(offer.items.m_buffer) == 0:
        # `:140-141` -- the source's zero-buffer early return, with its item rows left zero.
        return [[count, 0]] + [[0, 0] for _ in range(count)]

    from .data_item import Item_GetItemInfoByItemID

    rows: list[Any] = [[count, 0]]
    for item in offer.offered_items:
        rows.append(
            [
                Item_GetItemInfoByItemID(int(item.item_id), "ModelID"),
                int(item.quantity),
            ]
        )
    return rows

__all__ = ['Trade_GetTradeInfo', 'Trade_GetTradePtr', 'Trade_GetArrayPartnerTradeItems', 'Trade_GetArrayPlayerTradeItems', 'Trade_GetPartnerTradeItemsInfo', 'Trade_GetPlayerTradeItemsInfo']
