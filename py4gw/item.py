"""Port of Reforged's ``Py4GWCoreLib/Item.py`` (827 lines) over Native's ``PyItem`` binding.

**What the module is.** Reforged's item surface: the ``Bag`` enum, the ``Item`` class — six nested
namespaces (``Mods`` 22 members, ``Rarity`` 6, ``Properties`` 21, ``Type`` 8, ``Usage`` 10, ``Dye`` 4)
and its 17 own static methods — the three module constants and the four module functions
(``party_player_agent_ids``, ``has_summoning_sickness``, ``is_active_summoning_stone_ally``,
``has_active_party_summon``). Every member of the source is here with the source's name, signature,
nesting and order.

**The binding is part of the port, not a stand-in.** Every ``Item`` member reads through
``PyItem.PyItem(item_id)``, and that is Native's binding class (``item_bindings.cpp:210-380``, bound at
``:427-486``). This port carries it as :class:`PyItem` in this module — the same answer
``py4gw/effect.py`` gives for ``PyEffects.PyEffects`` — because the class belongs where the code that
uses it lives. The one spelling difference is recorded: native reaches it as ``PyItem.PyItem`` (module
``PyItem``, class ``PyItem``) and this port as ``PyItem``, since the class is right here.

**What the binding's reads became.** ``PyItemData::GetContext`` copies the client's item record into the
binding's fields; this port fills the same fields from the same record through the ported item context,
so the derived flags come from the record's own methods — ``GetIsStackable``, ``GetRarity``, ``IsTome``,
``IsIdentificationKit`` and the rest, which the ported record carries with native's names. **The read is
two steps, and it has to be**: the client's item-context *reader* hands out its record through ``read()``,
and ``GetItemById`` is a member of that record (``ItemContextStruct``), not of the reader — a shape three
files got wrong at first and ``pyright`` caught (``PORTING_PROGRESS.md``, round 18). The gate native
makes first (``item.cpp:170-174``: ``GetIsMapLoaded() && !GetIsObserving() && instance != Loading``) is
the ported ``Map.IsMapReady()``, which is how ``dialog.py`` and ``skillbar.py`` already express that same
condition.

**The item name, and the one mechanism that differs.** Native's ``RequestName`` spawns a thread,
enqueues ``AsyncGetItemName`` — which is ``ui::AsyncDecodeStr(item->complete_name_enc, &name)``
(``item_methods.cpp:360-363``) — onto the game thread and polls it for up to 1000 ms, then stores the
UTF-8 text, ``"No Item"`` when the item is gone, or ``"Timeout"`` when the second ran out
(``item_bindings.cpp:323-352``). This port has no per-request threads and no game-thread queue of its
own, so the **same client decoder** is driven directly — the route ``Agent.GetNameByID`` already uses
(``py4gw/ui/async_decode.py``, native's ``AsyncDecodeStr``): ``RequestName`` starts the decode of the
item's encoded complete name, and ``IsItemNameReady`` advances it and stores what the client answered.
The three observable states are native's own — not ready, the name, ``"No Item"`` — and the wall-clock
``"Timeout"`` is native's own check kept as it is.

**Two source facts kept rather than tidied.** ``Item.py`` imports ``Optional``, ``Type`` and ``Rarity``
and **no member uses any of the three** (the five rarity readers resolve the nested ``Item.Rarity``;
``Type`` is shadowed by the nested ``Item.Type``); they are imported here because the source imports
them. And ``Item.Dye.GetColor``/``GetChannels`` catch bare ``Exception`` around the dye reads, which is
the source's own error handling.

``tests/test_item_offline.py`` pins the member surface against the source's AST and drives the readers
over a fixture item.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Iterable, Optional, Type

from .client import require_client
from .enums_src.game_data_enums import Attribute, DyeColor, Gender
from .enums_src.item_enums import DAMAGE_RANGES, ItemType, Rarity
from . import mods_core
from .mods_types import ModifierIdentifier as ModId

#: Native's ``g_item_name_map`` (``item_bindings.cpp:180``): the text ``RequestName`` produced for an
#: item id, and whether it is ready. ``ItemNameData`` is the source's two-field record.
_item_name_map: dict[int, list[Any]] = {}


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise is
    what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )

#: The decode slots this module has asked for, by item id: what ``RequestName`` started and
#: ``IsItemNameReady`` finishes. Native keeps no such map — its request runs on its own thread — so this
#: is the port's bookkeeping for the same three members.
_item_name_requests: dict[int, tuple[int, float]] = {}


def item_type_name(type_int: int) -> str:
    """``ItemTypeName`` (``item_bindings.cpp:71-111``): the name for an ``ItemType`` value."""

    try:
        return ItemType(int(type_int)).name
    except ValueError:
        return "Unknown"


def dye_color_name(color_int: int) -> str:
    """``DyeColorName`` (``item_bindings.cpp:124-141``): the name for a ``DyeColor`` value."""

    if int(color_int) == int(DyeColor.NoColor):
        return "None"
    try:
        return DyeColor(int(color_int)).name
    except ValueError:
        return "None"


class PyItemType:
    """Native ``PyItem.ItemTypeClass`` (``item_bindings.cpp:113-122``, bound at ``:404-409``).

    The binding's own item-type value: an int with the type's name next to it. Defaults to
    ``ItemType.Unknown``, which is the C++ member's own initialiser (``:115``).
    """

    def __init__(self, type_value: int) -> None:
        self.type_int = int(type_value)

    def ToInt(self) -> int:
        """``PyItemType::ToInt`` (``:118``)."""

        return self.type_int

    def GetName(self) -> str:
        """``PyItemType::GetName`` (``:119``) → ``ItemTypeName``."""

        return item_type_name(self.type_int)

    def __eq__(self, other: object) -> bool:
        """``PyItemType::operator==`` (``:120``)."""

        if not isinstance(other, PyItemType):
            return NotImplemented
        return self.type_int == other.type_int

    def __ne__(self, other: object) -> bool:
        """``PyItemType::operator!=`` (``:121``)."""

        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash(("PyItemType", self.type_int))


class PyDyeColor:
    """Native ``PyItem.DyeColorClass`` (``item_bindings.cpp:143-152``, bound at ``:411-416``)."""

    def __init__(self, color_value: int) -> None:
        self.color_int = int(color_value)

    def ToInt(self) -> int:
        """``PyDyeColor::ToInt`` (``:148``)."""

        return self.color_int

    def ToString(self) -> str:
        """``PyDyeColor::ToString`` (``:149``) → ``DyeColorName``."""

        return dye_color_name(self.color_int)

    def __eq__(self, other: object) -> bool:
        """``PyDyeColor::operator==`` (``:150``)."""

        if not isinstance(other, PyDyeColor):
            return NotImplemented
        return self.color_int == other.color_int

    def __ne__(self, other: object) -> bool:
        """``PyDyeColor::operator!=`` (``:151``)."""

        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash(("PyDyeColor", self.color_int))


class PyDyeInfo:
    """Native ``PyItem.DyeInfo`` (``item_bindings.cpp:154-168``, bound at ``:418-425``).

    The C++ class has two constructors: the default one the binding exposes (``py::init<>()``, ``:419``)
    and ``PyDyeInfo(const GW::Context::DyeInfo& info)`` (``:159-162``), which the binding does **not**
    expose and which ``PyItemData::GetContext`` uses internally (``:276``). Python cannot overload a
    constructor, so both are one signature here: no argument gives the default field values the binding
    hands out, and a record gives the copy the C++ constructor makes.
    """

    def __init__(self, info: Any = None) -> None:
        self.dye_tint = 0
        self.dye1 = PyDyeColor(0)
        self.dye2 = PyDyeColor(0)
        self.dye3 = PyDyeColor(0)
        self.dye4 = PyDyeColor(0)
        if info is not None:
            self.dye_tint = int(info.dye_tint)
            self.dye1 = PyDyeColor(int(info.dye1))
            self.dye2 = PyDyeColor(int(info.dye2))
            self.dye3 = PyDyeColor(int(info.dye3))
            self.dye4 = PyDyeColor(int(info.dye4))

    def ToString(self) -> str:
        """``PyDyeInfo::ToString`` (``:163-167``)."""

        return (
            f"DyeInfo {{ dye_tint: {self.dye_tint}, dye1: {self.dye1.ToString()}, "
            f"dye2: {self.dye2.ToString()}, dye3: {self.dye3.ToString()}, "
            f"dye4: {self.dye4.ToString()} }}"
        )


class PyItem:
    """Native ``PyItem.PyItem`` (``item_bindings.cpp:210-380``, bound at ``:427-486``).

    The binding's item snapshot: 48 fields, ``GetContext`` to fill them from the client's record, the
    four encoded-string accessors, ``IsItemValid``, ``GetCompositeModelIDs`` and the name trio. Read
    from this side of the process, through the ported item context.
    """

    def __init__(self, item_id: int) -> None:
        """``PyItemData::PyItemData(int id) : item_id(id) { GetContext(); }`` (``:261``)."""

        self.item_id = int(item_id)
        self.agent_id = 0
        self.agent_item_id = 0
        self.name = ""
        self.modifiers: list[Any] = []
        self.is_customized = False
        self.item_type = PyItemType(int(ItemType.Unknown))
        self.dye_info = PyDyeInfo()
        self.value = 0
        self.interaction = 0
        self.model_id = 0
        self.model_file_id = 0
        self.item_formula = 0
        self.is_material_salvageable = 0
        self.quantity = 0
        self.equipped = 0
        self.profession = 0
        self.slot = 0
        self.is_stackable = False
        self.is_inscribable = False
        self.is_material = False
        self.is_zcoin = False
        self.rarity = Rarity.White
        self.uses = 0
        self.is_id_kit = False
        self.is_salvage_kit = False
        self.is_tome = False
        self.is_lesser_kit = False
        self.is_expert_salvage_kit = False
        self.is_perfect_salvage_kit = False
        self.is_weapon = False
        self.is_armor = False
        self.is_salvageable = False
        self.is_inventory_item = False
        self.is_storage_item = False
        self.is_rare_material = False
        self.is_offered_in_trade = False
        self.is_sparkly = False
        self.is_identified = False
        self.is_prefix_upgradable = False
        self.is_suffix_upgradable = False
        self.is_usable = False
        self.is_tradable = False
        self.is_inscription = False
        self.is_rarity_blue = False
        self.is_rarity_purple = False
        self.is_rarity_green = False
        self.is_rarity_gold = False
        self.GetContext()

    def _record(self) -> Any:
        """The client's record for this item id, or ``None`` — ``GW::item::GetItemById``.

        ``GW::item::GetItemById`` is native's ``item::GetItemById``, and in this port that read lives on
        the item context's own record (``ItemContextStruct.GetItemById``), which the reader hands out.
        """

        context = require_client().item_context.read()
        return None if context is None else context.GetItemById(int(self.item_id))

    def GetContext(self) -> None:
        """``PyItemData::GetContext`` (``item_bindings.cpp:263-319``)."""

        from .map import Map

        if not Map.IsMapReady():
            return
        record = self._record()
        if record is None:
            return

        self.agent_id = int(record.agent_id)
        self.agent_item_id = int(record.item_id)
        self.modifiers = list(record.read_modifiers())
        self.is_customized = int(record.customized) != 0
        self.item_type = PyItemType(int(record.type))
        self.dye_info = PyDyeInfo(record.dye)
        self.value = int(record.value)
        self.interaction = int(record.interaction)
        self.model_id = int(record.model_id)
        self.model_file_id = int(record.model_file_id)
        self.item_formula = int(record.item_formula)
        self.is_material_salvageable = int(record.is_material_salvageable)
        self.quantity = int(record.quantity)
        self.equipped = int(record.equipped)
        self.profession = int(record.profession)
        self.slot = int(record.slot)
        self.is_stackable = bool(record.GetIsStackable())
        self.is_inscribable = bool(record.GetIsInscribable())
        self.is_material = bool(record.GetIsMaterial())
        self.is_zcoin = bool(record.GetIsZcoin())
        self.rarity = Rarity(int(record.GetRarity()))
        self.uses = int(record.GetUses())
        self.is_id_kit = bool(record.IsIdentificationKit())
        self.is_salvage_kit = bool(record.IsSalvageKit())
        self.is_tome = bool(record.IsTome())
        self.is_lesser_kit = bool(record.IsLesserKit())
        self.is_expert_salvage_kit = bool(record.IsExpertSalvageKit())
        self.is_perfect_salvage_kit = bool(record.IsPerfectSalvageKit())
        self.is_weapon = bool(record.IsWeapon())
        self.is_armor = bool(record.IsArmor())
        self.is_salvageable = bool(record.IsSalvagable())
        self.is_inventory_item = bool(record.IsInventoryItem())
        self.is_storage_item = bool(record.IsStorageItem())
        self.is_rare_material = bool(record.IsRareMaterial())
        self.is_offered_in_trade = bool(record.IsOfferedInTrade())
        self.is_sparkly = bool(record.IsSparkly())
        self.is_identified = bool(record.GetIsIdentified())
        self.is_prefix_upgradable = bool(record.IsPrefixUpgradable())
        self.is_suffix_upgradable = bool(record.IsSuffixUpgradable())
        self.is_usable = bool(record.IsUsable())
        self.is_tradable = bool(record.IsTradable())
        self.is_inscription = bool(record.IsInscription())
        self.is_rarity_blue = bool(record.IsBlue())
        self.is_rarity_purple = bool(record.IsPurple())
        self.is_rarity_green = bool(record.IsGreen())
        self.is_rarity_gold = bool(record.IsGold())

    def IsItemValid(self, item_id: int) -> bool:
        """``PyItemData::IsItemValid`` (``:321``): ``GetItemById(id) != nullptr``."""

        context = require_client().item_context.read()
        return context is not None and context.GetItemById(int(item_id)) is not None

    def _enc_bytes(self, pointer: int) -> list[int]:
        """``EncBytesFrom`` (``item_bindings.cpp:192-200``): the encoded string's bytes, terminator
        included, or nothing when there is no pointer."""

        if not pointer:
            return []
        reader = require_client().reader
        units: list[int] = []
        index = 0
        while True:
            raw = reader.read(int(pointer) + index * 2, 2)
            unit = int.from_bytes(raw, "little")
            units.append(unit)
            if unit == 0:
                break
            index += 1
        out: list[int] = []
        for unit in units:
            out.extend((unit & 0xFF, (unit >> 8) & 0xFF))
        return out

    def _enc_pointer(self, field: str) -> int:
        """The record's pointer for one of the four encoded strings, or zero."""

        record = self._record()
        return 0 if record is None else int(getattr(record, field))

    def GetInfoString(self) -> list[int]:
        """``PyItemData::GetInfoString`` (``:364-367``)."""

        return self._enc_bytes(self._enc_pointer("info_string"))

    def GetNameEnc(self) -> list[int]:
        """``PyItemData::GetNameEnc`` (``:368-371``)."""

        return self._enc_bytes(self._enc_pointer("name_enc"))

    def GetCompleteNameEnc(self) -> list[int]:
        """``PyItemData::GetCompleteNameEnc`` (``:372-375``)."""

        return self._enc_bytes(self._enc_pointer("complete_name_enc"))

    def GetSingleItemName(self) -> list[int]:
        """``PyItemData::GetSingleItemName`` (``:376-379``)."""

        return self._enc_bytes(self._enc_pointer("single_item_name"))

    def RequestName(self) -> None:
        """``PyItemData::RequestName`` (``:323-352``), with the port's decode route.

        Native clears the map entry, starts a thread that enqueues the client's own
        ``AsyncGetItemName`` onto the game thread and polls it for up to 1000 ms, then stores the text,
        ``"No Item"`` or ``"Timeout"``. This port asks the same decoder directly
        (``py4gw/ui/async_decode.py``) and keeps the same three outcomes.
        """

        if not self.item_id:
            return
        from .ui.async_decode import async_decode_str, begin_string_decode

        item_id = int(self.item_id)
        _item_name_map[item_id] = ["", False]
        if self._record() is None:
            _item_name_map[item_id] = ["No Item", True]
            return
        encoded = bytes(self.GetCompleteNameEnc())
        slot = begin_string_decode(encoded)
        if not async_decode_str(encoded, slot):
            _item_name_map[item_id] = ["No Item", True]
            return
        import time

        _item_name_requests[item_id] = (slot, time.perf_counter())

    def IsItemNameReady(self) -> bool:
        """``PyItemData::IsItemNameReady`` (``:354-357``), advanced by polling the client's answer.

        Native's thread asks whether the map entry says ready; here the poll happens where native's
        thread did it — on the caller's next look — and native's own one-second bound is kept as the
        ``"Timeout"`` outcome.
        """

        item_id = int(self.item_id)
        pending = _item_name_requests.get(item_id)
        if pending is not None:
            from .ui.async_decode import DecodeState, decode_state, decoded_text

            slot, started = pending
            state = decode_state(slot)
            if state in (DecodeState.DONE, DecodeState.FAILED):
                text, _truncated = decoded_text(slot)
                _item_name_map[item_id] = [text, True]
                del _item_name_requests[item_id]
            else:
                import time

                if (time.perf_counter() - started) * 1000.0 >= 1000:
                    _item_name_map[item_id] = ["Timeout", True]
                    del _item_name_requests[item_id]
        entry = _item_name_map.get(item_id)
        return bool(entry is not None and entry[1])

    def GetName(self) -> str:
        """``PyItemData::GetName`` (``:359-362``)."""

        entry = _item_name_map.get(int(self.item_id))
        return "" if entry is None else str(entry[0])

    @staticmethod
    def GetCompositeModelIDs(model_file_id: int) -> list[int]:
        """``GetCompositeModelIDs`` (``:438`` → ``ItemCompositeModelIDs``, ``:202-208``).

        The binding is a ``def_static`` taking the model file id, and it answers the eleven file ids the
        composite-model record carries (``context/item.h:234-237``). The ported item context resolves
        that array and answers the same list (``ItemContext.get_composite_model_ids``).
        """

        if int(model_file_id) <= 0:
            return []
        return [
            int(file_id)
            for file_id in require_client().item_context.get_composite_model_ids(
                int(model_file_id)
            )
        ]


class Bag(Enum):
    """``Bag`` (``Item.py:13-37``): the bag ids, in the source's own spelling and order."""

    NoBag = 0
    Backpack = 1
    Belt_Pouch = 2
    Bag_1 = 3
    Bag_2 = 4
    Equipment_Pack = 5
    Material_Storage = 6
    Unclaimed_Items = 7
    Storage_1 = 8
    Storage_2 = 9
    Storage_3 = 10
    Storage_4 = 11
    Storage_5 = 12
    Storage_6 = 13
    Storage_7 = 14
    Storage_8 = 15
    Storage_9 = 16
    Storage_10 = 17
    Storage_11 = 18
    Storage_12 = 19
    Storage_13 = 20
    Storage_14 = 21
    Equipped_Items = 22
    Max = 23


class Item:
    """``Item`` (``Item.py:40-689``), in the source's own nesting and order.

    Every member is the source's body: ``item_instance`` builds the binding for the id and the member
    returns what it answers, and the five nested namespaces (``Mods``, ``Rarity``, ``Properties``,
    ``Type``, ``Usage``, ``Dye``) are nested here exactly as they are nested there.
    """

    class Mods:
        """``Item.Mods`` (``Item.py:45-215``): read and filter an item's modifiers."""

        Slot = mods_core.Slot

        @staticmethod
        def GetMods(item_id) -> list:
            """``Item.Mods.GetMods`` (``Item.py:48-55``)."""

            seen: list[int] = []
            for dm in mods_core.decode_item(item_id):
                if dm.identifier not in seen:
                    seen.append(dm.identifier)
            return [ModId(i) for i in seen]

        @staticmethod
        def GetName(mod) -> str:
            """``Item.Mods.GetName`` (``Item.py:57-60``)."""

            return mods_core.effect_name(int(mod))

        @staticmethod
        def GetDescriptions(item_id) -> list:
            """``Item.Mods.GetDescriptions`` (``Item.py:62-66``)."""

            return mods_core.describe_item(item_id)

        @staticmethod
        def GetRawDump(item_id) -> list:
            """``Item.Mods.GetRawDump`` (``Item.py:68-71``)."""

            return mods_core.raw_dump(item_id)

        @staticmethod
        def GetValues(item_id, mod) -> list:
            """``Item.Mods.GetValues`` (``Item.py:73-79``)."""

            for dm in mods_core.decode_item(item_id):
                if dm.identifier == int(mod):
                    return mods_core.value_of(dm)
            return []

        @staticmethod
        def GetSubtype(item_id, mod):
            """``Item.Mods.GetSubtype`` (``Item.py:81-87``)."""

            for dm in mods_core.decode_item(item_id):
                if dm.identifier == int(mod):
                    return mods_core.subtype_of(dm)
            return None

        @staticmethod
        def GetRaw(item_id, mod):
            """``Item.Mods.GetRaw`` (``Item.py:89-95``)."""

            for dm in mods_core.decode_item(item_id):
                if dm.identifier == int(mod):
                    return (dm.arg1, dm.arg2)
            return None

        @staticmethod
        def GetUpgrades(item_id) -> list:
            """``Item.Mods.GetUpgrades`` (``Item.py:97-100``)."""

            return [(name, mods_core.Slot(slot)) for name, slot in mods_core.upgrades_on(item_id)]

        @staticmethod
        def GetKnownUpgrades() -> list:
            """``Item.Mods.GetKnownUpgrades`` (``Item.py:102-105``)."""

            return [
                (name, mods_core.Slot(slot)) for name, slot in mods_core.known_upgrades()
            ]

        @staticmethod
        def GetSlot(item_id, upgrade_name):
            """``Item.Mods.GetSlot`` (``Item.py:107-111``)."""

            slot = mods_core.slot_of_upgrade(str(upgrade_name))
            return mods_core.Slot(slot) if slot is not None else None

        @staticmethod
        def GetUpgradeInSlot(item_id, slot):
            """``Item.Mods.GetUpgradeInSlot`` (``Item.py:113-119``)."""

            for name, s in Item.Mods.GetUpgrades(item_id):
                if s == slot:
                    return name
            return None

        @staticmethod
        def HasUpgradeInSlot(item_id, slot) -> bool:
            """``Item.Mods.HasUpgradeInSlot`` (``Item.py:121-124``)."""

            return any(s == slot for _, s in Item.Mods.GetUpgrades(item_id))

        @staticmethod
        def IsMaxed(item_id, upgrade_name) -> bool:
            """``Item.Mods.IsMaxed`` (``Item.py:126-129``)."""

            return mods_core.upgrade_is_maxed(item_id, str(upgrade_name))

        @staticmethod
        def HasMod(item_id, mod, *values) -> bool:
            """``Item.Mods.HasMod`` (``Item.py:131-154``)."""

            if any(callable(value) for value in values):
                raise TypeError(
                    "Item.Mods.HasMod accepts declarative subtype and numeric threshold values only"
                )
            modid = int(mod)
            subtype_filter = None
            value_filters: list = []
            for v in values:
                if isinstance(v, IntEnum):
                    subtype_filter = v
                else:
                    value_filters.append(v)
            for dm in mods_core.decode_item(item_id):
                if dm.identifier != modid:
                    continue
                if subtype_filter is not None and mods_core.subtype_of(dm) != subtype_filter:
                    continue
                if value_filters and not Item.Mods._values_match(dm, value_filters):
                    continue
                return True
            return False

        @staticmethod
        def _values_match(dm, value_filters) -> bool:
            """``Item.Mods._values_match`` (``Item.py:156-169``)."""

            vals = mods_core.value_of(dm)
            better_low = mods_core.is_better(dm)
            for i, f in enumerate(value_filters):
                if i >= len(vals):
                    return False
                got = vals[i]
                if better_low:
                    if got > f:
                        return False
                elif got < f:
                    return False
            return True

        @staticmethod
        def HasAllMods(item_id, modlist) -> bool:
            """``Item.Mods.HasAllMods`` (``Item.py:171-180``)."""

            for entry in modlist:
                if isinstance(entry, (tuple, list)):
                    if not Item.Mods.HasMod(item_id, entry[0], *entry[1:]):
                        return False
                elif not Item.Mods.HasMod(item_id, entry):
                    return False
            return True

        @staticmethod
        def HasAnyMods(item_id, modlist) -> bool:
            """``Item.Mods.HasAnyMods`` (``Item.py:182-191``)."""

            for entry in modlist:
                if isinstance(entry, (tuple, list)):
                    if Item.Mods.HasMod(item_id, entry[0], *entry[1:]):
                        return True
                elif Item.Mods.HasMod(item_id, entry):
                    return True
            return False

        @staticmethod
        def GetModifiers(item_id):
            """``Item.Mods.GetModifiers`` (``Item.py:194-197``)."""

            return Item.item_instance(item_id).modifiers

        @staticmethod
        def GetModifierCount(item_id) -> int:
            """``Item.Mods.GetModifierCount`` (``Item.py:199-201``)."""

            return len(Item.item_instance(item_id).modifiers)

        @staticmethod
        def ModifierExists(item_id, identifier_lookup) -> bool:
            """``Item.Mods.ModifierExists`` (``Item.py:203-208``)."""

            for m in Item.item_instance(item_id).modifiers:
                if m.GetIdentifier() == identifier_lookup:
                    return True
            return False

        @staticmethod
        def GetModifierValues(item_id, identifier_lookup):
            """``Item.Mods.GetModifierValues`` (``Item.py:210-215``)."""

            for m in Item.item_instance(item_id).modifiers:
                if m.GetIdentifier() == identifier_lookup:
                    return m.GetArg(), m.GetArg1(), m.GetArg2()
            return None, None, None

    @staticmethod
    def item_instance(item_id):
        """``Item.item_instance`` (``Item.py:217-225``): the binding instance for one item id."""

        return PyItem(item_id)

    @staticmethod
    def GetAgentID(item_id):
        """``Item.GetAgentID`` (``Item.py:227-230``)."""

        return Item.item_instance(item_id).agent_id

    @staticmethod
    def GetAgentItemID(item_id):
        """``Item.GetAgentItemID`` (``Item.py:232-235``)."""

        return Item.item_instance(item_id).agent_item_id

    @staticmethod
    def GetItemIdFromModelID(model_id):
        """``Item.GetItemIdFromModelID`` (``Item.py:237-251``).

        The source walks ``[Bag.Backpack, Bag.Belt_Pouch, Bag.Bag_1, Bag.Bag_2]``, takes each bag's
        ``GetItems()`` and answers the first element whose ``model_id`` matches, or ``0``. Those elements
        are :class:`~py4gw.item.PyItem` objects — Reforged's callers read ``item.item_id`` off each, and
        the bag surface this port serves is in ``py4gw/native_src/item/py_inventory.py``, where that shape decision is
        recorded.
        """

        from .native_src.item.py_inventory import Bag as PyInventoryBag

        bags_to_check = [Bag.Backpack, Bag.Belt_Pouch, Bag.Bag_1, Bag.Bag_2]

        for bag_enum in bags_to_check:
            bag_instance = PyInventoryBag(bag_enum.value, bag_enum.name)
            for item in bag_instance.GetItems():
                pyitem_instance = PyItem(item.item_id)

                if pyitem_instance.model_id == model_id:
                    return pyitem_instance.item_id

        return 0

    @staticmethod
    def GetItemByAgentID(agent_id):
        """``Item.GetItemByAgentID`` (``Item.py:253-271``): the first bag element with that agent id."""

        from .native_src.item.py_inventory import Bag as PyInventoryBag

        bags_to_check = [Bag.Backpack, Bag.Belt_Pouch, Bag.Bag_1, Bag.Bag_2]

        for bag_enum in bags_to_check:
            bag_instance = PyInventoryBag(bag_enum.value, bag_enum.name)

            for item in bag_instance.GetItems():
                pyitem_instance = PyItem(item.item_id)

                if pyitem_instance.agent_id == agent_id:
                    return pyitem_instance

        return None

    @staticmethod
    def RequestName(item_id):
        """``Item.RequestName`` (``Item.py:273-276``)."""

        return Item.item_instance(item_id).RequestName()

    @staticmethod
    def IsNameReady(item_id):
        """``Item.IsNameReady`` (``Item.py:278-281``)."""

        return Item.item_instance(item_id).IsItemNameReady()

    @staticmethod
    def GetName(item_id):
        """``Item.GetName`` (``Item.py:283-286``)."""

        return Item.item_instance(item_id).GetName()

    @staticmethod
    def GetItemType(item_id):
        """``Item.GetItemType`` (``Item.py:288-291``)."""

        return Item.item_instance(item_id).item_type.ToInt(), Item.item_instance(item_id).item_type.GetName()

    @staticmethod
    def IsArmorType(item_id):
        """``Item.IsArmorType`` (``Item.py:293-297``)."""

        item_type_value, _ = Item.GetItemType(item_id)
        return ItemType(item_type_value).is_armor_type()

    @staticmethod
    def IsWeapon(item_id):
        """``Item.IsWeapon`` (``Item.py:299-303``)."""

        item_type_value, _ = Item.GetItemType(item_id)
        return ItemType(item_type_value).is_weapon_type()

    @staticmethod
    def GetModelID(item_id):
        """``Item.GetModelID`` (``Item.py:305-308``)."""

        return Item.item_instance(item_id).model_id

    @staticmethod
    def GetModelFileID(item_id):
        """``Item.GetModelFileID`` (``Item.py:310-313``)."""

        return Item.item_instance(item_id).model_file_id

    @staticmethod
    def GetCompositeModelIDs(model_file_id) -> list[int]:
        """``Item.GetCompositeModelIDs`` (``Item.py:315-318``)."""

        return PyItem.GetCompositeModelIDs(model_file_id) if model_file_id > 0 else []

    @staticmethod
    def GetTrueModelFileID(model_file_id, gender: Gender = Gender.Unknown) -> int:
        """``Item.GetTrueModelFileID`` (``Item.py:320-339``)."""

        from .agent import Agent
        from .player import Player

        true_id = model_file_id
        female = Agent.IsFemale(Player.GetAgentID()) if gender == Gender.Unknown else gender == Gender.Female
        file_ids = Item.GetCompositeModelIDs(model_file_id)

        if file_ids:
            true_id = file_ids[10] if len(file_ids) > 10 else 0

            if not true_id:
                true_id = file_ids[5] if female and len(file_ids) > 5 else file_ids[0]

            if not true_id:
                true_id = model_file_id

        return true_id if true_id >= 0 else 0

    @staticmethod
    def GetSlot(item_id):
        """``Item.GetSlot`` (``Item.py:341-344``)."""

        return Item.item_instance(item_id).slot

    @staticmethod
    def GetDyeColor(item_id: int) -> int:
        """``Item.GetDyeColor`` (``Item.py:346-364``)."""

        mods = Item.item_instance(item_id).modifiers

        for mod in mods:
            modColor = mod.GetArg1()

            if modColor != 0:
                return modColor

        return 0

    class Rarity:
        """``Item.Rarity`` (``Item.py:366-400``)."""

        @staticmethod
        def GetRarity(item_id) -> tuple[int, str]:
            """``Item.Rarity.GetRarity`` (``Item.py:367-370``)."""

            return Item.item_instance(item_id).rarity.value, Item.item_instance(item_id).rarity.name

        @staticmethod
        def IsWhite(item_id):
            """``Item.Rarity.IsWhite`` (``Item.py:372-376``)."""

            rarity_value, rarity_name = Item.Rarity.GetRarity(item_id)
            return rarity_name == "White"

        @staticmethod
        def IsBlue(item_id):
            """``Item.Rarity.IsBlue`` (``Item.py:378-382``)."""

            rarity_value, rarity_name = Item.Rarity.GetRarity(item_id)
            return rarity_name == "Blue"

        @staticmethod
        def IsPurple(item_id):
            """``Item.Rarity.IsPurple`` (``Item.py:384-388``)."""

            rarity_value, rarity_name = Item.Rarity.GetRarity(item_id)
            return rarity_name == "Purple"

        @staticmethod
        def IsGold(item_id):
            """``Item.Rarity.IsGold`` (``Item.py:390-394``)."""

            rarity_value, rarity_name = Item.Rarity.GetRarity(item_id)
            return rarity_name == "Gold"

        @staticmethod
        def IsGreen(item_id):
            """``Item.Rarity.IsGreen`` (``Item.py:396-400``)."""

            rarity_value, rarity_name = Item.Rarity.GetRarity(item_id)
            return rarity_name == "Green"

    class Properties:
        """``Item.Properties`` (``Item.py:402-556``)."""

        @staticmethod
        def IsCustomized(item_id):
            """``Item.Properties.IsCustomized`` (``Item.py:403-406``)."""

            return Item.item_instance(item_id).is_customized

        @staticmethod
        def GetValue(item_id):
            """``Item.Properties.GetValue`` (``Item.py:408-411``)."""

            return Item.item_instance(item_id).value

        @staticmethod
        def GetQuantity(item_id):
            """``Item.Properties.GetQuantity`` (``Item.py:413-416``)."""

            return Item.item_instance(item_id).quantity

        @staticmethod
        def IsEquipped(item_id):
            """``Item.Properties.IsEquipped`` (``Item.py:418-421``)."""

            return Item.item_instance(item_id).equipped

        @staticmethod
        def GetProfession(item_id):
            """``Item.Properties.GetProfession`` (``Item.py:423-431``)."""

            return Item.item_instance(item_id).profession

        @staticmethod
        def GetInteraction(item_id):
            """``Item.Properties.GetInteraction`` (``Item.py:433-436``)."""

            return Item.item_instance(item_id).interaction

        @staticmethod
        def GetRequirement(item_id) -> tuple[Attribute, int]:
            """``Item.Properties.GetRequirement`` (``Item.py:438-451``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            if not item_type.is_weapon_type():
                return Attribute.None_, 0

            dm = mods_core.find(item_id, ModId.AttributeRequirement)
            if dm is None:
                return Attribute.None_, 0
            attr = mods_core.subtype_of(dm)
            vals = mods_core.value_of(dm)
            return (attr if isinstance(attr, Attribute) else Attribute.None_, vals[0] if vals else 0)

        @staticmethod
        def GetDamage(item_id) -> tuple[int, int]:
            """``Item.Properties.GetDamage`` (``Item.py:453-465``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            if not item_type.is_weapon_type() and not item_type in [ItemType.Offhand, ItemType.Shield]:
                return 0, 0

            dm = mods_core.find(item_id, ModId.Damage, ModId.Damage2)
            if dm is None:
                return 0, 0
            vals = mods_core.value_of(dm)
            return (vals[0] if len(vals) > 0 else 0, vals[1] if len(vals) > 1 else 0)

        @staticmethod
        def GetArmor(item_id) -> int:
            """``Item.Properties.GetArmor`` (``Item.py:467-477``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            if not item_type.is_armor_type() and not item_type == ItemType.Shield:
                return 0

            dm = mods_core.find(item_id, ModId.Armor1, ModId.Armor2)
            if dm is None:
                return 0
            vals = mods_core.value_of(dm)
            return vals[0] if vals else 0

        @staticmethod
        def GetShieldArmor(item_id) -> tuple[int, int]:
            """``Item.Properties.GetShieldArmor`` (``Item.py:479-489``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            if item_type != ItemType.Shield:
                return 0, 0

            dm = mods_core.find(item_id, ModId.Armor1)
            if dm is None:
                return 0, 0
            return dm.arg1, dm.arg2

        @staticmethod
        def GetEnergy(item_id) -> int:
            """``Item.Properties.GetEnergy`` (``Item.py:491-501``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            if not item_type.is_armor_type() and not item_type in [ItemType.Offhand, ItemType.Staff]:
                return 0

            dm = mods_core.find(item_id, ModId.Energy, ModId.Energy2)
            if dm is None:
                return 0
            vals = mods_core.value_of(dm)
            return vals[0] if vals else 0

        @staticmethod
        def GetItemFormula(item_id):
            """``Item.Properties.GetItemFormula`` (``Item.py:503-506``)."""

            return Item.item_instance(item_id).item_formula

        @staticmethod
        def IsStackable(item_id):
            """``Item.Properties.IsStackable`` (``Item.py:508-512``)."""

            interaction = Item.Properties.GetInteraction(item_id)
            return (interaction & 0x80000) != 0

        @staticmethod
        def IsSparkly(item_id):
            """``Item.Properties.IsSparkly`` (``Item.py:514-517``)."""

            return Item.item_instance(item_id).is_sparkly

        @staticmethod
        def IsInscription(item_id):
            """``Item.Properties.IsInscription`` (``Item.py:519-522``)."""

            return Item.item_instance(item_id).is_inscription

        @staticmethod
        def IsInscribable(item_id):
            """``Item.Properties.IsInscribable`` (``Item.py:524-527``)."""

            return Item.item_instance(item_id).is_inscribable

        @staticmethod
        def IsPrefixUpgradable(item_id):
            """``Item.Properties.IsPrefixUpgradable`` (``Item.py:529-532``)."""

            return Item.item_instance(item_id).is_prefix_upgradable

        @staticmethod
        def IsSuffixUpgradable(item_id):
            """``Item.Properties.IsSuffixUpgradable`` (``Item.py:534-537``)."""

            return Item.item_instance(item_id).is_suffix_upgradable

        @staticmethod
        def IsOfferedInTrade(item_id):
            """``Item.Properties.IsOfferedInTrade`` (``Item.py:539-542``)."""

            return Item.item_instance(item_id).is_offered_in_trade

        @staticmethod
        def IsTradable(item_id):
            """``Item.Properties.IsTradable`` (``Item.py:544-547``)."""

            return Item.item_instance(item_id).is_tradable

        @staticmethod
        def IsMaxDamage(item_id: int) -> bool:
            """``Item.Properties.IsMaxDamage`` (``Item.py:549-556``)."""

            item_type = ItemType(Item.GetItemType(item_id)[0])
            _, requirement = Item.Properties.GetRequirement(item_id)
            damage_for_requirement = DAMAGE_RANGES.get(item_type, {}).get(requirement, (0, 0))
            _, weapon_max = Item.Properties.GetDamage(item_id)
            return weapon_max > 0 and weapon_max == damage_for_requirement[1]

    class Type:
        """``Item.Type`` (``Item.py:558-597``)."""

        @staticmethod
        def IsWeapon(item_id):
            """``Item.Type.IsWeapon`` (``Item.py:559-562``)."""

            return Item.item_instance(item_id).is_weapon

        @staticmethod
        def IsArmor(item_id):
            """``Item.Type.IsArmor`` (``Item.py:564-567``)."""

            return Item.item_instance(item_id).is_armor

        @staticmethod
        def IsInventoryItem(item_id):
            """``Item.Type.IsInventoryItem`` (``Item.py:569-572``)."""

            return Item.item_instance(item_id).is_inventory_item

        @staticmethod
        def IsStorageItem(item_id):
            """``Item.Type.IsStorageItem`` (``Item.py:574-577``)."""

            return Item.item_instance(item_id).is_storage_item

        @staticmethod
        def IsMaterial(item_id):
            """``Item.Type.IsMaterial`` (``Item.py:579-582``)."""

            return Item.item_instance(item_id).is_material

        @staticmethod
        def IsRareMaterial(item_id):
            """``Item.Type.IsRareMaterial`` (``Item.py:584-587``)."""

            return Item.item_instance(item_id).is_rare_material

        @staticmethod
        def IsZCoin(item_id):
            """``Item.Type.IsZCoin`` (``Item.py:589-592``)."""

            return Item.item_instance(item_id).is_zcoin

        @staticmethod
        def IsTome(item_id):
            """``Item.Type.IsTome`` (``Item.py:594-597``)."""

            return Item.item_instance(item_id).is_tome

    class Usage:
        """``Item.Usage`` (``Item.py:599-648``)."""

        @staticmethod
        def IsUsable(item_id):
            """``Item.Usage.IsUsable`` (``Item.py:600-603``)."""

            return Item.item_instance(item_id).is_usable

        @staticmethod
        def GetUses(item_id):
            """``Item.Usage.GetUses`` (``Item.py:605-608``)."""

            return Item.item_instance(item_id).uses

        @staticmethod
        def IsSalvageable(item_id):
            """``Item.Usage.IsSalvageable`` (``Item.py:610-613``)."""

            return Item.item_instance(item_id).is_salvageable

        @staticmethod
        def IsMaterialSalvageable(item_id):
            """``Item.Usage.IsMaterialSalvageable`` (``Item.py:615-618``)."""

            return Item.item_instance(item_id).is_material_salvageable

        @staticmethod
        def IsSalvageKit(item_id):
            """``Item.Usage.IsSalvageKit`` (``Item.py:620-623``)."""

            return Item.item_instance(item_id).is_salvage_kit

        @staticmethod
        def IsLesserKit(item_id):
            """``Item.Usage.IsLesserKit`` (``Item.py:625-628``)."""

            return Item.item_instance(item_id).is_lesser_kit

        @staticmethod
        def IsExpertSalvageKit(item_id):
            """``Item.Usage.IsExpertSalvageKit`` (``Item.py:630-633``)."""

            return Item.item_instance(item_id).is_expert_salvage_kit

        @staticmethod
        def IsPerfectSalvageKit(item_id):
            """``Item.Usage.IsPerfectSalvageKit`` (``Item.py:635-638``)."""

            return Item.item_instance(item_id).is_perfect_salvage_kit

        @staticmethod
        def IsIDKit(item_id):
            """``Item.Usage.IsIDKit`` (``Item.py:640-643``)."""

            return Item.item_instance(item_id).is_id_kit

        @staticmethod
        def IsIdentified(item_id):
            """``Item.Usage.IsIdentified`` (``Item.py:645-648``)."""

            return Item.item_instance(item_id).is_identified

    class Dye:
        """``Item.Dye`` (``Item.py:650-689``): an item's dye channels and tint, and dye-vial colour."""

        @staticmethod
        def GetInfo(item_id):
            """``Item.Dye.GetInfo`` (``Item.py:654-657``)."""

            return Item.item_instance(item_id).dye_info

        @staticmethod
        def GetColor(item_id: int) -> DyeColor:
            """``Item.Dye.GetColor`` (``Item.py:659-671``)."""

            try:
                primary = DyeColor.from_dye_info(Item.item_instance(item_id).dye_info)
                if primary != DyeColor.NoColor:
                    return primary
            except Exception:
                pass
            try:
                return DyeColor(Item.GetDyeColor(item_id))
            except Exception:
                return DyeColor.NoColor

        @staticmethod
        def GetChannels(item_id):
            """``Item.Dye.GetChannels`` (``Item.py:673-683``)."""

            info = Item.item_instance(item_id).dye_info

            def _dc(ch) -> DyeColor:
                try:
                    return DyeColor(ch.ToInt())
                except Exception:
                    return DyeColor.NoColor

            return (info.dye_tint, [_dc(info.dye1), _dc(info.dye2), _dc(info.dye3), _dc(info.dye4)])

        @staticmethod
        def IsColor(item_id: int, color: DyeColor) -> bool:
            """``Item.Dye.IsColor`` (``Item.py:685-689``)."""

            item_type, _ = Item.GetItemType(item_id)
            return item_type == ItemType.Dye and Item.Dye.GetColor(item_id) == color


SUMMONING_SICKNESS_EFFECT_ID = 2886

KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS = frozenset({
    513,         # Fire Imp
    1726,        # Fire Imp variant
    8028,        # Legionnaire
    9055, 9076,  # Tengu Support Flare - Warrior
    9056, 9077,  # Tengu Support Flare - Ranger
    9058, 9079,  # Tengu Support Flare - Monk
    9060, 9081,  # Tengu Support Flare - Mesmer
    9062, 9083,  # Tengu Support Flare - Ritualist
    9065, 9086,  # Tengu Support Flare - Assassin
    9067, 9088,  # Tengu Support Flare - Elementalist
    9069, 9090,  # Tengu Support Flare - Necromancer
    9264,        # Imperial Guard Reinforcement Order / Canthan Guard
})

KNOWN_SUMMONING_STONE_CREATURE_ENC_NAMES = frozenset({
    "\\x8103\\x06FE",  # Imperial Guard Reinforcement Order / Canthan Guard
})


def party_player_agent_ids() -> set[int]:
    """``party_player_agent_ids`` (``Item.py:714-739``)."""

    from .party import Party
    from .player import Player

    out: set[int] = set()
    try:
        me = int(Player.GetAgentID() or 0)
        if me > 0:
            out.add(me)
    except Exception:
        pass

    try:
        for player in Party.GetPlayers() or []:
            try:
                login_number = int(getattr(player, "login_number", 0) or 0)
                if login_number <= 0:
                    continue
                agent_id = int(Party.Players.GetAgentIDByLoginNumber(login_number) or 0)
                if agent_id > 0:
                    out.add(agent_id)
            except Exception:
                continue
    except Exception:
        pass
    return out


def has_summoning_sickness(agent_id: int | None = None) -> bool:
    """``has_summoning_sickness`` (``Item.py:742-752``)."""

    from .effect import Effects
    from .player import Player

    try:
        target_agent_id = int(agent_id or Player.GetAgentID() or 0)
        if target_agent_id <= 0:
            return False
        return bool(Effects.HasEffect(target_agent_id, SUMMONING_SICKNESS_EFFECT_ID))
    except Exception:
        return False


def is_active_summoning_stone_ally(agent_id: int, owner_ids: set[int] | None = None) -> bool:
    """``is_active_summoning_stone_ally`` (``Item.py:755-806``)."""

    from .agent import Agent

    try:
        agent_id = int(agent_id or 0)
    except Exception:
        return False
    if agent_id <= 0:
        return False

    try:
        if not Agent.IsAlive(agent_id):
            return False
    except Exception:
        return False

    try:
        model_id = int(Agent.GetModelID(agent_id) or 0)
        if model_id in KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS:
            return True
    except Exception:
        pass

    try:
        encoded_name = Agent.GetEncNameStrByID(agent_id, literal=True)
        if encoded_name in KNOWN_SUMMONING_STONE_CREATURE_ENC_NAMES:
            return True
    except Exception:
        pass

    try:
        if Agent.IsSpirit(agent_id) or Agent.IsMinion(agent_id):
            return False
    except Exception:
        pass

    if owner_ids is None:
        owner_ids = party_player_agent_ids()

    try:
        owner_id = int(Agent.GetOwnerID(agent_id) or 0)
    except Exception:
        owner_id = 0

    if owner_id > 0 and owner_id in owner_ids:
        try:
            if Agent.IsNPC(agent_id):
                return True
        except Exception:
            return True

    return False


def has_active_party_summon(others: Iterable[int] | None = None) -> bool:
    """``has_active_party_summon`` (``Item.py:809-826``)."""

    from .party import Party

    owner_ids = party_player_agent_ids()
    if others is None:
        try:
            others = Party.GetOthers() or []
        except Exception:
            others = []

    for other in others:
        try:
            agent_id = int(other or 0)
        except Exception:
            continue
        if is_active_summoning_stone_ally(agent_id, owner_ids=owner_ids):
            return True
    return False

