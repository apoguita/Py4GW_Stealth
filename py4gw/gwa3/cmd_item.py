"""GwAu3's ``Item_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Twelve of the twenty-four are routed and twelve refuse, and the line between them is one mechanism.**
GwAu3's item actions split cleanly: the ones that call the client through ``Core_SendPacket`` mostly
have a ported member that does the same thing, and the ones that go through ``Core_Enqueue`` -- GwAu3's
injected assembler stub writing into the client's command queue -- mostly do not. **One of the enqueuing
ones is routed anyway, because the effect it asks for is a client control action Reforged presses for
itself**: `Item_DropBundle` enqueues a four-byte record whose stub calls the client's own ``DropBundle``,
and Reforged releases a held bundle with ``ControlAction_DropItem`` (``routines_src/yield_src/keybinds.py:116-117``),
so the bundle is dropped by pressing that action (``py4gw/gwa3/core.py``'s `Core_PerformAction` carries the
route). The refuse pile is where a *session* lives: salvage, upgrade, mass-identify and mass-deposit are
all multi-step procedures whose state GwAu3 keeps in its own memory slots (``$g_d_Salvage``,
``$g_i_InvCanIdentifyAllResult`` and their neighbours), and reproducing the sequence is the work rather
than the capability.

**Two argument conventions are kept straight, and both are silent when crossed.**

* ``$a_v_Item`` is an item -- an id or a record -- and every routed function resolves it through
  `Item_ItemID`, which is what GwAu3's own functions do before they build their packet.
* ``Item_PickUpItem``'s argument is an **agent id**, not an item id: an item lying on the ground *is* an
  agent, and GwAu3 converts it with `Agent_ConvertID` before forging ``HEADER_ITEM_INTERACT``. The
  ported member's parameter is named ``item_id``, and what it takes is the item agent's id -- which is
  what GwAu3 passes. The name and the meaning disagree in both, identically.
"""

from __future__ import annotations

from typing import Any, NoReturn

from ..inventory import Inventory
from ..party import Party
from ..player import Player
from . import constants as _constants
from .core import Core_PerformAction
from .data_agent import Agent_ConvertID
from .data_item import (
    Item_GetBagInfo,
    Item_GetItemInfoByItemID,
    Item_GetItemPtr,
    Item_ItemID,
)

__all__ = [
    "Item_AcceptAllItems",
    "Item_ApplyUpgrade",
    "Item_CanDepositAllMaterials",
    "Item_CanIdentifyAll",
    "Item_ChangeGold",
    "Item_DepositAllMaterials",
    "Item_DepositGold",
    "Item_DestroyItem",
    "Item_DropBundle",
    "Item_DropGold",
    "Item_DropItem",
    "Item_EquipHero",
    "Item_EquipItem",
    "Item_IdentifyAll",
    "Item_IdentifyItem",
    "Item_MoveItem",
    "Item_MoveItem_",
    "Item_OpenChest",
    "Item_PickUpItem",
    "Item_SalvageItem",
    "Item_SwitchWeaponSet",
    "Item_UnequipHero",
    "Item_UseItem",
    "Item_WithdrawGold",
]

#: GwAu3's own gold caps, from the arithmetic in `Item_DepositGold`/`Item_WithdrawGold`: storage holds
#: a million and a character carries a hundred thousand (``GwAu3_Cmd_Item.au3:477``, ``:494``).
_STORAGE_CAP = 1000000
_CHARACTER_CAP = 100000

#: The rule the ``Core_Enqueue`` functions refuse by. One mechanism, nine rows.
_QUEUE_RULE = (
    "GwAu3_Cmd_Item.au3:{line} calls `Core_Enqueue`, GwAu3's injected assembler stub, which writes the "
    "record into the client's own command queue with `WriteProcessMemory` "
    "(`GwAu3_Core.au3:559-566`). This project writes into no such queue: the members of `py4gw/` call "
    "the client's own functions instead, and `docs/GWA3_ROUTE_MAP.md` records which one each effect "
    "gets."
)

#: The rule for the functions whose state lives in GwAu3's own memory slots.
_SLOT_RULE = (
    "GwAu3_Cmd_Item.au3:{line} polls {slots} -- memory GwAu3 allocated in the client for its own "
    "injected code to write its answer into. This project keeps no such slots: its calls are the "
    "client's own functions, taken from `py4gw/`'s classes, whose answers come back through the call "
    "rather than through a slot."
)


def _refuse(line: int, rule: str = _QUEUE_RULE, **fields: str) -> NoReturn:
    """Refuse one function, citing its body line and the mechanism it refuses by.

    ``NoReturn`` rather than ``None``: the function never comes back, so the callers above keep GwAu3's
    own return annotations -- `Item_CanIdentifyAll` is a ``bool`` in GwAu3 and stays one here, even
    though every path raises.
    """

    raise NotImplementedError(rule.format(line=line, **fields))


# -- routed ------------------------------------------------------------------------------------


def Item_EquipItem(item: Any) -> bool:
    """Equip an item on the controlled character (``GwAu3_Cmd_Item.au3:371-373``).

    GwAu3 forges ``HEADER_ITEM_EQUIP`` with the item id alone -- the client equips onto the character
    it is driving. The ported member takes the agent explicitly, so it is given the controlled
    character's id, which is the agent GwAu3's packet implies and never has to name.
    """

    Inventory.EquipItem(Item_ItemID(item), int(Player.GetAgentID()))
    return True


def Item_EquipHero(hero_number: Any, item: Any) -> bool:
    """Equip an item on a hero (``GwAu3_Cmd_Item.au3:376-383``).

    GwAu3's guard is kept and so is its failure shape: a hero that resolves to agent ``0`` **or** an
    item id of ``0`` answers ``False`` with ``@error`` 1 without reaching the client. The hero's party
    position resolves to an agent id exactly as GwAu3 resolves it.
    """

    hero_agent_id = int(Party.Heroes.GetHeroAgentIDByPartyPosition(int(hero_number)))
    item_id = Item_ItemID(item)
    if hero_agent_id == 0 or item_id == 0:
        return False

    Inventory.EquipItem(item_id, hero_agent_id)
    return True


def Item_UseItem(item: Any) -> bool:
    """Use an item (``GwAu3_Cmd_Item.au3:400-402``). GwAu3 forges ``HEADER_ITEM_USE``."""

    Inventory.UseItem(Item_ItemID(item))
    return True


def Item_PickUpItem(agent_id: Any) -> bool:
    """Pick up an item off the ground (``GwAu3_Cmd_Item.au3:405-407``).

    GwAu3 forges ``HEADER_ITEM_INTERACT`` with ``Agent_ConvertID($a_v_AgentID)`` and a trailing zero.
    The ported member is the client's own interaction, and it takes the **item agent's id** -- which is
    what GwAu3 converts its argument to. The two names disagree about what the argument is called and
    agree about what it is, in both.
    """

    Inventory.PickUpItem(Agent_ConvertID(agent_id))
    return True


def Item_DropItem(item: Any, amount: Any = 0) -> bool:
    """Drop an item (``GwAu3_Cmd_Item.au3:410-415``).

    GwAu3's clamp is kept exactly: an amount of ``0``, or one larger than the stack, becomes the stack's
    own quantity, read from the record's ``Quantity`` key. So ``Item_DropItem($item)`` drops the whole
    stack, which is what a caller writing no amount means.
    """

    item_id = Item_ItemID(item)
    quantity = int(Item_GetItemInfoByItemID(item_id, "Quantity"))
    if int(amount) == 0 or int(amount) > quantity:
        amount = quantity

    Inventory.DropItem(item_id, int(amount))
    return True


def Item_DestroyItem(item: Any) -> bool:
    """Destroy an item (``GwAu3_Cmd_Item.au3:425-427``). GwAu3 forges ``HEADER_ITEM_DESTROY``."""

    Inventory.DestroyItem(Item_ItemID(item))
    return True


def Item_MoveItem(item: Any, bag_number: Any, slot: Any) -> bool:
    """Move an item into a slot (``GwAu3_Cmd_Item.au3:430-432``).

    GwAu3 forges ``HEADER_ITEM_MOVE`` with the item id, the bag's **ID** -- read from the bag record,
    not the bag's number -- and the slot. The ported member takes the bag id and the slot, so the same
    two values are produced the same way: ``Item_GetBagInfo($bag, "ID")`` is the bag id.
    """

    Inventory.MoveItem(
        Item_ItemID(item),
        int(Item_GetBagInfo(bag_number, "ID")),
        int(slot),
        1,
    )
    return True


def Item_DropGold(amount: Any = 0) -> bool:
    """Drop gold on the ground (``GwAu3_Cmd_Item.au3:454-458``).

    GwAu3's clamp is kept: an amount of ``0``, or one larger than the character's purse, becomes the
    whole purse. GwAu3 reads it with ``Item_GetInventoryInfo("GoldCharacter")``; the ported member for
    that reading is `Inventory.GetGoldOnCharacter`.
    """

    held = int(Inventory.GetGoldOnCharacter())
    if int(amount) == 0 or int(amount) > held:
        amount = held

    Inventory.DropGold(int(amount))
    return True


def Item_DepositGold(amount: Any = 0) -> bool:
    """Deposit gold into storage (``GwAu3_Cmd_Item.au3:466-480``).

    GwAu3's two decisions are kept in its own order: the amount is the caller's when it fits the
    purse and the whole purse otherwise, and then it is **cut to the storage cap** -- one million. That
    second cut is the one a caller notices: depositing more than the vault can hold moves only what
    fits, rather than failing.
    """

    storage = int(Inventory.GetGoldInStorage())
    held = int(Inventory.GetGoldOnCharacter())

    if int(amount) > 0 and held >= int(amount):
        chosen = int(amount)
    else:
        chosen = held

    if storage + chosen > _STORAGE_CAP:
        chosen = _STORAGE_CAP - storage

    Inventory.DepositGold(chosen)
    return True


def Item_WithdrawGold(amount: Any = 0) -> bool:
    """Withdraw gold from storage (``GwAu3_Cmd_Item.au3:483-497``). As the deposit, with the caps
    swapped: the amount falls back to the whole vault, and the cut is to the **character's** cap of one
    hundred thousand (``:494``)."""

    storage = int(Inventory.GetGoldInStorage())
    held = int(Inventory.GetGoldOnCharacter())

    if int(amount) > 0 and storage >= int(amount):
        chosen = int(amount)
    else:
        chosen = storage

    if held + chosen > _CHARACTER_CAP:
        chosen = _CHARACTER_CAP - held

    Inventory.WithdrawGold(chosen)
    return True


# -- routed: the client's own control action, pressed the way Reforged presses it -----------------


def Item_DropBundle() -> bool:
    """Drop the bundle the player is holding -- a torch, ashes, a relic (``GwAu3_Cmd_Item.au3:417-422``).

    **GwAu3's mechanism.** Its guard reads its own command struct -- ``If DllStructGetData($g_d_DropBundle,
    1) <= 0 Then Return SetError(1, 0, False)`` (``:419``) -- and then enqueues a four-byte record
    (``Core_Enqueue($g_p_DropBundle, 4)``, ``:420``) whose stub is ``CommandDropBundle:`` → ``call
    DropBundle`` (``GwAu3_Core_Assembler.au3:2427-2428``), the client's own drop function, resolved by
    GwAu3's own byte signature. The struct's first word is that command pointer
    (``GwAu3_Core.au3:478``) -- GwAu3's own runtime, not a client record -- so this member has no
    equivalent guard and does not invent one.

    **The route is Reforged's, for the same effect.** Reforged releases a held bundle by pressing the
    client's own control action: ``Keybinds.DropBundle()`` →
    ``Keybinds.PressKeybind(ControlAction_DropItem, 75)`` (``routines_src/yield_src/keybinds.py:116-117``),
    held down and released through ``UIManager.Keydown``/``Keyup``
    (``routines_src/behaviourtrees_src/keybinds.py:101,119``). That is the press this member makes, through
    the layer's own control-action member -- ``$GC_I_CONTROL_ACTION_DROP_ITEM`` (``0xCD``) with the
    activate flag, which is what Reforged presses and what ``ControlAction_DropItem`` carries in this port
    (``py4gw/enums_src/ui_enums.py``, "drops bundle item >> flags, ashes, etc"). GwAu3's return shape is
    kept: ``True`` once the press is made, and no ``@error``, which is the value a caller can act on --
    AutoIt's ``@error`` has no twin here.
    """

    Core_PerformAction(
        _constants.GC_I_CONTROL_ACTION_DROP_ITEM, _constants.GC_I_CONTROL_TYPE_ACTIVATE
    )
    return True


def Item_SwitchWeaponSet(weapon_set: Any) -> bool:
    """Switch the character's weapon set (``GwAu3_Cmd_Item.au3:508-510``).

    GwAu3 forges ``HEADER_SWITCH_SET`` (``0x32``) with the set number and nothing else: ``Return
    Core_SendPacket(0x8, $GC_I_HEADER_SWITCH_SET, $a_i_WeaponSet)`` -- one code, one number, no guard.

    **The route is the control action Reforged presses for this effect.** ``Keybinds.ActivateWeaponSet($i)``
    presses ``ControlAction_ActivateWeaponSet1.value + (index - 1)``
    (``routines_src/yield_src/keybinds.py:110-113``) -- control actions ``0x81``-``0x84``, which are the
    same four codes GwAu3's own constants name ``$GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1..4``
    (``129``-``132``) and the same four this port's enum carries. So a set number here maps to the same
    action GwAu3's number selects, and the press is made through the layer's own control-action member.

    **Reforged's own guard is kept**, because it is that route's guard and this is the only route: a set
    outside ``1..4`` has no control action -- ``0x80`` is ``ATTACK_INTERACT``, not "set zero" -- so the
    member answers ``False`` (``routines_src/yield_src/keybinds.py:111-112``) rather than pressing a
    different action. GwAu3 sent the number through regardless; the divergence is this one answer, and it
    is recorded here rather than papered over.
    """

    if int(weapon_set) < 1 or int(weapon_set) > 4:
        return False

    # Reforged's own expression for the set-to-action mapping
    # (``routines_src/yield_src/keybinds.py:113``), over GwAu3's own first constant.
    set_to_use = _constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1 + (int(weapon_set) - 1)

    Core_PerformAction(set_to_use, _constants.GC_I_CONTROL_TYPE_ACTIVATE)
    return True


# -- refused: GwAu3's injected queue -------------------------------------------------------------


def Item_SalvageItem(item: Any, kit_type: Any = "Standard", salvage_type: Any = "Materials") -> bool:
    """**REFUSED: a salvage session runs through the injected queue and GwAu3's own session id.**

    ``GwAu3_Cmd_Item.au3:4-180`` is the longest function in the API, and it is a *session*: it refuses
    ``Standard`` kits for non-material salvage, walks bags 1..4 for the best salvage kit of five models
    (comparing each kit's remaining uses, derived from its ``Value`` by a per-model divisor), reads a
    salvage **session id** out of ``BasePointer[0x18][0x2C][0x690]``, enqueues the salvage record
    through the injected stub, sleeps on the ping between steps, and then sends a *second* packet
    chosen by the salvage type -- ``Materials``, ``Prefix``, ``Suffix`` or ``Inscription``.

    Everything it needs is now in this layer **except the session**: the bag walk is
    `Item_GetBagInfo`/`Item_GetBagPtr`/`Item_GetItemBySlot`, the kit's model and value come from
    `Item_GetItemInfoByPtr`, and `Inventory.SalvageItem`/`GetFirstSalvageKit` are the ported
    transactions. What is missing is GwAu3's mid-procedure session id and its ping-paced waits -- and
    `Other_PingSleep` refuses in this layer for want of the ping reading. Reproducing the sequence is
    the work.
    """

    _refuse(156)


def Item_ApplyUpgrade(
    target_item: Any,
    upgrade_item: Any,
    upgrade_slot: Any,
    confirm: Any = True,
    extra_wait: Any = 248,
) -> bool:
    """**REFUSED: the injected queue, with GwAu3's own confirmation timing on top.**

    ``GwAu3_Cmd_Item.au3:185-208`` guards both items and the slot (``0..2``), writes a 24-byte
    ``$GC_I_UIMSG_ITEM_APPLY_UPGRADE`` record into the client's queue, and -- when the caller wants the
    confirmation -- waits **twice** for the two server replies the client answers on its own, then sends
    ``HEADER_UPGRADE_SESSION_END``. Those waits are `Other_PingSleep` calls, which refuse here for want
    of the ping reading, so the timing that makes the confirmation work cannot be reproduced.
    """

    _refuse(199)


def Item_CanIdentifyAll(timeout: Any = 1000) -> bool:
    """**REFUSED: it writes into GwAu3's own slots and polls them.**

    ``GwAu3_Cmd_Item.au3:299-314`` writes ``0xFFFFFFFF`` into ``$g_i_InvCanIdentifyAllResult``, enqueues
    a four-byte record, and polls that slot until it changes or the timeout expires -- answering
    ``False`` with ``@error`` 2 on the timeout. The pending code and the result are both GwAu3's own
    memory, which this project does not write.
    """

    _refuse(308, _SLOT_RULE, slots="`$g_i_InvCanIdentifyAllResult`")


def Item_IdentifyAll(timeout: Any = 1000) -> bool:
    """**REFUSED: as `Item_CanIdentifyAll`, one step further on.**

    ``GwAu3_Cmd_Item.au3:317-332`` calls `Item_CanIdentifyAll` first and returns its error unchanged,
    then repeats the pending-code dance against ``$g_i_InvIdentifyAllResult`` and answers ``True``.
    """

    _refuse(326, _SLOT_RULE, slots="`$g_i_InvIdentifyAllResult`")


def Item_CanDepositAllMaterials(timeout: Any = 1000) -> bool:
    """**REFUSED: the same slot protocol as `Item_CanIdentifyAll`.**

    ``GwAu3_Cmd_Item.au3:335-350`` polls ``$g_i_InvCanDepositAllMaterialsResult`` after enqueuing.
    """

    _refuse(344, _SLOT_RULE, slots="`$g_i_InvCanDepositAllMaterialsResult`")


def Item_DepositAllMaterials(timeout: Any = 1000) -> bool:
    """**REFUSED: the same slot protocol, for the deposit.**

    ``GwAu3_Cmd_Item.au3:353-368`` polls ``$g_i_InvDepositAllMaterialsResult`` after enqueuing.
    """

    _refuse(362, _SLOT_RULE, slots="`$g_i_InvDepositAllMaterialsResult`")


def Item_MoveItem_(item: Any, bag_number: Any, slot: Any, amount: Any = 0) -> bool:
    """**REFUSED: the split-stack arm sends a packet this layer has no member for.**

    ``GwAu3_Cmd_Item.au3:435-446`` clamps the amount to the stack, then chooses: the whole stack goes
    through ``HEADER_ITEM_MOVE`` and a **partial** one through ``HEADER_ITEM_SPLIT_STACK`` with the
    amount and the destination. `Item_MoveItem` is routed because `Inventory.MoveItem` takes a quantity
    and performs the move; **the split itself has no ported member**, so routing this to the same call
    would move the whole stack where the caller asked for part of it -- a wrong quantity, reported as
    success.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:435-446 clamps the amount to the stack and then sends `HEADER_ITEM_MOVE` "
        "for the whole stack or `HEADER_ITEM_SPLIT_STACK` with the amount for a partial one. "
        "`Inventory.MoveItem(item_id, bag_id, slot, quantity)` (`py4gw/inventory.py`) is the ported "
        "move and takes a quantity, but the *split* a partial move performs has no member here. Routing "
        "both arms to the same call would move the whole stack where the caller asked for part of it."
    )


def Item_UnequipHero(
    hero_number: Any,
    equipment_slot: Any,
    bag_number: Any,
    slot: Any,
) -> bool:
    """**REFUSED: no member moves a hero's equipment back into a bag.**

    ``GwAu3_Cmd_Item.au3:386-397`` resolves the hero's agent id and the destination bag's **ID** and
    slot count, guards the equipment slot (``$GC_I_EQUIPMENT_SLOT_RIGHT_HAND`` up to but excluding
    ``$GC_I_EQUIPMENT_SLOT_NONE``) and the destination slot, then forges
    ``HEADER_ITEM_UNEQUIP_HERO`` with all four. This project has no member that unequips a hero's item
    into a bag -- `Inventory.EquipItem` equips and nothing reverses it -- so the effect has no route.
    The guards are worth keeping when it lands: they are three separate answers with three ``@error``
    values (1, 2 and 3).
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:386-397 forges `HEADER_ITEM_UNEQUIP_HERO` with the hero's agent id, the "
        "equipment slot, the destination bag id and the zero-based slot, after three guards that answer "
        "`@error` 1, 2 and 3. `py4gw/inventory.py` has no member that unequips a hero's item into a "
        "bag -- `Inventory.EquipItem` equips, and nothing reverses it -- so the effect has no route."
    )


def Item_AcceptAllItems() -> bool:
    """**REFUSED: no member accepts the unclaimed items after a mission.**

    ``GwAu3_Cmd_Item.au3:449-451`` forges ``HEADER_ITEMS_ACCEPT_UNCLAIMED`` with the id of bag **7**
    (the unclaimed-items bag), which it reads from the bag record. This project has no member that
    accepts them, so the packet's effect has no route.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:449-451 forges `HEADER_ITEMS_ACCEPT_UNCLAIMED` carrying "
        "`Item_GetBagInfo(7, \"ID\")` -- the unclaimed-items bag's id. `py4gw/inventory.py` has no "
        "member that accepts the unclaimed items after a mission, so the effect has no route. The bag "
        "id the packet needs *is* available: `Item_GetBagInfo(7, \"ID\")` is routed in "
        "`py4gw/gwa3/data_item.py`."
    )


def Item_ChangeGold(character: Any, storage: Any) -> bool:
    """**REFUSED: it sets *both* purses at once, and no ported member does.**

    ``GwAu3_Cmd_Item.au3:461-463`` forges ``HEADER_ITEM_CHANGE_GOLD`` with **both** the character's new
    total and the storage's new total, in one message. The ported `Inventory.DepositGold` and
    `WithdrawGold` each take a single amount and work the two totals out themselves -- which is why
    `Item_DepositGold` and `Item_WithdrawGold` are routed through them -- while this function's
    arguments are the *results* of that arithmetic, passed in by the caller. There is no member that
    takes both totals, and splitting one message into two calls would be two different actions.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:461-463 forges `HEADER_ITEM_CHANGE_GOLD` carrying **both** new totals -- "
        "the character's and the storage's -- in one message. `Inventory.DepositGold(amount)` and "
        "`Inventory.WithdrawGold(amount)` (`py4gw/inventory.py`) each take a single amount and compute "
        "the two totals themselves, which is the route `Item_DepositGold` and `Item_WithdrawGold` use. "
        "No member takes both totals, and calling two members where GwAu3 sent one message would be two "
        "different actions."
    )


def Item_OpenChest(with_lockpick: Any = True) -> bool:
    """**REFUSED: no member opens a chest.**

    ``GwAu3_Cmd_Item.au3:500-506`` forges ``HEADER_CHEST_OPEN`` with ``2`` when a lockpick may be used
    and ``1`` when it may not. This project has no member that opens a chest -- `Ui_OpenChest` reaches
    the same effect through GwAu3's injected queue and refuses for that reason -- so the packet's effect
    has no route.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:500-506 forges `HEADER_CHEST_OPEN` with `2` (lockpick allowed) or `1` (not "
        "allowed). No member of `py4gw/` opens a chest, so the effect has no route; the same action's "
        "other spelling, `Ui_OpenChest`, refuses for the injected-queue reason."
    )


def Item_IdentifyItem(item: Any, kit_type: Any = "Superior") -> bool:
    """**REFUSED: its kit search runs on the injected queue's terms, and its early answer is not a call.**

    ``GwAu3_Cmd_Item.au3:211-296`` answers ``True`` **without touching the client** when the item is
    already identified (``Item_GetItemInfoByItemID($item, "IsIdentified")``), then walks bags 1..4 for
    the best identification kit of three models -- scoring each by remaining uses, derived from its
    ``Value`` by a per-model divisor -- and finally enqueues the identify record through the injected
    stub. The guard is a *read* this layer can do, and the bag walk is now possible too
    (`Item_GetBagInfo`/`Item_GetBagPtr`/`Item_GetItemBySlot`); what is missing is the enqueue that
    follows it, and the kit scoring is GwAu3's own preference order (`Superior`, then the infinite kit,
    then normal) that `Inventory.GetFirstIDKit` does not reproduce -- it answers the first kit it finds.
    Using it would identify with a kit the caller did not choose.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Item.au3:211-296 answers True when `Item_GetItemInfoByItemID($item, \"IsIdentified\")` "
        "is already true, then scores the identification kits found in bags 1..4 by remaining uses "
        "(model 2989 divided by 2, 5899 by 2.5, 38620 the infinite kit) in its own preference order, "
        "then enqueues the identify record through GwAu3's injected stub. `Inventory.GetFirstIDKit` "
        "(`py4gw/inventory.py`) answers *the first kit it finds*, which is not GwAu3's preference -- and "
        "the enqueue has no route either. The bag walk it needs IS routed: `Item_GetBagPtr`, "
        "`Item_GetBagInfo` and `Item_GetItemBySlot` are in `py4gw/gwa3/data_item.py`."
    )
