"""Port of Native's ``PyInventory`` module (``inventory_bindings.cpp``, 216 lines).

**Why this is a module of its own.** In both sources ``PyInventory`` *is* a module — native's embedded
binding (``inventory_bindings.cpp:157-216``) and the stub Reforged's Python imports. Three ported
modules need it (``item.py``'s two bag members, ``item_array.py`` and ``inventory.py``) and it cannot
live inside any of them: ``Inventory.py`` imports ``ItemArray``, so hosting the binding in either would
make the import a cycle. So it is ported where the sources put it — as a module — with the class names
the binding exposes.

**What the binding is.** ``Bag`` (``:19-67``) is a bag snapshot: its id and name, the container item, the
item count, the three bag-type flags, ``GetSize``, ``GetItemCount`` and ``GetItems``. ``PyInventory``
(``:70-126``) is the action surface: eighteen members, each one an action the client performs on the
game's own thread or a read of inventory state. The four module functions are ``get_bag`` (the dict
snapshot, ``:129-153``), ``get_hovered_item_id``, ``salvage`` and ``accept_salvage_window``.

**The one shape decision, and it comes from Reforged.** Native's ``Bag::GetItems`` builds ``dict``s
(``:50-66``: ``item_id``, ``slot``, ``model_id``, ``quantity``), but Reforged's Python reads
**attributes** off each element — ``item.item_id`` (``ItemArray.py:49``, ``Item.py:245,265``),
``item.slot`` (``Inventory.py:1396``, ``1459``) — and its stub declares ``List[PyItem]``
(``stubs/PyInventory.pyi:17``). Since the classes being ported here are Reforged's, ``GetItems`` answers
:class:`~py4gw.item.PyItem` objects, which carry every field native's dict carries and the rest of the
record as well. The dict shape is recorded, not reproduced: it would break the callers this port exists
to serve.

**How an action reaches the client.** Native enqueues the work onto the game thread
(``GW::game_thread::Enqueue``), which is what this port's call path already is: a catalog function
called on the client's own thread from the host. So each member calls the resolver the methods layer
uses (``item_methods.cpp``) — ``item.drop_item_func``, ``item.drop_gold_func``, ``item.change_gold_func``,
``item.destroy_item_func`` — and keeps the methods layer's own guards, limits and clamps, which are
written on each member.

**The interact guard, and the members it holds.** ``UseItem``, ``EquipItem``, ``IdentifyItem`` and
``Salvage`` run the methods layer's guard chain, ported here in the source's own order:
``CanInteractWithItem`` → ``IsStorageItem`` → ``IsStorageBag`` → ``CanAccessXunlaiChest``
(``item_methods.cpp:57-74``). ``IsStorageItem`` is the **free** function — storage only — and not the
record's ``Item::IsStorageItem``, which answers for the material storage too. ``CanInteractWithItem``'s
expression is ``item && !IsStorageItem(item) || CanAccessXunlaiChest()``, so a **null** item answers
``CanAccessXunlaiChest()``, which is what native's operator precedence does.

**One divergence, recorded on ``_can_access_xunlai_chest``.** Native takes the current map record from
``map::GetCurrentMapInfo()`` — ``Context::GetAreaInfoArray()`` indexed by ``GetMapID()`` — while this port
takes it from the instance-info record's own pointer (``GWContext.InstanceInfo().GetMapInfo()``): the same
``AreaInfo`` for the current map, through the read this port already has. The global ``AreaInfo`` array is
unported (it is what ``Map.GetUnloadedMapInfo`` raises for), so that route is that member's work item.

**What still raises.** ``OpenXunlaiWindow`` emulates a StoC ``DataWindow`` packet
(``item_methods.cpp:343-349``) and no StoC path is ported. ``AcceptSalvageWindow`` (and the module's
``accept_salvage_window``) clicks a child frame (``ui::ButtonClick(ui::GetChildFrame(...))``) and no
frame-click path is ported.
"""

from __future__ import annotations

import ctypes
import struct
from typing import Any

from .client import require_client
from .context.gw_context import GWContext
from .context.instance_info_context import InstanceType, Region
from .context.item_context import BagStruct, BagType
from .enums_src.item_enums import MAX_GOLD_CHARACTER, MAX_GOLD_STORAGE
from .game_thread.shared_block import CallForm
from .item import PyItem

#: ``ui::UIMessage::kSendInteractItem`` (``constants/ui.h:190``): what ``GW::item::PickUpItem`` sends.
_K_SEND_INTERACT_ITEM = 0x3000000F

#: ``ui::UIMessage::kPreStartSalvage`` (``constants/ui.h:96``): what ``GW::item::SalvageStart`` sends,
#: with a ``ui::packet::kPreStartSalvage`` payload (``ui.h:242-245``).
_K_PRE_START_SALVAGE = 0x10000102

#: The resolvers the actions below call (``offsets/item.json``, from ``item_patterns.cpp``).
_USE_ITEM_FUNC = "item.use_item_func"
_EQUIP_ITEM_FUNC = "item.equip_item_func"
_DROP_ITEM_FUNC = "item.drop_item_func"
_MOVE_ITEM_FUNC = "item.move_item_func"
_DROP_GOLD_FUNC = "item.drop_gold_func"
_CHANGE_GOLD_FUNC = "item.change_gold_func"
_DESTROY_ITEM_FUNC = "item.destroy_item_func"
_IDENTIFY_ITEM_FUNC = "item.identify_item_func"
_SALVAGE_START_FUNC = "item.salvage_start_func"


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet."""

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


def _context_record(client: Any) -> Any:
    """The item context's own record (``ItemContext.read()``), or ``None``.

    ``GW::item::GetItemById`` natively walks ``Context::GetItemArray()``; in this port that walk and the
    inventory relationship are both members of the context's record, which its reader hands out.
    """

    return client.item_context.read()


def _salvage_session_id(client: Any) -> int:
    """``GW::item::GetSalvageSessionId`` (``item_methods.cpp:52-55``)."""

    world = client.read_world_context()
    return 0 if world is None else int(world.salvage_session_id)


def _can_access_xunlai_chest() -> bool:
    """``GW::item::CanAccessXunlaiChest`` (``item_methods.cpp:57-62``).

    Native asks ``map::GetInstanceType()`` for ``Outpost``, and then refuses the one region the chest may
    not be reached from (``map::GetCurrentMapInfo()->region != Context::Region::Region_Presearing``).

    The instance-type read is the ported ``Map.GetInstanceType()`` and **not** ``Map.IsOutpost()``: that
    member asks ``IsMapDataLoaded()`` first, and native asks nothing of the sort here.
    """

    from .map import Map

    if Map.GetInstanceType() != InstanceType.OUTPOST:
        return False
    map_info = GWContext.InstanceInfo().GetMapInfo()
    return map_info is not None and int(map_info.region) != int(Region.Region_Presearing)


def _bag_record_at(client: Any, address: int | None) -> Any:
    """The bag record at a bag pointer (native's ``item->bag`` field), or ``None``."""

    if address is None:
        return None
    try:
        raw_bag = client.reader.read(address, ctypes.sizeof(BagStruct))
    except (OSError, ValueError):
        return None
    return BagStruct.from_buffer_copy(raw_bag).bind_reader(client.reader, address)


def _is_storage_bag(bag: Any) -> bool:
    """``GW::item::IsStorageBag`` (``item_methods.cpp:64-65``): storage, and only storage."""

    return bag is not None and int(bag.bag_type) == int(BagType.Storage)


def _is_storage_item(client: Any, item: Any) -> bool:
    """``GW::item::IsStorageItem`` (``item_methods.cpp:68-70``): ``IsStorageBag(item->bag)``.

    This is the **free** function, and it is storage only. ``Item::IsStorageItem`` on the record itself
    (``item.h:140``) is a different rule — it answers for the material storage too — and the guard below
    asks this one, exactly as native does.
    """

    return item is not None and _is_storage_bag(_bag_record_at(client, item.bag_address))


def _can_interact_with_item(client: Any, item: Any) -> bool:
    """``GW::item::CanInteractWithItem`` (``item_methods.cpp:72-74``).

    Native's expression is ``item && !IsStorageItem(item) || CanAccessXunlaiChest()``, and ``&&`` binds
    tighter than ``||``: a **null** item therefore answers ``CanAccessXunlaiChest()``. Its callers pass
    ``GetItemById(...)``'s result — null included — and this keeps that.
    """

    return (
        item is not None and not _is_storage_item(client, item)
    ) or _can_access_xunlai_chest()


def _controlled_character_id() -> int:
    """``agent::GetControlledCharacterId()`` (``agent_methods.cpp:60``), through the ported member."""

    from .player import Player

    return int(Player.GetAgentID())


def _bag_record(client: Any, bag_id: int) -> Any:
    """``GW::item::GetBag`` (``item_methods.cpp:76-81``): ``bags[bag_id]`` for a valid id only."""

    if not (int(bag_id) > 0 and int(bag_id) < 23):
        return None
    context = _context_record(client)
    if context is None:
        return None
    inventory = context.read_inventory()
    if inventory is None:
        return None
    return inventory.bag_at(int(bag_id))


def _inventory_record(client: Any) -> Any:
    """``Context::GetInventory()`` (``context_methods.cpp:273-276``): the gold and bag relationship."""

    context = _context_record(client)
    return None if context is None else context.read_inventory()


def _item_record(client: Any, item_id: int) -> Any:
    """``GW::item::GetItemById`` (``item_methods.cpp:109-112``)."""

    context = _context_record(client)
    return None if context is None else context.GetItemById(int(item_id))


def hovered_item(client: Any) -> Any:
    """``GW::item::GetHoveredItem`` (``item_methods.cpp:94-107``).

    The tooltip's ``payload`` is a ``uint32_t*`` (``ui.h:370-380``), so native's ``payload[1]`` and
    ``payload[2]`` are **words**: an item tooltip's payload is either ``{item_id, 0xff}`` eight bytes
    long or ``{item_id, item_id, 0xff}`` twelve, and in the second case the first non-zero id is the
    item. The record is then read by id, as native does.
    """

    tooltip = client.read_current_tooltip()
    if tooltip is None:
        return None
    payload = int(tooltip.payload)
    payload_len = int(tooltip.payload_len)
    if not payload:
        return None
    if payload_len == 0x8:
        first, second = struct.unpack("<II", client.reader.read(payload, 8))
        if second == 0xFF:
            return _item_record(client, first)
    if payload_len == 0xC:
        first, second, third = struct.unpack("<III", client.reader.read(payload, 12))
        if third == 0xFF:
            return _item_record(client, first if first else second)
    return None


def _salvage_start(client: Any, salvage_kit_id: int, item_id: int) -> bool:
    """``GW::item::SalvageStart`` (``item_methods.cpp:292-301``).

    Both records go through the guard — a missing one answers ``CanAccessXunlaiChest()``, which is what
    ``CanInteractWithItem`` does with a null item — then the client is told with a ``kPreStartSalvage``
    packet ``{item_id, kit_id}`` (``ui.h:242-245``), and the resolver takes the kit, the salvage session
    and the item.
    """

    if not (
        client.resolves(_SALVAGE_START_FUNC)
        and _can_interact_with_item(client, _item_record(client, salvage_kit_id))
        and _can_interact_with_item(client, _item_record(client, item_id))
    ):
        return False
    client.send_ui_message(_K_PRE_START_SALVAGE, int(item_id), int(salvage_kit_id))
    client.call_function(
        _SALVAGE_START_FUNC,
        CallForm.U32_U32_U32,
        int(salvage_kit_id),
        _salvage_session_id(client),
        int(item_id),
    )
    return True


class Bag:
    """Native ``PyInventory.Bag`` (``inventory_bindings.cpp:19-67``, bound at ``:161-173``)."""

    def __init__(self, bag_id: int, bag_name: str = "") -> None:
        self.id = int(bag_id)
        self.name = bag_name
        self.container_item = 0
        self.items_count = 0
        self.is_inventory_bag = False
        self.is_storage_bag = False
        self.is_material_storage = False
        self.GetContext()

    def _record(self) -> Any:
        """The client's bag record for this id, or ``None``."""

        return _bag_record(require_client(), self.id)

    def GetContext(self) -> None:
        """``Bag::GetContext`` (``:31-40``)."""

        from .map import Map

        if not Map.IsMapReady():
            return
        record = self._record()
        if record is None:
            return
        self.container_item = int(record.container_item)
        self.items_count = int(record.items_count)
        self.is_inventory_bag = bool(record.IsInventoryBag())
        self.is_storage_bag = bool(record.IsStorageBag())
        self.is_material_storage = bool(record.IsMaterialStorage())

    def GetSize(self) -> int:
        """``Bag::GetSize`` (``:42-46``): the array's size, not the item count."""

        from .map import Map

        if not Map.IsMapReady():
            return 0
        record = self._record()
        return 0 if record is None else int(record.items.m_size)

    def GetItemCount(self) -> int:
        """``Bag::GetItemCount`` (``:48``): the field ``GetContext`` copied, not a fresh read."""

        return self.items_count

    def GetItems(self) -> list[PyItem]:
        """``Bag::GetItems`` (``:50-66``), answering :class:`~py4gw.item.PyItem` objects.

        Native builds a ``dict`` per slot; Reforged's callers read attributes off each element and its
        stub declares ``List[PyItem]``, which is what this port serves — see the module docstring. A
        slot whose pointer is null is skipped, exactly as native skips it.
        """

        from .map import Map

        result: list[PyItem] = []
        if not Map.IsMapReady():
            return result
        record = self._record()
        if record is None:
            return result
        for slot in range(int(record.items.m_size)):
            item = record.item_at(slot)
            if item is None:
                continue
            result.append(PyItem(int(item.item_id)))
        return result


class PyInventory:
    """Native ``PyInventory.PyInventory`` (``inventory_bindings.cpp:70-126``, bound at ``:176-194``)."""

    def _client(self) -> Any:
        return require_client()

    # -- reads -------------------------------------------------------------

    def GetIsStorageOpen(self) -> bool:
        """``PyInventory::GetIsStorageOpen`` (``:76``) → ``GW::item::GetIsStorageOpen``."""

        return bool(self._client().item_context.is_storage_open)

    def GetGoldAmount(self) -> int:
        """``PyInventory::GetGoldAmount`` (``:104``) → ``GetGoldAmountOnCharacter`` (``:230-233``)."""

        inventory = _inventory_record(self._client())
        return 0 if inventory is None else int(inventory.gold_character)

    def GetGoldAmountInStorage(self) -> int:
        """``PyInventory::GetGoldAmountInStorage`` (``:105``) → ``:235-238``."""

        inventory = _inventory_record(self._client())
        return 0 if inventory is None else int(inventory.gold_storage)

    def GetHoveredItemID(self) -> int:
        """``PyInventory::GetHoveredItemID`` (``:100-103``)."""

        item = hovered_item(self._client())
        return 0 if item is None else int(item.item_id)

    # -- actions the client performs ---------------------------------------

    def PickUpItem(self, item_id: int, call_target: bool = False) -> None:
        """``PyInventory::PickUpItem`` (``:78-81``) → ``GW::item::PickUpItem`` (``:150-153``).

        The methods layer sends ``kSendInteractItem`` with a ``kInteractAgent`` packet
        ``{item->agent_id, call_target == 1}`` — the port's UI-message form carries exactly those two
        words. The binding's own guard is the item existing; a missing item enqueues nothing.
        """

        client = self._client()
        item = _item_record(client, item_id)
        if item is None:
            return
        client.send_ui_message(
            _K_SEND_INTERACT_ITEM, int(item.agent_id), 1 if call_target else 0
        )

    def DropItem(self, item_id: int, quantity: int = 1) -> None:
        """``PyInventory::DropItem`` (``:82-85``) → ``GW::item::DropItem`` (``:136-141``).

        Enqueued only when the item exists; the methods layer then calls ``g_drop_item_func`` with the
        item id and the quantity.
        """

        client = self._client()
        item = _item_record(client, item_id)
        if item is None:
            return
        if not client.resolves(_DROP_ITEM_FUNC):
            return
        client.call_function(
            _DROP_ITEM_FUNC, CallForm.U32_U32, int(item.item_id), int(quantity)
        )

    def DestroyItem(self, item_id: int) -> None:
        """``PyInventory::DestroyItem`` (``:94-96``) → ``GW::item::DestroyItem`` (``:323-325``).

        The binding enqueues for any id (no item check), and the methods layer calls the resolver with
        the id.
        """

        client = self._client()
        if not client.resolves(_DESTROY_ITEM_FUNC):
            return
        client.call_function(_DESTROY_ITEM_FUNC, CallForm.U32, int(item_id))

    def DropGold(self, amount: int) -> None:
        """``PyInventory::DropGold`` (``:108``) → ``GW::item::DropGold`` (``:240-245``)."""

        client = self._client()
        if not client.resolves(_DROP_GOLD_FUNC):
            return
        inventory = _inventory_record(client)
        character_gold = 0 if inventory is None else int(inventory.gold_character)
        if not character_gold >= int(amount):
            return
        client.call_function(_DROP_GOLD_FUNC, CallForm.U32, int(amount))

    def DepositGold(self, amount: int) -> None:
        """``PyInventory::DepositGold`` (``:106``) → ``GW::item::DepositGold`` (``:254-271``).

        The methods layer's own limits: an explicit amount is refused when it would pass the storage
        maximum (1,000,000) or when the character does not hold it; ``amount == 0`` moves as much as
        fits. The move then goes through ``ChangeGold``, which verifies the totals add up.
        """

        client = self._client()
        inventory = _inventory_record(client)
        gold_storage = 0 if inventory is None else int(inventory.gold_storage)
        gold_character = 0 if inventory is None else int(inventory.gold_character)
        will_move = 0
        if amount == 0:
            will_move = min(MAX_GOLD_STORAGE - gold_storage, gold_character)
        else:
            if gold_storage + int(amount) > MAX_GOLD_STORAGE:
                return
            if int(amount) > gold_character:
                return
            will_move = int(amount)
        gold_storage += will_move
        gold_character -= will_move
        self._change_gold(gold_character, gold_storage)

    def WithdrawGold(self, amount: int) -> None:
        """``PyInventory::WithdrawGold`` (``:107``) → ``GW::item::WithdrawGold`` (``:273-290``)."""

        client = self._client()
        inventory = _inventory_record(client)
        gold_storage = 0 if inventory is None else int(inventory.gold_storage)
        gold_character = 0 if inventory is None else int(inventory.gold_character)
        will_move = 0
        if amount == 0:
            will_move = min(gold_storage, MAX_GOLD_CHARACTER - gold_character)
        else:
            if gold_character + int(amount) > MAX_GOLD_CHARACTER:
                return
            if int(amount) > gold_storage:
                return
            will_move = int(amount)
        gold_storage -= will_move
        gold_character += will_move
        self._change_gold(gold_character, gold_storage)

    def _change_gold(self, character_gold: int, storage_gold: int) -> None:
        """``GW::item::ChangeGold`` (``:247-252``): the totals must add up, then the resolver runs."""

        client = self._client()
        if not client.resolves(_CHANGE_GOLD_FUNC):
            return
        inventory = _inventory_record(client)
        current_storage = 0 if inventory is None else int(inventory.gold_storage)
        current_character = 0 if inventory is None else int(inventory.gold_character)
        if not (current_storage + current_character) == (
            int(character_gold) + int(storage_gold)
        ):
            return
        client.call_function(
            _CHANGE_GOLD_FUNC, CallForm.U32_U32, int(character_gold), int(storage_gold)
        )

    # -- members whose guard or call form this port does not have yet -------

    def UseItem(self, item_id: int) -> None:
        """``PyInventory::UseItem`` (``:90-93``) → ``GW::item::UseItem`` (``:114-121``).

        The resolver and the item come first, then the interact guard, then one word — the item's own id.
        """

        client = self._client()
        item = _item_record(client, item_id)
        if not (client.resolves(_USE_ITEM_FUNC) and item is not None):
            return
        if not _can_interact_with_item(client, item):
            return
        client.call_function(_USE_ITEM_FUNC, CallForm.U32, int(item.item_id))

    def EquipItem(self, item_id: int, agent_id: int) -> None:
        """``PyInventory::EquipItem`` (``:86-89``) → ``GW::item::EquipItem`` (``:123-134``).

        An empty ``agent_id`` means the controlled character (``agent::GetControlledCharacterId``), and
        the call is refused when even that answers nothing.
        """

        client = self._client()
        item = _item_record(client, item_id)
        if not (item is not None and client.resolves(_EQUIP_ITEM_FUNC)):
            return
        if not _can_interact_with_item(client, item):
            return
        if not agent_id:
            agent_id = _controlled_character_id()
        if not agent_id:
            return
        client.call_function(
            _EQUIP_ITEM_FUNC, CallForm.U32_U32, int(item.item_id), int(agent_id)
        )

    def IdentifyItem(self, id_kit_id: int, item_id: int) -> None:
        """``PyInventory::IdentifyItem`` (``:97-99``) → ``GW::item::IdentifyItem`` (``:303-309``).

        The methods layer guards **both** records and then calls the resolver with the ids the caller
        passed — not with the records' own ids.
        """

        client = self._client()
        if not (
            _can_interact_with_item(client, _item_record(client, id_kit_id))
            and _can_interact_with_item(client, _item_record(client, item_id))
        ):
            return
        if not client.resolves(_IDENTIFY_ITEM_FUNC):
            return
        client.call_function(
            _IDENTIFY_ITEM_FUNC, CallForm.U32_U32, int(id_kit_id), int(item_id)
        )

    def MoveItem(self, item_id: int, bag_id: int, slot: int, quantity: int = 1) -> None:
        """``PyInventory::MoveItem`` (``:109-114``) → ``GW::item::MoveItem`` (``:155-166``).

        The binding enqueues with the item looked up first; the methods layer then takes the bag, refuses
        when the bag's array is smaller than the slot, clamps the quantity to what the item holds (and to
        all of it when the caller passed nothing positive), and calls ``g_move_item_func`` with **four**
        words — item id, quantity, the bag's index and the slot. That four-word shape is
        ``CallForm.U32_U32_U32_U32``, which exists for this call (``shared_block.py``).
        """

        client = self._client()
        item = _item_record(client, item_id)
        if item is None:
            return
        bag = _bag_record(client, bag_id)
        if bag is None or not client.resolves(_MOVE_ITEM_FUNC):
            return
        if int(bag.items.m_size) < int(slot):
            return
        moved = int(quantity)
        if moved <= 0:
            moved = int(item.quantity)
        if moved > int(item.quantity):
            moved = int(item.quantity)
        client.call_function(
            _MOVE_ITEM_FUNC,
            CallForm.U32_U32_U32_U32,
            int(item.item_id),
            moved,
            int(bag.index),
            int(slot),
        )

    def Salvage(self, salv_kit_id: int, item_id: int) -> None:
        """``PyInventory::Salvage`` (``:115-120``) → ``GW::item::SalvageStart`` (``:292-301``).

        The binding's own guard comes first — the kit classifies as a salvage kit and the item is
        salvageable — and then ``SalvageStart`` runs its two interact guards, tells the client with the
        ``kPreStartSalvage`` packet and calls the resolver.
        """

        client = self._client()
        item = _item_record(client, item_id)
        kit = _item_record(client, salv_kit_id)
        if item is None or kit is None:
            return
        if not (kit.IsSalvageKit() and item.IsSalvagable()):
            return
        _salvage_start(client, int(kit.item_id), int(item.item_id))

    def OpenXunlaiWindow(self) -> None:
        """``PyInventory::OpenXunlaiWindow`` (``:71-75``) → ``GW::item::OpenXunlaiWindow``."""

        raise _unported(
            "PyInventory.OpenXunlaiWindow",
            "a ported StoC path: the methods layer emulates a `DataWindow` packet "
            "(item_methods.cpp:343-349, GW::StoC::EmulatePacket)",
        )

    def AcceptSalvageWindow(self) -> None:
        """``PyInventory::AcceptSalvageWindow`` (``:121-125``)."""

        raise _unported(
            "PyInventory.AcceptSalvageWindow",
            "a ported frame-click path: the binding clicks child 6.0x62.6 of the frame labelled "
            "\"Game\" (inventory_bindings.cpp:121-125, ui::ButtonClick)",
        )


def get_bag(bag_id: int) -> dict[str, Any]:
    """``get_bag`` (``inventory_bindings.cpp:129-153``): the dict snapshot, key for key."""

    out: dict[str, Any] = {
        "id": int(bag_id),
        "items_count": 0,
        "container_item": 0,
        "size": 0,
        "is_inventory_bag": False,
        "is_storage_bag": False,
        "is_material_storage": False,
        "items": [],
    }
    from .map import Map

    if not Map.IsMapReady():
        return out
    client = require_client()
    record = _bag_record(client, bag_id)
    if record is None:
        return out
    out["items_count"] = int(record.items_count)
    out["container_item"] = int(record.container_item)
    out["size"] = int(record.items.m_size)
    out["is_inventory_bag"] = bool(record.IsInventoryBag())
    out["is_storage_bag"] = bool(record.IsStorageBag())
    out["is_material_storage"] = bool(record.IsMaterialStorage())
    items: list[dict[str, int]] = []
    for slot in range(int(record.items.m_size)):
        item = record.item_at(slot)
        if item is None:
            continue
        items.append(
            {
                "item_id": int(item.item_id),
                "slot": slot,
                "model_id": int(item.model_id),
                "quantity": int(item.quantity),
            }
        )
    out["items"] = items
    return out


def get_hovered_item_id() -> int:
    """``get_hovered_item_id`` (``inventory_bindings.cpp:199-202``)."""

    client = require_client()
    item = hovered_item(client)
    return 0 if item is None else int(item.item_id)


def salvage(salv_kit_id: int, item_id: int) -> None:
    """``salvage`` (``inventory_bindings.cpp:204-209`` → ``GW::item::SalvageStart``).

    The same body the class member has: both records, the binding's own two guards, then the methods
    layer's ``SalvageStart``.
    """

    client = require_client()
    item = _item_record(client, item_id)
    kit = _item_record(client, salv_kit_id)
    if item is None or kit is None:
        return
    if not (kit.IsSalvageKit() and item.IsSalvagable()):
        return
    _salvage_start(client, int(kit.item_id), int(item.item_id))


def accept_salvage_window() -> None:
    """``accept_salvage_window`` (``inventory_bindings.cpp:211-215``)."""

    raise _unported(
        "accept_salvage_window",
        "a ported frame-click path: it clicks child 6.0x62.6 of the frame labelled \"Game\" "
        "(inventory_bindings.cpp:211-215, ui::ButtonClick)",
    )
