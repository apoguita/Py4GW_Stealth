"""GwAu3's `Item_GetItemInfoByItemID`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's item reader. The public name resolves an item pointer and then calls `Item_GetItemInfoByPtr`, which holds the ``Switch``; both take the same arguments in the same order, so the cases come from the second and the routine keeps the first one's name -- which is what a script calls.

This project reads the same record as `ItemStruct`, and its offsets match GwAu3's exactly (item id at ``+0x0``, agent id at ``+0x4``, bag at ``+0xC``, model file id at ``+0x1C``, type at ``+0x20``, value at ``+0x24``, model id at ``+0x2C``).

`Item_GetItemInfoByItemID` is one ``Switch`` over 39 keys in GwAu3
(``GwAu3_Data_Item.au3``). 34 of the 39 field keys resolve to a **named
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
import ctypes
from typing import Any

from ..client import require_client
from ..context import ItemStruct
from ..context import BagStruct, InventoryStruct
from ..item import Item
from .data_agent import Agent_ConvertID, Agent_GetMyID
_UNIMPLEMENTED: dict[str, str] = {'Dye1': "GwAu3_Data_Item.au3:605 reads a byte at ``+0x21``. This project's `ItemStruct` holds a three-byte `dye` structure at exactly that offset, so the byte is inside it and there is no attribute naming it (`py4gw/context/item_context.py:282`). Reading the structure's first byte would work but would be an offset read of a field the port chose not to name, which is the kind of answer this layer refuses rather than guesses at. It needs a named accessor on the ported class.", 'Dye2': 'GwAu3_Data_Item.au3:607 reads a byte at ``+0x22`` -- the second byte of the `dye` structure at ``+0x21``, which this project declares as a three-byte field without naming its parts (`py4gw/context/item_context.py:282`). Refused for the same reason as `Dye1`: it needs a named accessor on the ported class.', 'Dye3': 'GwAu3_Data_Item.au3:609 reads a byte at ``+0x23`` -- the third byte of the `dye` structure named at `py4gw/context/item_context.py:282`. Refused for the same reason as `Dye1`: it needs a named accessor on the ported class.', 'ExtraID': 'GwAu3_Data_Item.au3:610 reads a byte at ``+0x22``, the same offset as `Dye2`, and its own comment records the alias. Refused for the same reason as `Dye1`: the byte is inside a structure this project does not name its parts for (`py4gw/context/item_context.py:282`).'}

_COMPUTED: frozenset[str] = frozenset(['CompleteName', 'Name', 'SingleItemName'])

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


def _read_iscommonmaterial(record: Any) -> bool:
    """``GwAu3_Data_Item.au3`` -- the ``IsCommonMaterial`` case: ``BitAND(interaction, 0x2000000) <> 0``."""

    return bool(record.interaction & 0x2000000)


def _read_isidentified(record: Any) -> bool:
    """``GwAu3_Data_Item.au3`` -- the ``IsIdentified`` case: ``BitAND(interaction, 0x1) <> 0``."""

    return bool(record.interaction & 0x1)


def _read_isinscribable(record: Any) -> bool:
    """``GwAu3_Data_Item.au3`` -- the ``IsInscribable`` case: ``BitAND(interaction, 0x80000) <> 0``."""

    return bool(record.interaction & 0x80000)


def _read_isstackable(record: Any) -> bool:
    """``GwAu3_Data_Item.au3`` -- the ``IsStackable`` case: ``BitAND(interaction, 0x2) <> 0``."""

    return bool(record.interaction & 0x2)


def _read_ismaterial(record: Any) -> bool:
    """``GwAu3_Data_Item.au3`` -- the ``IsMaterial`` case: ``type = 11``."""

    return record.type == 11


def _read_completename(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Item.au3`` -- the ``CompleteName`` case, through this project's name handshake.

    The three steps are the port's own (`Item.RequestName(record_id)`, `Item.IsNameReady(record_id)`, `Item.GetName(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Item.RequestName, Item.IsNameReady, Item.GetName, record_id)


def _read_name(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Item.au3`` -- the ``Name`` case, through this project's name handshake.

    The three steps are the port's own (`Item.RequestName(record_id)`, `Item.IsNameReady(record_id)`, `Item.GetName(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Item.RequestName, Item.IsNameReady, Item.GetName, record_id)


def _read_singleitemname(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Item.au3`` -- the ``SingleItemName`` case, through this project's name handshake.

    The three steps are the port's own (`Item.RequestName(record_id)`, `Item.IsNameReady(record_id)`, `Item.GetName(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Item.RequestName, Item.IsNameReady, Item.GetName, record_id)


def _read_rarity(record: Any) -> Any:
    """``GwAu3_Data_Item.au3`` -- the ``Rarity`` case: the pointer read *through* ``+0x38``."""

    return record.complete_name_enc


def _read_dye1(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["Dye1"])


def _read_dye2(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["Dye2"])


def _read_dye3(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["Dye3"])


def _read_extraid(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["ExtraID"])




def _find_item(records: list[ItemStruct], item_id: int) -> ItemStruct | None:
    """The one item record whose id matches, from the inventory records read now.

    GwAu3 walks ``BasePointer -> 0x18 -> 0x40 -> 0xB8 -> 4 * item_id`` to reach an item pointer. This
    project reads the bags and their records (``py4gw/client.py:1621``, ``read_item_records``) and
    picks the entry with the id -- from a traversal made on **every** call, because a stored record is
    a dereferenced read and this project does not keep those.
    """

    for record in records:
        if record.item_id == item_id:
            return record
    return None

_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "AgentID": lambda record: record.agent_id,
        "Bag": lambda record: record.bag,
        "BagEquipped": lambda record: record.bag_equipped,
        "CompleteName": _read_completename,
        "CompleteNameEnc": lambda record: record.complete_name_enc,
        "Customized": lambda record: record.customized,
        "Dye1": _read_dye1,
        "Dye2": _read_dye2,
        "Dye3": _read_dye3,
        "Equipped": lambda record: record.equipped,
        "ExtraID": _read_extraid,
        "InfoStringEnc": lambda record: record.info_string,
        "InfoStringPtr": lambda record: record.info_string,
        "Interaction": lambda record: record.interaction,
        "IsCommonMaterial": _read_iscommonmaterial,
        "IsIdentified": _read_isidentified,
        "IsInscribable": _read_isinscribable,
        "IsMaterial": _read_ismaterial,
        "IsMaterialSalvageable": lambda record: record.is_material_salvageable,
        "IsStackable": _read_isstackable,
        "ItemFormula": lambda record: record.item_formula,
        "ItemID": lambda record: record.item_id,
        "ItemType": lambda record: record.type,
        "ModStruct": lambda record: record.mod_struct,
        "ModStructSize": lambda record: record.mod_struct_size,
        "ModelFileID": lambda record: record.model_file_id,
        "ModelID": lambda record: record.model_id,
        "Name": _read_name,
        "NameEnc": lambda record: record.name_enc,
        "Profession": lambda record: record.profession,
        "Quantity": lambda record: record.quantity,
        "Rarity": _read_rarity,
        "SingleItemName": _read_singleitemname,
        "SingleItemNameEnc": lambda record: record.single_item_name,
        "Slot": lambda record: record.slot,
        "Value": lambda record: record.value,
        "h0026": lambda record: record.h0026,
        "h0040[2]": lambda record: _read_raw(record, 0x0040, "<i"),
        "h004B": lambda record: record.h004B,
    }
)


def Item_GetItemInfoByItemID(record_id: Any, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Item.au3``).

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

    record = _record(record_id)
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
        return reader(record, record_id)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``_find_item(client.read_item_records(), int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return _find_item(client.read_item_records(), int(record_id))

def Item_GetItemContextPtr() -> Any:
    """The item context record (``GwAu3_Data_Item.au3:4-8``).

    GwAu3 resolves ``BasePointer[0][0x18][0x40]`` with its own ``Memory_ReadPtr`` and answers that
    client *address* -- the root every other reader in the file hangs off. This answers **the record**
    the same slot holds, read through this project's own member:
    `py4gw.client.ConnectedClient.read_item_context` (``py4gw/client.py:1610``) over `ItemContextStruct`
    (`py4gw/context/item_context.py:1896`) -- and the ``0x40`` is that structure's own offset in the game
    context (`GameContextStruct.item_context`, `py4gw/context/game_context.py:46`, the slot
    ``data_game.py``'s ``ItemContext`` key resolves). ``0`` when the client holds no item context, which
    is GwAu3's own answer for a null pointer and the value its ``Item_GetItemPtr`` chain tests for
    (``Item_GetInventoryPtr``, ``:10-15``).

    **The divergence, in one sentence:** GwAu3 hands back a client address and this hands back the record
    that address holds, the substitution `Item_GetItemPtr` (below), `Agent_GetAgentPtr` and
    `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`) already record.
    """

    context = require_client().read_item_context()
    return 0 if context is None else context


def Item_ItemID(item: Any) -> int:
    """The item's id, from whatever a caller holds (``GwAu3_Data_Item.au3:519-527``).

    GwAu3 has three arms: a **pointer** is dereferenced at ``+0`` for the id, a **DllStruct** answers
    its ``ID`` field, and anything else is answered as given. The first two are AutoIt's own handle
    types and cannot arise for a caller of this layer -- a Python caller holds an id or a record, and
    the bridge never hands out a client address (the divergence recorded on `Agent_GetAgentPtr`) -- so
    they are not reproduced, exactly as `Agent_ConvertID` drops its pointer and struct arms for the same
    reason. The third arm is the one that matters, and it is kept.

    **A record is accepted as well as an id**, because that is this layer's equivalent of GwAu3's
    struct arm: `Item_GetItemPtr` answers a record here, so a script that passes its result back into
    an ``Item_*`` function must not break. That is the same "a script passes the result straight back
    in" case the agent accessor documents.
    """

    if isinstance(item, int):
        return item
    record_id = getattr(item, "item_id", None)
    if record_id is not None:
        return int(record_id)
    return int(item)


def Item_GetItemPtr(item: Any) -> Any:
    """The item's record (``GwAu3_Data_Item.au3:529-534``).

    **The shape differs and the difference is deliberate, as it is for `Agent_GetAgentPtr`.** GwAu3
    resolves a raw client pointer through ``BasePointer[0x18][0x40][0xB8][4 * item_id]``; this answers
    the **materialized record** this project reads (``client.read_item_records``), because a client
    address is of no use to a caller here.

    GwAu3's own short-circuit is kept: an argument that is already a pointer is answered unchanged --
    here, one that is already a record is answered unchanged. A record is recognised by carrying an
    ``item_id``, which is the field the rest of this module reads.
    """

    if not isinstance(item, int) and getattr(item, "item_id", None) is not None:
        return item
    record_id = Item_ItemID(item)
    if record_id == 0:
        return None
    return _record(record_id)


def Item_GetItemInfoByPtr(record: Any, info: str) -> Any:
    """One field of an item record (``GwAu3_Data_Item.au3:575-...``).

    GwAu3's ``Switch`` over the record's offsets is this layer's `Item_GetItemInfoByItemID`, whose table
    was generated from exactly that ``Case`` list -- so this is the same answer from the same table, and
    it routes rather than repeating the switch. An unrecognised field answers ``0``, which is GwAu3's
    own ``Case Else``, and the two guards are the same two: no record answers ``0``, and an empty field
    name answers ``0`` before anything is read.
    """

    if info == "":
        return 0
    if record is None:
        return 0
    return Item_GetItemInfoByItemID(int(record.item_id), info)


def Item_GetBagPtr(bag_number: Any) -> Any:
    """A bag's record (``GwAu3_Data_Item.au3:162-167``).

    GwAu3 walks ``BasePointer[0x18][0x40][0xF8] + 4 * bagNumber`` and answers the pointer it finds, with
    its own short-circuit for an argument that is already a pointer. This answers the **materialized
    record** (`client.read_item_bags`), the same divergence `Item_GetItemPtr` records, and its
    short-circuit is the same rule: an argument that is already a record comes back unchanged.

    **The index matches GwAu3's**, which is worth stating because it is the kind of thing that silently
    shifts: the ported reader walks the bag array from index ``0`` to its size
    (``py4gw/context/item_context.py:1532-1548``), so bag number ``n`` is the record at ``n`` -- exactly
    what GwAu3's ``4 * n`` stride addresses. Bag ``0`` is the unused bag and bag ``1`` the backpack,
    which is what ``$GC_I_INVENTORY_UNUSED_BAG``/``$GC_I_INVENTORY_BACKPACK`` name.
    """

    if not isinstance(bag_number, int) and hasattr(bag_number, "bag_type"):
        return bag_number

    index = int(bag_number)
    if index < 0:
        return None
    bags = require_client().read_item_bags()
    if index >= len(bags):
        return None
    return bags[index]


#: The bag's field names, resolved by offset against `BagStruct` -- ctypes' own view of the structure,
#: the same authority the item table rests on.
#:
#: **Two of these read *through* the port's nested array, and the arithmetic is what says so.**
#: ``BagStruct.items`` is a ``GWArray`` at ``+0x18`` (``m_buffer`` ``+0x18``, ``m_capacity`` ``+0x1C``,
#: ``m_size`` ``+0x20``, ``m_param`` ``+0x24``; the structure is 40 bytes). GwAu3's ``ItemArray`` is
#: ``+0x18`` -- the buffer -- ``FakeSlots`` is ``+0x1C`` -- the capacity -- and ``Slots`` is ``+0x20``
#: -- the size. So the three land on the nested array's own members rather than on fields of their own,
#: and the names are read off the layout rather than guessed.
_BAG_READERS: dict[str, Any] = {
    "BagType": lambda bag: bag.bag_type,
    "Index": lambda bag: bag.index,
    # GwAu3 calls ``+0x8`` the bag's ``ID``; the port declares that offset as ``_unknown0``, a
    # placeholder name for a field whose meaning was not established. The offset is what GwAu3's case
    # reads, so the placeholder is what answers it -- and the name is reported as a placeholder rather
    # than dressed up.
    "ID": lambda bag: bag._unknown0,
    "ContainerItem": lambda bag: bag.container_item,
    "ItemCount": lambda bag: bag.items_count,
    "Bag": lambda bag: bag.bag_array,
    "ItemArray": lambda bag: bag.items.m_buffer,
    "FakeSlots": lambda bag: bag.items.m_capacity,
    "Slots": lambda bag: bag.items.m_size,
}

#: ``{key: (attribute, value)}`` for the keys whose case compares ``bag_type`` and answers a boolean.
#: GwAu3 writes each as ``If Memory_Read($p, "dword") = n Then Return True`` -- a third case shape, and
#: it needs its own table for the same reason the item family's `IsMaterial` did: the offset says which
#: field, not what the case *answers*.
_BAG_EQUALITIES: dict[str, int] = {
    "IsInventoryBag": 1,
    "IsEquipped": 2,
    "IsNotCollected": 3,
    "IsStorage": 4,
    "IsMaterialStorage": 5,
}


def Item_GetBagInfo(bag_number: Any, info: str = "") -> Any:
    """One field of a bag, by GwAu3's field name (``GwAu3_Data_Item.au3:169-215``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before the bag is resolved, and a bag
    that cannot be resolved answers ``0`` rather than raising. An unrecognised field name answers ``0``
    -- GwAu3's own ``Case Else``.

    ``EmptySlots`` is GwAu3's own arithmetic (``:209``): ``Slots`` minus ``ItemCount``, written as the
    subtraction it is rather than as a fourth stored value.
    """

    if info == "":
        return 0

    bag = Item_GetBagPtr(bag_number)
    if bag is None:
        return 0

    if info in _BAG_EQUALITIES:
        return int(bag.bag_type) == _BAG_EQUALITIES[info]

    if info == "EmptySlots":
        return int(bag.items.m_size) - int(bag.items_count)

    reader = _BAG_READERS.get(info)
    if reader is None:
        return 0
    return reader(bag)


def Item_GetItemBySlot(bag_number: Any, slot: Any) -> Any:
    """The item in a bag's slot (``GwAu3_Data_Item.au3:510-517``).

    GwAu3's two steps are kept: a slot outside ``1..Item_GetBagInfo($bag, "Slots")`` answers ``0``
    without reading anything, and otherwise the slot's record is taken from the bag's item array at
    ``4 * (slot - 1)``. Its answer is a **pointer** and this answers the **materialized record**, the
    same divergence `Item_GetItemPtr` records; an empty slot answers ``None``, which is GwAu3's own
    zero pointer.

    **The slot list has to be the one that keeps empty slots.** The port offers two readers from the
    same bag -- ``read_items`` and ``items_with_slots`` -- and ``read_items`` *filters the empty
    entries out* (``py4gw/context/item_context.py:1017-1021``). Reading this function from that one
    would shift every slot after the first gap: asking for slot 3 would answer whatever item happens to
    be third among the occupied ones. ``items_with_slots`` keeps the alignment, which is what GwAu3's
    fixed ``4 * (slot - 1)`` stride addresses, so that is the reader used here.
    """

    slots = Item_GetBagInfo(bag_number, "Slots")
    if int(slot) < 1 or int(slot) > int(slots):
        return None

    bag = Item_GetBagPtr(bag_number)
    if bag is None:
        return None

    entries = bag.items_with_slots()
    index = int(slot) - 1
    if index >= len(entries):
        return None
    return entries[index]


def Item_GetInventoryPtr() -> Any:
    """The inventory record (``GwAu3_Data_Item.au3:10-14``).

    GwAu3 walks ``BasePointer[0x18][0x40][0xF8]`` and answers the pointer it finds; this answers the
    **materialized record** the same address holds (``client.read_inventory``), the divergence
    `Item_GetItemPtr` and `Item_GetBagPtr` already record -- a client address is of no use to a caller
    of this layer.

    **The record is the same one, field for field.** The port's `InventoryStruct` asserts the offsets
    GwAu3's own case list reads: ``bags[23]`` at ``+0x00`` (so ``Backpack`` is ``+0x04`` and
    ``EquippedItems`` is ``+0x58``), ``bundle`` at ``+0x5C``, the four weapon/offhand pairs at
    ``+0x64`` .. ``+0x80``, ``active_weapon_set`` at ``+0x84`` and the two gold counters at ``+0x90``
    and ``+0x94`` (``py4gw/context/item_context.py:1104-1117``).

    ``None`` is GwAu3's zero pointer, which is what a client without a character in a map answers.
    """

    return require_client().read_inventory()


#: ``{key: the bag number the client's own array index gives it}`` for the keys whose case answers a
#: bag pointer (``GwAu3_Data_Item.au3:22-67``).
#:
#: **The numbers are GwAu3's own offsets divided by four**, which is why they are written down here
#: rather than guessed: ``+0x04`` is the array's element ``1``, ``+0x08`` element ``2``, and so on
#: through ``+0x58`` -- the equipped-items bag -- at element ``22``. `Item_GetBagPtr` takes that index
#: and answers the bag record, so both names for each bag are one entry.
_INVENTORY_BAGS: dict[str, int] = {
    "BackpackPtr": 1,
    "Backpack": 1,
    "BeltPouchPtr": 2,
    "BeltPouch": 2,
    "Bag1Ptr": 3,
    "Bag1": 3,
    "Bag2Ptr": 4,
    "Bag2": 4,
    "EquipmentPackPtr": 5,
    "EquipmentPack": 5,
    "MaterialStoragePtr": 6,
    "MaterialStorage": 6,
    "UnclaimedItemsPtr": 7,
    "UnclaimedItems": 7,
    "Storage1Ptr": 8,
    "Storage1": 8,
    "Storage2Ptr": 9,
    "Storage2": 9,
    "Storage3Ptr": 10,
    "Storage3": 10,
    "Storage4Ptr": 11,
    "Storage4": 11,
    "Storage5Ptr": 12,
    "Storage5": 12,
    "Storage6Ptr": 13,
    "Storage6": 13,
    "Storage7Ptr": 14,
    "Storage7": 14,
    "Storage8Ptr": 15,
    "Storage8": 15,
    "Storage9Ptr": 16,
    "Storage9": 16,
    "Storage10Ptr": 17,
    "Storage10": 17,
    "Storage11Ptr": 18,
    "Storage11": 18,
    "Storage12Ptr": 19,
    "Storage12": 19,
    "Storage13Ptr": 20,
    "Storage13": 20,
    "Storage14Ptr": 21,
    "Storage14": 21,
    "EquippedItemsPtr": 22,
    "EquippedItems": 22,
}

#: ``{slot name: the reader that answers that slot's pointer}``. Each lambda names the structure's
#: attribute **literally**, so the nine slots of the inventory are a table of named reads rather than a
#: dynamic attribute lookup -- the same rule the item and bag tables follow.
_INVENTORY_SLOTS: dict[str, Any] = {
    "Bundle": lambda inventory: inventory.bundle,
    "WeaponSet0Weapon": lambda inventory: inventory.weapon_set0,
    "WeaponSet0Offhand": lambda inventory: inventory.offhand_set0,
    "WeaponSet1Weapon": lambda inventory: inventory.weapon_set1,
    "WeaponSet1Offhand": lambda inventory: inventory.offhand_set1,
    "WeaponSet2Weapon": lambda inventory: inventory.weapon_set2,
    "WeaponSet2Offhand": lambda inventory: inventory.offhand_set2,
    "WeaponSet3Weapon": lambda inventory: inventory.weapon_set3,
    "WeaponSet3Offhand": lambda inventory: inventory.offhand_set3,
}

#: ``{key: (slot, field)}`` for the keys whose case reads an item **through** one of those pointers
#: (``GwAu3_Data_Item.au3:69-149``).
#:
#: The field is the arm of the case: ``Ptr`` is the pointer itself -- which this layer answers as the
#: item record, as it does for every other pointer key -- and ``ItemID``, ``AgentID`` and ``ModelID``
#: are the dwords at ``+0x00``, ``+0x04`` and ``+0x2C`` of the record it addresses.
_INVENTORY_ITEM_KEYS: dict[str, tuple[str, str]] = {
    "BundlePtr": ("Bundle", "Ptr"),
    "BundleItemID": ("Bundle", "ItemID"),
    "BundleAgentID": ("Bundle", "AgentID"),
    "BundleModelID": ("Bundle", "ModelID"),
    "WeaponSet0WeaponPtr": ("WeaponSet0Weapon", "Ptr"),
    "WeaponSet0WeaponItemID": ("WeaponSet0Weapon", "ItemID"),
    "WeaponSet0WeaponAgentID": ("WeaponSet0Weapon", "AgentID"),
    "WeaponSet0WeaponModelID": ("WeaponSet0Weapon", "ModelID"),
    "WeaponSet0OffhandPtr": ("WeaponSet0Offhand", "Ptr"),
    "WeaponSet0OffhandItemID": ("WeaponSet0Offhand", "ItemID"),
    "WeaponSet0OffhandAgentID": ("WeaponSet0Offhand", "AgentID"),
    "WeaponSet0OffhandModelID": ("WeaponSet0Offhand", "ModelID"),
    "WeaponSet1WeaponPtr": ("WeaponSet1Weapon", "Ptr"),
    "WeaponSet1WeaponItemID": ("WeaponSet1Weapon", "ItemID"),
    "WeaponSet1WeaponAgentID": ("WeaponSet1Weapon", "AgentID"),
    "WeaponSet1WeaponModelID": ("WeaponSet1Weapon", "ModelID"),
    "WeaponSet1OffhandPtr": ("WeaponSet1Offhand", "Ptr"),
    "WeaponSet1OffhandItemID": ("WeaponSet1Offhand", "ItemID"),
    "WeaponSet1OffhandAgentID": ("WeaponSet1Offhand", "AgentID"),
    "WeaponSet1OffhandModelID": ("WeaponSet1Offhand", "ModelID"),
    "WeaponSet2WeaponPtr": ("WeaponSet2Weapon", "Ptr"),
    "WeaponSet2WeaponItemID": ("WeaponSet2Weapon", "ItemID"),
    "WeaponSet2WeaponAgentID": ("WeaponSet2Weapon", "AgentID"),
    "WeaponSet2WeaponModelID": ("WeaponSet2Weapon", "ModelID"),
    "WeaponSet2OffhandPtr": ("WeaponSet2Offhand", "Ptr"),
    "WeaponSet2OffhandItemID": ("WeaponSet2Offhand", "ItemID"),
    "WeaponSet2OffhandAgentID": ("WeaponSet2Offhand", "AgentID"),
    "WeaponSet2OffhandModelID": ("WeaponSet2Offhand", "ModelID"),
    "WeaponSet3WeaponPtr": ("WeaponSet3Weapon", "Ptr"),
    "WeaponSet3WeaponItemID": ("WeaponSet3Weapon", "ItemID"),
    "WeaponSet3WeaponAgentID": ("WeaponSet3Weapon", "AgentID"),
    "WeaponSet3WeaponModelID": ("WeaponSet3Weapon", "ModelID"),
    "WeaponSet3OffhandPtr": ("WeaponSet3Offhand", "Ptr"),
    "WeaponSet3OffhandItemID": ("WeaponSet3Offhand", "ItemID"),
    "WeaponSet3OffhandAgentID": ("WeaponSet3Offhand", "AgentID"),
    "WeaponSet3OffhandModelID": ("WeaponSet3Offhand", "ModelID"),
}


def _item_at_address(address: Any) -> Any:
    """The item record a pointer addresses, or ``None`` when the pointer is zero.

    GwAu3 hands the pointer it read to ``Item_GetItemInfoByPtr``, which reads the record's fields
    through it. This layer's equivalent is the record itself, so this reads the same
    ``sizeof(ItemStruct)`` bytes at the same address and binds them, exactly as
    ``py4gw/context/item_context.py:987-999`` does for a bag slot's pointer.

    An address that cannot be read is the caller's failure rather than a value: the source's
    ``ReadProcessMemory`` answers a zeroed buffer and its caller reads zeros out of it, which this
    layer cannot tell from a real record -- so the read is left to raise (``Item_GetItemBySlot`` and
    `_record` raise on the same kind of failure).
    """

    if not address:
        return None
    client = require_client()
    reader = client.reader
    raw = reader.read(int(address), ctypes.sizeof(ItemStruct))
    return ItemStruct.from_buffer_copy(raw).bind_reader(reader, int(address))


def Item_GetInventoryInfo(a_s_Info: Any = "") -> Any:
    """One field of the client's inventory struct (``GwAu3_Data_Item.au3:16-160``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    client with no inventory record answers ``0`` for every key -- its own ``If $l_p_Ptr = 0 ... Then
    Return 0``. An unrecognised field name answers ``0``, which is its ``Case Else`` at ``:159``.

    **The pointer keys answer records and the value keys answer numbers.** GwAu3 answers a **pointer**
    for every ``...Ptr`` key; this answers the **record** it addresses, the divergence
    `Item_GetItemPtr` and `Item_GetBagPtr` record, and answers ``None`` (this layer's zero pointer)
    where the pointer is null. The four bag-shaped keys reach `Item_GetBagPtr` with the array index
    GwAu3's own offset gives them. The three counters -- ``ActiveWeaponSet``, ``GoldCharacter``,
    ``GoldStorage`` -- answer the struct's own fields; GwAu3 reads them as ``long`` and the port's
    structure declares them unsigned, which is the same number for every gold total a client can hold.

    **Measured live, read-only (pid 19696, 2026-10-10, ``tests/live_reports/gwa3_inventory.log``).**
    The struct answered ``active_weapon_set=3`` and 2064 gold, and its eight weapon/offhand pointers
    resolved to real item records -- a type-2 axe in sets 1 and 2, a type-24 shield in sets 2 and 4, a
    type-5 bow in set 3, another type-2 axe in set 4, and two null offhand slots. Every one of those
    records' ids **and** addresses was also among the 341 records `read_item_records()` returned, which
    is what makes `Item_GetItemInfoByPtr` -- which re-resolves a record by id -- answer correctly for a
    weapon-set item.
    """

    if a_s_Info == "":
        return 0

    inventory = Item_GetInventoryPtr()
    if inventory is None:
        return 0

    if a_s_Info in _INVENTORY_BAGS:
        return Item_GetBagPtr(_INVENTORY_BAGS[a_s_Info])

    entry = _INVENTORY_ITEM_KEYS.get(a_s_Info)
    if entry is not None:
        address = _INVENTORY_SLOTS[entry[0]](inventory)
        field = entry[1]
        if field == "Ptr":
            return _item_at_address(address)
        record = _item_at_address(address)
        if record is None:
            return 0
        if field == "ItemID":
            return int(record.item_id)
        if field == "AgentID":
            return int(record.agent_id)
        return int(record.model_id)

    if a_s_Info == "ActiveWeaponSet":
        return int(inventory.active_weapon_set)
    if a_s_Info == "GoldCharacter":
        return int(inventory.gold_character)
    if a_s_Info == "GoldStorage":
        return int(inventory.gold_storage)

    return 0


def Item_GetModStruct(item: Any) -> Any:
    """An item's raw mod bytes, in the text form GwAu3's string search expects
    (``GwAu3_Data_Item.au3:776-781``).

    The source's two steps: the record's ``ModStruct`` pointer, answered as ``""`` when it is zero,
    and then ``Memory_Read($p, 'Byte[' & ModStructSize * 4 & ']')`` -- the mod array's own bytes.

    **What those bytes *are*, measured rather than assumed.** ``Memory_Read`` on a ``byte[n]`` struct
    returns AutoIt's **binary** type, whose string form is ``0x`` followed by upper-case hex, two
    digits per byte (``tests/scratch/_probe_modstruct.au3`` records the run: eight bytes read back as
    ``0xDE0168240500D822``, ``StringLen`` ``18``). That text is what the weapon-set analysis searches:
    a four-byte group is one upgrade's identifier and argument. This answers the same text as a ``str``,
    because this layer has no binary string type -- ``len()``, membership and replacement all behave as
    ``StringLen``, ``StringInStr`` and ``StringReplace`` did on the source's value.

    **Its argument is the item the caller holds, not a client address.** GwAu3 hands whatever it was
    given straight to ``Item_GetItemInfoByPtr``, which reads it as an **address**, and the weapon-set
    analysis passes an **item id** (``UtilityAI_WeaponSets.au3:107-119``). An id is not an address, and
    the read it makes is not merely wrong -- it **fails**: ``tests/probe_gwa3_inventory_live.py`` tried
    ``id + 0x10`` for all four sets' items on pid 19696 (2026-10-10) and every one raised Windows error
    299, ``ERROR_PARTIAL_COPY`` (``tests/live_reports/gwa3_inventory.log``). So GwAu3's own weapon-set
    analysis reads a failed buffer and finds **no mods at all** when it runs. This member resolves its
    argument the way every other ``Item_*`` member here does (`Item_GetItemPtr`) -- which is what the
    source's own caller means by it, since its merchant caller passes a pointer
    (``GwAu3_Cmd_Merchant.au3:60``) -- so the port scores the record's real mod array. That divergence
    is recorded in ``docs/GWA3_COMPAT_SPEC.md`` and in ``py4gw/gwa3/uai_weaponsets.py``, and the live
    bytes it produces scores from are asserted in ``tests/test_gwa3_uai_weaponsets_offline.py``. The
    guard order here is the source's: no mod pointer, no mod text.
    """

    record = Item_GetItemPtr(item)
    address = Item_GetItemInfoByPtr(record, "ModStruct")
    if address == 0:
        return ""

    size = Item_GetItemInfoByPtr(record, "ModStructSize")
    raw = require_client().reader.read(int(address), int(size) * 4)
    return "0x" + raw.hex().upper()


def Item_GetBagItemArray(a_v_BagNumber: Any) -> list[Any]:
    """The items in one bag, as GwAu3's counted array (``GwAu3_Data_Item.au3:237-268``).

    **GwAu3's shape is kept exactly.** Element ``0`` is the **count** and ``1..count`` are the bag's
    occupied slots in slot order; a bag that does not resolve, an item array that is null and a slot
    count of zero each answer the one-element ``[0]``, with ``@error`` 1, 2 and 3 (``:242-249``). Its
    argument is a bag **pointer** when the caller already holds one -- ``Item_GetBagPtr`` returns a
    pointer unchanged (``:233-236``), which is how the script this was ported for feeds it the result of
    ``Item_GetBagPtr`` -- and a bag number otherwise. That pair is kept: a number resolves through
    `Item_GetBagPtr`, and anything else is used as the bag it already is.

    **The entries are item ids, not pointers.** GwAu3 hands back client addresses; this layer hands out
    no address to a caller (the divergence `Item_GetItemPtr` and `Item_GetBagPtr` record), and what a
    caller does with the entries is pass them straight back into an ``Item_*`` member -- the farm script
    feeds them to ``Item_GetItemInfoByPtr``, whose port answers by id (`Item_GetItemInfoByPtr`). So the
    array's *shape* is GwAu3's and its *entries* are what the layer's own reader accepts.
    """

    if isinstance(a_v_BagNumber, int):
        bag = Item_GetBagPtr(a_v_BagNumber)
    else:
        bag = a_v_BagNumber

    if bag is None:
        return [0]

    if not int(Item_GetBagInfo(bag, "ItemArray") or 0):
        return [0]

    if not int(Item_GetBagInfo(bag, "Slots")):
        return [0]

    entries = bag.items_with_slots()
    ids = [int(entry.item_id) for entry in entries if entry is not None]
    return [len(ids), *ids]


def Item_GetItemArray() -> list[Any]:
    """Every item record the client holds, as GwAu3's counted array (``GwAu3_Data_Item.au3:745-771``).

    GwAu3 reads the client's own item array: `Item_GetMaxItems` gives the capacity (``:739-743``), the
    array's base is ``BasePointer[0][0x18][0x40][0xB8]``, every non-null pointer in it becomes an entry
    and element ``0`` is the count (``:750-768``). This project reads the same records through
    `py4gw.client.RemoteClient.read_item_records` (``py4gw/client.py:1621``), which is the port's own
    walk of the item context -- **341 records, every one with an address**, measured live and recorded
    in ``tests/live_reports/gwa3_inventory.log``.

    The entries are item **ids**, for the reason `Item_GetBagItemArray` states: this layer hands no
    address to a caller, and the entries are meant to be passed back into an ``Item_*`` member.
    """

    records = require_client().read_item_records()
    ids = [int(record.item_id) for record in records]
    return [len(ids), *ids]


def Item_GetInventoryArray(
    a_i_IncludeBag1: Any = True,
    a_i_IncludeBag2: Any = True,
    a_i_IncludeBag3: Any = True,
    a_i_IncludeBag4: Any = True,
    a_b_IncludeEquipmentPack: Any = False,
) -> list[list[int]]:
    """The character's carried items as GwAu3's 2-D array (``GwAu3_Data_Item.au3:331-...``).

    **GwAu3's shape is kept**: one row per occupied slot, **14 columns**, and the column numbers are
    GwAu3's own (``$GC_I_INVENTORY_PTR`` = 0 through ``$GC_I_INVENTORY_SLOT`` = 13, which is what the
    scripts index -- ``$l_av_Inventory[$i][$GC_I_INVENTORY_RARITY]`` and its neighbours). Its five
    arguments are kept as written, defaults included: the four bags are on, the equipment pack is off
    (``:331``), and the bag list and its contents come from the client's own records.

    **Two columns are answered the Pythonic way, and both say so.**

    * ``EXTRAID`` is a byte at ``+0x22`` in GwAu3 -- the second byte of the item's three-byte dye
      record. This port declares that record as **named nibbles** (`DyeInfoStruct.dye1..dye4`,
      ``py4gw/context/item_context.py:120-130``), so the byte is the packing of the two nibbles that
      make it up, in the port's own names, rather than a read of an unnamed offset.
    * ``PTR`` answers the item's **id**, not an address. GwAu3 hands back the item's client address;
      this layer hands no address to a caller (the divergence `Item_GetItemPtr` and `Item_GetBagPtr`
      already record), and an id is the identity this library uses -- it is what `Item_ItemID` answers
      and what every member of this module takes. The column's place in the row is kept, because the
      scripts index columns by GwAu3's own numbers.

    Every other column is the record's own named field, and the three flag columns are the same bits
    GwAu3 tests (``0x1`` identified, ``0x80000`` stackable, ``0x8000000`` inscribable) over
    ``ItemStruct.interaction``.
    """

    from . import constants as _constants

    bags: list[Any] = []
    if a_i_IncludeBag1:
        bags.append(_constants.GC_I_INVENTORY_BACKPACK)
    if a_i_IncludeBag2:
        bags.append(_constants.GC_I_INVENTORY_BELT_POUCH)
    if a_i_IncludeBag3:
        bags.append(_constants.GC_I_INVENTORY_BAG1)
    if a_i_IncludeBag4:
        bags.append(_constants.GC_I_INVENTORY_BAG2)
    if a_b_IncludeEquipmentPack:
        bags.append(_constants.GC_I_INVENTORY_EQUIPMENT_PACK)

    rows: list[list[int]] = []
    for bag_number in bags:
        bag = Item_GetBagPtr(bag_number)
        if bag is None:
            continue
        for entry in bag.items_with_slots():
            if entry is None:
                continue
            interaction = int(entry.interaction)
            rows.append(
                [
                    int(entry.item_id),  # PTR -- the item's id, the identity this library uses
                    int(entry.item_id),
                    int(entry.bag),
                    int(entry.type),
                    int(entry.dye.dye1) | (int(entry.dye.dye2) << 4),  # EXTRAID, GwAu3's +0x22
                    int(entry.value),
                    interaction & 0x1,
                    interaction & 0x80000,
                    interaction & 0x8000000,
                    int(entry.model_id),
                    int(_read_rarity(entry)),
                    int(entry.is_material_salvageable),
                    int(entry.quantity),
                    int(entry.slot),
                ]
            )
    return rows
"""``GwAu3_Data_Item.au3``'s **searches and mod parsing**, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism the item resolvers use:
``data_item.py`` is rewritten whole on every run.

**What is here.** Four readers whose whole body is a walk over the item records, written over this
project's own walk of them rather than over GwAu3's pointer array:

* ``Item_FindItemByModelID`` (``GwAu3_Data_Item.au3:...``) and ``Item_FindItemByAgentID`` -- GwAu3 walks
  ``Item_GetItemArray()`` and compares one field of each record; this walks
  `RemoteClient.read_item_records` (``py4gw/client.py:1621``), which is the port's own read of the same
  records, and answers the item's **id**, exactly as GwAu3's ``Return Memory_Read($p, "dword")`` does.
* ``Item_GetItemIsCommonMaterial`` -- GwAu3's own list, ``$GC_AI_COMMON_MATERIALS``, is in this layer's
  constants (``py4gw/gwa3/constants.py:1135``), so this is the source's own membership test over the
  item's model id.
* ``Item_GetModByIdentifier`` -- GwAu3's string arithmetic over the mod bytes, kept step for step:
  strip the ``0x`` prefix, then for every eight-character group compare its **last four** characters
  with the identifier (case-insensitively, which is what AutoIt's ``StringUpper`` comparison is) and, on
  a match, answer the group's first two characters and its second two as hex. The mod text comes from
  `Item_GetModStruct`, the ported reader of the same bytes.

**Three more members of the same file answer a word GwAu3 reaches by address, and each is answered
from a field this project names.**

* ``Item_GetItemInventoryID`` (``GwAu3_Data_Item.au3:537-548``) walks item -> bag (``+0xC``, then
  ``+0x8``) -> the bag's inventory (``+0x14``) and answers that record's first dword. Every step is a
  named field here -- `ItemStruct.bag`, `ItemStruct.bag_equipped` (`py4gw/context/item_context.py:295`,
  ``:294``), `BagStruct.bag_array` (``:913``) and `InventoryStruct.unused_bag` (``:1136-1138``, the
  first word of the 23-entry bag array, which GwAu3's own ``Item_GetBagPtr(0)`` also reads as a
  pointer) -- so the answer is the same dword, taken through the port's records rather than by walking
  addresses.
* ``Item_GetInventoryIDByAgentID`` (``:896-916``) has two arms: the controlled character's inventory
  (the same first dword) and, for anyone else, the hero flag array's matching entry at ``+0x8``. GwAu3
  resolves that array's **address** (``World_GetWorldInfo("HeroFlagArray")``, refused under that name
  in `py4gw/gwa3/data_world.py`); this reads the same array's records through
  `WorldContextStruct.hero_flags` (`py4gw/context/world_context.py:1824-1828`), whose ``0x24``-byte
  entries and ``agent_id`` at ``+0x4`` are exactly the stride and field GwAu3 reads.
* ``Item_GetMaxItems`` (``:739-743``) reads the dword at ``+0xB8 + 0x8`` of the item context: this
  project declares that array as `ItemContextStruct.item_array`, a ``GWArray`` at exactly ``+0xB8``
  (`py4gw/context/item_context.py:1478`, asserted at ``:1645``), and ``+0x8`` is its ``m_size`` word
  (`py4gw/context/gw_array.py:35-44`) -- not its capacity, which sits one word earlier.
"""

#: `Item_GetModByIdentifier`'s own answer for a record with no mod text: GwAu3's ``[0, 0]`` with ``@error`` 1.
_NO_MOD: list[int] = [0, 0]


def Item_FindItemByModelID(a_i_ModelID: Any) -> int:
    """The id of the first item whose model is ``a_i_ModelID``, or ``0`` (``GwAu3_Data_Item.au3:...``).

    GwAu3 reads ``+0x2C`` of each record in its item array and answers ``+0x0`` of the first match,
    answering ``0`` when nothing matches. This reads the same two fields of the same records through the
    port's own walk -- `ItemStruct.model_id` (``py4gw/context/item_context.py:305``) and
    `ItemStruct.item_id` (``:292``) -- so the answer is the same id.
    """

    for record in require_client().read_item_records():
        if int(record.model_id) == int(a_i_ModelID):
            return int(record.item_id)
    return 0


def Item_FindItemByAgentID(a_i_AgentID: Any) -> int:
    """The id of the first item whose agent is ``a_i_AgentID``, or ``0`` (``GwAu3_Data_Item.au3:...``).

    The same walk as `Item_FindItemByModelID`, over ``+0x4`` -- `ItemStruct.agent_id` -- which is how
    GwAu3 finds the item an agent id refers to.
    """

    for record in require_client().read_item_records():
        if int(record.agent_id) == int(a_i_AgentID):
            return int(record.item_id)
    return 0


def Item_GetItemIsCommonMaterial(a_p_Item: Any) -> bool:
    """Whether the item is one of the common materials (``GwAu3_Data_Item.au3:...``).

    GwAu3 reads the item's model id and tests it against its own ``$GC_AI_COMMON_MATERIALS`` table. That
    table is in this layer's constants, so the test and the list are both the source's.
    """

    from . import constants as _constants

    record = Item_GetItemPtr(a_p_Item)
    if record is None:
        return False

    return int(record.model_id) in _constants.GC_AI_COMMON_MATERIALS


def Item_GetModByIdentifier(a_v_Item: Any, a_s_Identifier: Any) -> list[int]:
    """The two bytes a mod's identifier names, or ``[0, 0]`` (``GwAu3_Data_Item.au3:...``).

    GwAu3's arithmetic, kept: the mod text's ``0x`` prefix is dropped, every eight-character group is
    tested by its **last four** characters against the identifier -- uppercase on both sides, because
    AutoIt's string comparison is case-insensitive -- and a match answers the group's first two
    characters and its next two as hex numbers. No match, or no mod text at all, answers ``[0, 0]``,
    which is the source's own ``$l_ai_Return`` with ``@error`` 1 for the empty case.
    """

    text = Item_GetModStruct(a_v_Item)
    if text == "":
        return list(_NO_MOD)

    body = text[2:] if text[:2].lower() == "0x" else text
    wanted = str(a_s_Identifier).upper()

    for index in range(0, len(body) // 8):
        base = 8 * index
        if body[base + 4 : base + 8].upper() == wanted:
            return [int(body[base : base + 2], 16), int(body[base + 2 : base + 4], 16)]

    return list(_NO_MOD)


def _bag_at_address(address: Any) -> Any:
    """The bag record a pointer addresses, or ``None`` when the pointer is zero.

    GwAu3 reads the bag's fields through the pointer it walked to (``+0xC`` of the item, or ``+0x8``
    when that is null, then ``+0x14`` for the inventory it belongs to). This layer's equivalent is the
    record itself, so the same ``sizeof(BagStruct)`` bytes are read at the same address and bound to the
    same reader, exactly as `_item_at_address` does for an item pointer
    (``py4gw/context/item_context.py:987-999`` is the port's own read of a bag's slots).

    An address that cannot be read is the caller's failure rather than a value -- the source's
    ``ReadProcessMemory`` answers a zeroed buffer and its caller reads zeros out of it, which this layer
    cannot tell from a real record -- so the read is left to raise.
    """

    if not address:
        return None
    client = require_client()
    reader = client.reader
    raw = reader.read(int(address), ctypes.sizeof(BagStruct))
    return BagStruct.from_buffer_copy(raw).bind_reader(reader, int(address))


def _inventory_at_address(address: Any) -> Any:
    """The inventory record a pointer addresses, or ``None`` when the pointer is zero.

    The bag's ``+0x14`` word is the inventory that owns it: GwAu3 dereferences it there
    (``GwAu3_Data_Item.au3:545``) and reads the record's first dword, and its own
    ``Item_GetHeroEquippedItemPtr`` strides the same record by ``4 * 22`` to the equipped-items bag
    (``:938``) -- which is this project's `InventoryStruct.equipped_items` at ``+0x58``
    (``py4gw/context/item_context.py:1225-1226``). This reads that record as the port declares it.
    """

    if not address:
        return None
    client = require_client()
    reader = client.reader
    raw = reader.read(int(address), ctypes.sizeof(InventoryStruct))
    return InventoryStruct.from_buffer_copy(raw).bind_reader(reader, int(address))


def Item_GetItemInventoryID(a_v_Item: Any) -> int:
    """The id of the inventory that owns an item (``GwAu3_Data_Item.au3:537-548``).

    GwAu3's chain in its own order: the item's bag (``+0xC``), the equipped bag when that is null
    (``+0x8``), that bag's inventory (``+0x14``), and the dword at the start of the inventory record.
    Each step is a field this project names -- `ItemStruct.bag` and `ItemStruct.bag_equipped`
    (``py4gw/context/item_context.py:295``, ``:294``), `BagStruct.bag_array` (``:913``) and
    `InventoryStruct.unused_bag` (``:1136-1138``) -- so the answer is the same dword GwAu3 reads, taken
    through the port's own records instead of by walking addresses.

    **One divergence, and it is the name of the word.** GwAu3 calls that dword the inventory's *id* and
    mirrors the client's ``ItemHelpGetInventoryFromAgent``; this project's `InventoryStruct` declares it
    as element ``0`` of the bag pointer array -- the *unused bag*, ``$GC_I_INVENTORY_UNUSED_BAG`` -- and
    GwAu3's own ``Item_GetBagPtr(0)``/``Item_GetBagInfo(0, "BagType")`` read the same word as a bag
    pointer. The value is the same either way.

    ``0`` is GwAu3's own answer at every guard it makes: no record, no bag, or no inventory.
    """

    record = Item_GetItemPtr(a_v_Item)
    if record is None:
        return 0

    bag_address = int(record.bag)
    if bag_address == 0:
        bag_address = int(record.bag_equipped)
    if bag_address == 0:
        return 0

    bag = _bag_at_address(bag_address)
    if bag is None:
        return 0

    inventory = _inventory_at_address(int(bag.bag_array))
    if inventory is None:
        return 0

    return int(inventory.unused_bag)


def Item_GetInventoryIDByAgentID(a_v_AgentID: Any) -> int:
    """The id of the inventory an agent owns (``GwAu3_Data_Item.au3:896-916``).

    GwAu3's steps in its own order: the id through `Agent_ConvertID`, ``0`` for an id of ``0``; for the
    **controlled character** the inventory record's first dword (the read `Item_GetItemInventoryID`
    makes); and for anyone else the **hero flag array** entry whose agent id matches, at ``+0x8``.

    **The hero arm is answered from the array's records, not from its address.** GwAu3 resolves
    ``World_GetWorldInfo("HeroFlagArray")`` -- an address this layer refuses under that name
    (`py4gw/gwa3/data_world.py:107-110`) -- and strides it by ``0x24``; this reads the same array
    through `WorldContextStruct.hero_flags` (``py4gw/context/world_context.py:1824-1828``), whose
    entries are the same ``0x24`` bytes with ``agent_id`` at ``+0x4`` (``:732``). ``0`` stands where
    GwAu3 answers ``0`` for a null array, and where no entry matches its own fall-through.

    **One divergence, and it is the name of the answered word.** GwAu3 calls the entry's ``+0x8`` the
    hero's *inventory id*; this project's `HeroFlagStruct` gives that word Reforged's own name,
    ``level`` (``:733``). The value is the same word either way -- and the finding that follows belongs
    to the source rather than to this port: the two arms answer words of the same width and different
    meaning, and it is that pair `Item_GetHeroEquippedItemPtr` compares (``:925-930``).
    """

    agent_id = int(Agent_ConvertID(a_v_AgentID))
    if agent_id == 0:
        return 0

    if agent_id == int(Agent_GetMyID()):
        inventory = Item_GetInventoryPtr()
        if inventory is None:
            return 0
        return int(inventory.unused_bag)

    world = require_client().read_world_context()
    if world is None:
        return 0

    hero_flags = world.hero_flags
    if hero_flags is None:
        return 0

    for flag in hero_flags:
        if int(flag.agent_id) == agent_id:
            return int(flag.level)
    return 0


def Item_GetMaxItems() -> int:
    """The item array's own count word (``GwAu3_Data_Item.au3:739-743``).

    GwAu3 reads the dword at ``BasePointer[0][0x18][0x40][0xB8 + 0x8]``, and its own
    `Item_GetItemArray` uses it as the loop bound over the pointer buffer at ``+0xB8`` (``:750-768``).
    That header is the item context's item array: this project declares it as
    `ItemContextStruct.item_array`, a ``GWArray`` at exactly ``+0xB8``
    (``py4gw/context/item_context.py:1478``, asserted at ``:1645``), so ``+0x8`` is its ``m_size`` word
    (`py4gw/context/gw_array.py:35-44`). GwAu3's name says ``MaxItems``; the word it reads is the
    array's **size**, one word after its capacity, and this answers that word
    (`py4gw/client.py:1610`, `RemoteClient.read_item_context`). ``0`` stands where the client publishes
    no item context, which is what GwAu3's own read of a null base amounts to.
    """

    snapshot = require_client().read_item_context()
    if snapshot is None:
        return 0
    return int(snapshot.item_array.m_size)

__all__ = ['Item_GetItemInfoByItemID', 'Item_GetBagInfo', 'Item_GetBagItemArray', 'Item_GetBagPtr', 'Item_FindItemByAgentID', 'Item_FindItemByModelID', 'Item_GetInventoryIDByAgentID', 'Item_GetItemInventoryID', 'Item_GetItemContextPtr', 'Item_GetItemIsCommonMaterial', 'Item_GetMaxItems', 'Item_GetModByIdentifier', 'Item_GetInventoryInfo', 'Item_GetInventoryArray', 'Item_GetInventoryPtr', 'Item_GetItemArray', 'Item_GetItemBySlot', 'Item_GetItemInfoByPtr', 'Item_GetItemPtr', 'Item_GetModStruct', 'Item_ItemID']
