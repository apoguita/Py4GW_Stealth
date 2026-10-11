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
