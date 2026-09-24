"""External read-only readers for the native item context and its records.

The normal inventory path follows the maintained native relationship
``ItemContext -> bags -> Bag.items -> Item``. The context reader also caches
the source-defined item-global resolver results for formulas, composite-model
records, storage state, and PvP tables. The large global item array is kept
available as an explicitly bounded optional view; it is not traversed by the
normal bag reader.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint8, c_uint16, c_uint32
from enum import IntEnum
from typing import ClassVar, Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .game_context import GameContext, GameContextStruct
from .gw_array import (
    GWArray,
    GWArrayValueView,
    GWArrayView,
    RemoteMemoryReader,
)
from .trade_context import TradeContext


_MAX_ITEM_MODIFIER_READ_BYTES = 16 * 1024 * 1024


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by item records."""


# Native aliases over the same fixed-width GWArray header. The element type
# differs in C++, but is not part of the header stored in the target process.
ItemArray = GWArray
MerchItemArray = GWArray


def _read_encoded_wide(
    reader: _memory_reader, address: int, limit: int = 256
) -> str:
    """Read one bounded UTF-16 target string through a pointer.

    Guild Wars stores item names as encoded wide strings.  This function only
    transports and decodes the target bytes; it does not pretend to implement
    the game's full encoded-text renderer.
    """

    if address < 0x10000:
        return ""
    raw = bytearray()
    for index in range(max(0, limit)):
        try:
            pair = reader.read(address + index * 2, 2)
        except (OSError, ValueError):
            break
        if pair == b"\x00\x00":
            break
        raw.extend(pair)
    return bytes(raw).decode("utf-16-le", errors="replace")


def _format_encoded_text(value: str) -> str:
    """Make printable characters visible while preserving encoded values."""

    output: list[str] = []
    for character in value:
        code_point = ord(character)
        if 32 <= code_point <= 126:
            output.append(character)
        elif character == "\n":
            output.append("\\n")
        elif character == "\t":
            output.append("\\t")
        else:
            output.append(f"\\x{code_point:04X}")
    return "".join(output)


class ItemRarity(IntEnum):
    """The native/Reforged item-rarity values."""

    white = 0
    blue = 1
    purple = 2
    gold = 3
    green = 4


_WEAPON_TYPES = frozenset({2, 5, 12, 15, 22, 24, 26, 27, 32, 35, 36})
_ARMOR_TYPES = frozenset({4, 7, 13, 16, 19})


class DyeInfoStruct(TargetStruct):
    """The native three-byte dye record."""

    _pack_ = 1
    _fields_ = [
        ("dye_tint", c_uint8),
        ("dye1", c_uint8, 4),
        ("dye2", c_uint8, 4),
        ("dye3", c_uint8, 4),
        ("dye4", c_uint8, 4),
    ]


class ItemDataStruct(TargetStruct):
    """The native 0x10-byte item-context item data record.

    This record is declared by ``GW::Context::item.h``. It intentionally lives
    in this module even though AgentArray has a distinct source record with
    the same C++ name and layout; keeping each context's declaration local
    avoids making one context depend on another.
    """

    _pack_ = 1
    _fields_ = [
        ("model_file_id", c_uint32),
        ("type", c_uint8),
        ("dye", DyeInfoStruct),
        ("value", c_uint32),
        ("interaction", c_uint32),
    ]


class MaterialCostStruct(TargetStruct):
    """The native 0x10-byte material-cost record."""

    _pack_ = 1
    _fields_ = [
        ("material", c_uint32),
        ("amount", c_uint32),
        ("h0008", c_uint32),
        ("h000c", c_uint32),
    ]


class ItemModifierStruct(TargetStruct):
    """One native four-byte ``ItemModifier`` word.

    The native item stores modifiers indirectly as an array of these words.
    The bit layout is source-defined and does not require any target-process
    code execution: the upper 16 bits identify the modifier and the lower
    bytes carry its arguments.
    """

    _pack_ = 1
    _fields_ = [("mod", c_uint32)]

    @property
    def identifier(self) -> int:
        """Return the native 16-bit modifier identifier."""

        return int(self.mod) >> 16

    @property
    def arg1(self) -> int:
        """Return the native first eight-bit argument."""

        return (int(self.mod) >> 8) & 0xFF

    @property
    def arg2(self) -> int:
        """Return the native second eight-bit argument."""

        return int(self.mod) & 0xFF

    @property
    def arg(self) -> int:
        """Return the native combined 16-bit argument."""

        return int(self.mod) & 0xFFFF

    @property
    def is_valid(self) -> bool:
        """Return whether the native modifier word is non-zero."""

        return int(self.mod) != 0

    @property
    def mod_bits(self) -> str:
        """Return the raw word in the native 32-bit display form."""

        return f"{int(self.mod):032b}"

    @property
    def identifier_bits(self) -> str:
        """Return the identifier portion as a 16-bit binary string."""

        return f"{self.identifier:016b}"

    @property
    def arg1_bits(self) -> str:
        """Return argument one as an eight-bit binary string."""

        return f"{self.arg1:08b}"

    @property
    def arg2_bits(self) -> str:
        """Return argument two as an eight-bit binary string."""

        return f"{self.arg2:08b}"

    @property
    def arg_bits(self) -> str:
        """Return the combined argument as a 16-bit binary string."""

        return f"{self.arg:016b}"

    def to_string(self) -> str:
        """Return the same diagnostic representation as native ``ToString``."""

        if not self.is_valid:
            return "No Modifier"
        return (
            f"Modifier ID: {self.identifier} ({self.identifier_bits})"
            f", Arg1: {self.arg1} ({self.arg1_bits})"
            f", Arg2: {self.arg2} ({self.arg2_bits})"
            f", Arg: {self.arg} ({self.arg_bits})"
        )

    # Keep the source spellings available to code ported from Reforged.
    def GetIdentifier(self) -> int:
        """Return :attr:`identifier` using the native method spelling."""

        return self.identifier

    def GetArg1(self) -> int:
        """Return :attr:`arg1` using the native method spelling."""

        return self.arg1

    def GetArg2(self) -> int:
        """Return :attr:`arg2` using the native method spelling."""

        return self.arg2

    def GetArg(self) -> int:
        """Return :attr:`arg` using the native method spelling."""

        return self.arg

    def IsValid(self) -> bool:
        """Return :attr:`is_valid` using the native method spelling."""

        return self.is_valid

    def GetModBits(self) -> str:
        """Return :attr:`mod_bits` using the native method spelling."""

        return self.mod_bits

    ToString = to_string


class ItemStruct(TargetStruct):
    """The native fixed-width x86 ``Item`` record (0x54 bytes).

    Pointer fields remain target-process addresses.  In particular,
    ``mod_struct`` and ``mod_struct_size`` identify a bounded, lazily-read
    array of :class:`ItemModifierStruct` values.
    """

    _pack_ = 4
    _fields_ = [
        ("item_id", c_uint32),
        ("agent_id", c_uint32),
        ("bag_equipped", c_uint32),
        ("bag", c_uint32),
        ("mod_struct", c_uint32),
        ("mod_struct_size", c_uint32),
        ("customized", c_uint32),
        ("model_file_id", c_uint32),
        ("type", c_uint8),
        ("dye", DyeInfoStruct),
        ("value", c_uint16),
        ("h0026", c_uint16),
        ("interaction", c_uint32),
        ("model_id", c_uint32),
        ("info_string", c_uint32),
        ("name_enc", c_uint32),
        ("complete_name_enc", c_uint32),
        ("single_item_name", c_uint32),
        ("h0040", c_uint32 * 2),
        ("item_formula", c_uint16),
        ("is_material_salvageable", c_uint8),
        ("h004B", c_uint8),
        ("quantity", c_uint16),
        ("equipped", c_uint8),
        ("profession", c_uint8),
        ("slot", c_uint8),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _trade_context: TradeContext | None = None

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        trade_context: TradeContext | None = None,
    ) -> ItemStruct:
        """Attach the target address and context readers for this item."""

        self._remote_reader = reader
        self._remote_address = address
        self._trade_context = trade_context
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this snapshot."""

        return self._remote_address

    @property
    def bag_address(self) -> int | None:
        """Return the owning bag address, if present."""

        address = int(self.bag)
        return address or None

    @property
    def equipped_bag_address(self) -> int | None:
        """Return the equipped-bag address, if present."""

        address = int(self.bag_equipped)
        return address or None

    @property
    def modifier_address(self) -> int | None:
        """Return the raw modifier-array address without reading it."""

        address = int(self.mod_struct)
        return address or None

    @property
    def modifier_count(self) -> int:
        """Return the native modifier count without reading the array."""

        return int(self.mod_struct_size)

    def read_modifiers(self, limit: int = 64) -> list[ItemModifierStruct]:
        """Read the item's bounded native modifier array.

        The native source trusts its in-process pointer and count. An external
        reader must additionally bound the count and stop on an unreadable or
        implausible pointer so a stale item cannot turn into an unbounded read.
        """

        if self._remote_reader is None:
            return []
        count = min(max(0, int(self.mod_struct_size)), max(0, limit), 64)
        address = self.modifier_address
        if address is None or count == 0:
            return []
        values: list[ItemModifierStruct] = []
        for index in range(count):
            try:
                raw_value = self._remote_reader.read(
                    address + index * ctypes.sizeof(ItemModifierStruct),
                    ctypes.sizeof(ItemModifierStruct),
                )
            except (OSError, ValueError):
                break
            values.append(ItemModifierStruct.from_buffer_copy(raw_value))
        return values

    @property
    def modifiers(self) -> list[ItemModifierStruct]:
        """Return the current bounded modifier snapshot."""

        return self.read_modifiers()

    def get_modifier(self, identifier: int) -> ItemModifierStruct | None:
        """Return the first modifier whose native identifier matches."""

        if self._remote_reader is None:
            return None
        address = self.modifier_address
        count = int(self.mod_struct_size)
        if address is None or count == 0:
            return None
        if address < 0x10000:
            raise ValueError(
                f"Item modifier array has an implausible address: 0x{address:08X}"
            )

        item_size = ctypes.sizeof(ItemModifierStruct)
        byte_count = count * item_size
        if byte_count > _MAX_ITEM_MODIFIER_READ_BYTES:
            raise ValueError(
                "Item modifier array exceeds the per-array read limit: "
                f"count={count}, bytes={byte_count}"
            )
        if address + byte_count > 0x1_0000_0000:
            raise ValueError(
                "Item modifier array extends beyond the 32-bit target address space: "
                f"address=0x{address:08X}, bytes={byte_count}"
            )

        raw = self._remote_reader.read(address, byte_count)
        if len(raw) != byte_count:
            raise OSError(
                "Item modifier array read returned an unexpected byte count: "
                f"address=0x{address:08X}, requested={byte_count}, received={len(raw)}"
            )
        for offset in range(0, byte_count, item_size):
            modifier = ItemModifierStruct.from_buffer_copy(raw, offset)
            if modifier.identifier == int(identifier):
                return modifier
        return None

    @property
    def uses(self) -> int:
        """Return uses using the native ``Item::GetUses`` rule."""

        modifier = self.get_modifier(0x2458)
        return modifier.arg2 if modifier is not None else int(self.quantity)

    @property
    def is_tome(self) -> bool:
        """Return the native tome classification."""

        modifier = self.get_modifier(0x2788)
        return modifier is not None and 15 < modifier.arg2 < 36

    @property
    def is_identification_kit(self) -> bool:
        """Return the native identification-kit classification."""

        modifier = self.get_modifier(0x25E8)
        return modifier is not None and modifier.arg1 == 1

    @property
    def is_lesser_kit(self) -> bool:
        """Return the native lesser-salvage-kit classification."""

        modifier = self.get_modifier(0x25E8)
        return modifier is not None and modifier.arg1 == 3

    @property
    def is_expert_salvage_kit(self) -> bool:
        """Return the native expert-salvage-kit classification."""

        modifier = self.get_modifier(0x25E8)
        return modifier is not None and modifier.arg1 == 2

    @property
    def is_perfect_salvage_kit(self) -> bool:
        """Return the native perfect-salvage-kit classification."""

        modifier = self.get_modifier(0x25E8)
        return modifier is not None and modifier.arg1 == 6

    @property
    def is_salvage_kit(self) -> bool:
        """Return whether the item is any native salvage-kit variant."""

        return self.is_lesser_kit or self.is_expert_salvage_kit or self.is_perfect_salvage_kit

    @property
    def is_rare_material(self) -> bool:
        """Return the native rare-material modifier classification."""

        modifier = self.get_modifier(0x2508)
        return modifier is not None and modifier.arg1 > 11

    def _read_pointer_text(self, pointer: int) -> str:
        """Read one of the item's indirect encoded strings."""

        if self._remote_reader is None:
            return ""
        return _read_encoded_wide(self._remote_reader, pointer)

    @property
    def name_encoded_str(self) -> str:
        """Return the raw encoded item name from ``name_enc``."""

        return self._read_pointer_text(int(self.name_enc))

    @property
    def name_str(self) -> str:
        """Return a printable representation of the item name."""

        return _format_encoded_text(self.name_encoded_str)

    @property
    def complete_name_encoded_str(self) -> str:
        """Return the encoded name including quantity and color data."""

        return self._read_pointer_text(int(self.complete_name_enc))

    @property
    def complete_name_str(self) -> str:
        """Return a printable complete item name."""

        return _format_encoded_text(self.complete_name_encoded_str)

    @property
    def single_item_name_encoded_str(self) -> str:
        """Return the encoded single-item name used by native rarity checks."""

        return self._read_pointer_text(int(self.single_item_name))

    @property
    def single_item_name_str(self) -> str:
        """Return a printable single-item name."""

        return _format_encoded_text(self.single_item_name_encoded_str)

    @property
    def info_string_encoded_str(self) -> str:
        """Return the encoded item information string."""

        return self._read_pointer_text(int(self.info_string))

    @property
    def info_string_str(self) -> str:
        """Return a printable item information string."""

        return _format_encoded_text(self.info_string_encoded_str)

    @property
    def is_stackable(self) -> bool:
        """Return the native stackability flag."""

        return bool(int(self.interaction) & 0x00080000)

    @property
    def is_inscribable(self) -> bool:
        """Return the native inscribability flag."""

        return bool(int(self.interaction) & 0x08000000)

    @property
    def is_identified(self) -> bool:
        """Return the native identification flag."""

        return bool(int(self.interaction) & 0x1)

    @property
    def is_usable(self) -> bool:
        """Return the native usability flag."""

        return bool(int(self.interaction) & 0x01000000)

    @property
    def is_tradable(self) -> bool:
        """Return the native tradability flag."""

        return not bool(int(self.interaction) & 0x100)

    @property
    def is_sparkly(self) -> bool:
        """Return the native sparkly flag."""

        return not bool(int(self.interaction) & 0x2000)

    @property
    def is_prefix_upgradable(self) -> bool:
        """Return whether the native prefix slot is upgradable."""

        return not bool((int(self.interaction) >> 14) & 1)

    @property
    def is_suffix_upgradable(self) -> bool:
        """Return whether the native suffix slot is upgradable."""

        return not bool((int(self.interaction) >> 15) & 1)

    @property
    def is_inscription(self) -> bool:
        """Return the native inscription flag combination."""

        return (int(self.interaction) & 0x25000000) == 0x25000000

    @property
    def is_purple(self) -> bool:
        """Return the native purple-rarity flag."""

        return bool(int(self.interaction) & 0x400000)

    def _read_blue_prefix(self) -> bool:
        """Read the native blue-rarity marker from the name pointer."""

        if self._remote_reader is None or int(self.single_item_name) < 0x10000:
            return False
        try:
            first_code_unit = int.from_bytes(
                self._remote_reader.read(int(self.single_item_name), 2), "little"
            )
        except (OSError, ValueError):
            return False
        return first_code_unit == 0xA3F

    @property
    def is_blue(self) -> bool:
        """Return the native blue-rarity result."""

        return self._read_blue_prefix()

    @property
    def is_green(self) -> bool:
        """Return the native green-rarity flag."""

        return bool(int(self.interaction) & 0x10)

    @property
    def is_gold(self) -> bool:
        """Return the native gold-rarity flag."""

        return bool(int(self.interaction) & 0x20000)

    @property
    def is_zcoin(self) -> bool:
        """Return whether the model-file ID is one of the native ZCoins."""

        return int(self.model_file_id) in {31202, 31203, 31204}

    @property
    def is_material(self) -> bool:
        """Return whether the item is a material but not a ZCoin."""

        return int(self.type) == 11 and not self.is_zcoin

    @property
    def rarity(self) -> ItemRarity:
        """Return the native rarity precedence used by the source project."""

        if self.is_green:
            return ItemRarity.green
        if self.is_gold:
            return ItemRarity.gold
        if self.is_purple:
            return ItemRarity.purple
        if self.is_blue:
            return ItemRarity.blue
        return ItemRarity.white

    @property
    def is_white(self) -> bool:
        """Return whether the item has white rarity."""

        return self.rarity is ItemRarity.white

    @property
    def is_weapon(self) -> bool:
        """Return whether the item type is one of the native weapon types."""

        return int(self.type) in _WEAPON_TYPES

    @property
    def is_armor(self) -> bool:
        """Return whether the item type is one of the native armor types."""

        return int(self.type) in _ARMOR_TYPES

    @property
    def is_salvageable(self) -> bool:
        """Apply the native read-only salvageability rules.

        Modifier-dependent rules such as kit uses and rare-material checks
        remain deferred because modifier decoding is intentionally not part of
        this migration pass.
        """

        if int(self.item_formula) == 0x5DA:
            return False
        if self.is_usable or self.is_green:
            return False
        item_type = int(self.type)
        if item_type == 30:  # Trophy
            return self.rarity is ItemRarity.white and bool(self.info_string) and bool(
                self.is_material_salvageable
            )
        if item_type in {0, 17}:  # Salvage and CC shards
            return True
        if item_type == 11:  # Materials/ZCoins
            return bool(self.is_material_salvageable)
        return self.is_weapon or self.is_armor

    @property
    def is_salvagable(self) -> bool:
        """Return salvageability using the native source spelling."""

        return self.is_salvageable

    def _read_owner_bag(self) -> BagStruct | None:
        """Read the owning bag needed by inventory/storage classification."""

        if self._remote_reader is None or self.bag_address is None:
            return None
        try:
            raw_bag = self._remote_reader.read(
                self.bag_address, ctypes.sizeof(BagStruct)
            )
        except (OSError, ValueError):
            return None
        return BagStruct.from_buffer_copy(raw_bag).bind_reader(
            self._remote_reader, self.bag_address
        )

    @property
    def is_inventory_item(self) -> bool:
        """Return whether the owning bag is inventory or equipped items."""

        bag = self._read_owner_bag()
        return bag is not None and (
            bag.is_inventory_bag or int(bag.bag_type) == 22
        )

    @property
    def is_storage_item(self) -> bool:
        """Return whether the owning bag is storage or material storage."""

        bag = self._read_owner_bag()
        return bag is not None and (bag.is_storage_bag or bag.is_material_storage)

    # Keep the native method names callable. The snake_case properties above
    # are convenience spellings; these methods preserve the C++ call surface.
    def GetIsStackable(self) -> bool:
        """Return the native stackability flag."""

        return self.is_stackable

    def GetIsInscribable(self) -> bool:
        """Return the native inscribability flag."""

        return self.is_inscribable

    def GetIsMaterial(self) -> bool:
        """Return whether this item is a material other than ZCoins."""

        return self.is_material

    def GetIsZcoin(self) -> bool:
        """Return whether this item is one of the native ZCoin models."""

        return self.is_zcoin

    def GetModifier(self, identifier: int) -> ItemModifierStruct | None:
        """Return the first matching native modifier, if present."""

        return self.get_modifier(identifier)

    def IsSparkly(self) -> bool:
        """Return the native sparkly flag result."""

        return self.is_sparkly

    def GetIsIdentified(self) -> bool:
        """Return whether the native identified bit is set."""

        return self.is_identified

    def IsPrefixUpgradable(self) -> bool:
        """Return whether the native prefix slot is upgradable."""

        return self.is_prefix_upgradable

    def IsSuffixUpgradable(self) -> bool:
        """Return whether the native suffix slot is upgradable."""

        return self.is_suffix_upgradable

    def IsUsable(self) -> bool:
        """Return whether the native usable bit is set."""

        return self.is_usable

    def IsTradable(self) -> bool:
        """Return whether the item is not marked non-tradable."""

        return self.is_tradable

    def IsInscription(self) -> bool:
        """Return whether the native inscription bit pattern matches."""

        return self.is_inscription

    def IsBlue(self) -> bool:
        """Return the native blue-rarity result."""

        return self.is_blue

    def IsPurple(self) -> bool:
        """Return whether the native purple bit is set."""

        return self.is_purple

    def IsGreen(self) -> bool:
        """Return whether the native green bit is set."""

        return self.is_green

    def IsGold(self) -> bool:
        """Return whether the native gold bit is set."""

        return self.is_gold

    def IsInventoryItem(self) -> bool:
        """Return whether the owning bag is an inventory/equipped bag."""

        return self.is_inventory_item

    def IsStorageItem(self) -> bool:
        """Return whether the owning bag is a storage bag."""

        return self.is_storage_item

    def GetUses(self) -> int:
        """Return the native uses modifier value or stack quantity."""

        return self.uses

    def IsTome(self) -> bool:
        """Return whether this item's tome modifier is in the native range."""

        return self.is_tome

    def IsIdentificationKit(self) -> bool:
        """Return whether the identification-kit modifier matches."""

        return self.is_identification_kit

    def IsLesserKit(self) -> bool:
        """Return whether the lesser salvage-kit modifier matches."""

        return self.is_lesser_kit

    def IsExpertSalvageKit(self) -> bool:
        """Return whether the expert salvage-kit modifier matches."""

        return self.is_expert_salvage_kit

    def IsPerfectSalvageKit(self) -> bool:
        """Return whether the perfect salvage-kit modifier matches."""

        return self.is_perfect_salvage_kit

    def IsSalvageKit(self) -> bool:
        """Return whether any native salvage-kit classification matches."""

        return self.is_salvage_kit

    def IsRareMaterial(self) -> bool:
        """Return whether the native rare-material modifier matches."""

        return self.is_rare_material

    def GetRarity(self) -> ItemRarity:
        """Return rarity using native green/gold/purple/blue precedence."""

        return self.rarity

    def IsWeapon(self) -> bool:
        """Return whether the item type is a native weapon type."""

        return self.is_weapon

    def IsArmor(self) -> bool:
        """Return whether the item type is a native armor type."""

        return self.is_armor

    def IsSalvagable(self) -> bool:
        """Return the native salvageability result."""

        return self.is_salvagable

    def IsOfferedInTrade(self) -> bool:
        """Return whether the current client's player offer contains this item."""

        if self._trade_context is None:
            raise RuntimeError("Item snapshot is not bound to a TradeContext reader.")
        trade_snapshot = self._trade_context.read()
        return (
            trade_snapshot is not None
            and trade_snapshot.is_item_offered(int(self.item_id))
        )


class BagStruct(TargetStruct):
    """The native fixed-width x86 ``Bag`` record (0x28 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("bag_type", c_uint32),
        ("index", c_uint32),
        ("_unknown0", c_uint32),
        ("container_item", c_uint32),
        ("items_count", c_uint32),
        ("bag_array", c_uint32),
        ("items", GWArray),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _trade_context: TradeContext | None = None
    npos: ClassVar[int] = 0xFFFFFFFF

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        trade_context: TradeContext | None = None,
    ) -> BagStruct:
        """Attach the reader used by the nested item-pointer array."""

        self._remote_reader = reader
        self._remote_address = address
        self._trade_context = trade_context
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this bag snapshot."""

        return self._remote_address

    @property
    def unknown_0(self) -> int:
        """Compatibility spelling for the native ``_unknown0`` field."""

        return int(self._unknown0)

    @property
    def items_array(self) -> GWArray:
        """Compatibility alias for the native ``items`` array header."""

        return self.items

    @items_array.setter
    def items_array(self, value: GWArray) -> None:
        self.items = value

    def bag_id(self) -> int:
        """Return the native one-based bag index."""

        return int(self.index) + 1

    @property
    def bag_id_value(self) -> int:
        """Return the one-based bag index as a Python-style property."""

        return self.bag_id()

    @property
    def is_inventory_bag(self) -> bool:
        """Return whether this is a normal inventory bag."""

        return int(self.bag_type) == 1

    @property
    def is_storage_bag(self) -> bool:
        """Return whether this is a storage bag."""

        return int(self.bag_type) == 8

    @property
    def is_material_storage(self) -> bool:
        """Return whether this is the material-storage bag."""

        return int(self.bag_type) == 6

    def _item_pointer(self, index: int) -> int | None:
        """Read one item pointer while preserving null slots."""

        if self._remote_reader is None:
            raise RuntimeError("Bag snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.items, ItemStruct)
        if not view.valid() or index < 0 or index >= view.size():
            return None
        try:
            raw_pointer = self._remote_reader.read(
                int(self.items.m_buffer) + index * 4, 4
            )
        except (OSError, ValueError):
            return None
        pointer = int.from_bytes(raw_pointer, "little")
        if pointer == 0:
            return 0
        return pointer if pointer >= 0x10000 else None

    def item_at(self, index: int) -> ItemStruct | None:
        """Read one item slot, returning ``None`` for empty/stale slots."""

        pointer = self._item_pointer(index)
        if pointer is None or pointer == 0 or self._remote_reader is None:
            return None
        try:
            raw_item = self._remote_reader.read(pointer, ctypes.sizeof(ItemStruct))
        except (OSError, ValueError):
            return None
        return ItemStruct.from_buffer_copy(raw_item).bind_reader(
            self._remote_reader, pointer, self._trade_context
        )

    def items_with_slots(self, limit: int = 256) -> list[ItemStruct | None]:
        """Read a bounded item-slot list without dropping empty slots."""

        if self._remote_reader is None:
            raise RuntimeError("Bag snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.items, ItemStruct)
        if not view.valid():
            return []
        return [
            self.item_at(index)
            for index in range(min(view.size(), max(0, limit)))
        ]

    def read_items(self, limit: int = 256) -> list[ItemStruct]:
        """Read at most ``limit`` item records from this bag."""

        return [
            value
            for value in self.items_with_slots(limit)
            if value is not None
        ]

    def item_records(self, limit: int = 256) -> list[ItemStruct]:
        """Readable alias for :meth:`read_items`."""

        return self.read_items(limit)

    def find1(self, model_id: int, pos: int = 0) -> int:
        """Find the first matching item slot, preserving native slot order."""

        pos = int(pos) & 0xFFFFFFFF
        if self._remote_reader is None:
            raise RuntimeError("Bag snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.items, ItemStruct)
        if not view.valid():
            return self.npos
        for index in range(pos, view.size()):
            pointer = self._item_pointer(index)
            if pointer == 0:
                if model_id == 0:
                    return index
                continue
            if pointer is None:
                continue
            item = self.item_at(index)
            if item is not None and int(item.model_id) == model_id:
                return index
        return self.npos

    def find_dye(
        self, model_id: int, dye: DyeInfoStruct, pos: int = 0
    ) -> int:
        """Find a model and exact packed-dye match in the item slots."""

        pos = int(pos) & 0xFFFFFFFF
        if self._remote_reader is None:
            raise RuntimeError("Bag snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.items, ItemStruct)
        if not view.valid():
            return self.npos
        for index in range(pos, view.size()):
            pointer = self._item_pointer(index)
            if pointer == 0:
                if model_id == 0:
                    return index
                continue
            if pointer is None:
                continue
            item = self.item_at(index)
            if item is not None and int(item.model_id) == model_id and bytes(item.dye) == bytes(dye):
                return index
        return self.npos

    def find2(self, item: ItemStruct, pos: int = 0) -> int:
        """Find an item using the native dye-aware search rule."""

        if int(item.model_id) == 146:  # ItemID::Dye
            return self.find_dye(int(item.model_id), item.dye, pos)
        return self.find1(int(item.model_id), pos)

    def IsInventoryBag(self) -> bool:
        """Return whether the native bag type is inventory."""

        return self.is_inventory_bag

    def IsStorageBag(self) -> bool:
        """Return whether the native bag type is storage."""

        return self.is_storage_bag

    def IsMaterialStorage(self) -> bool:
        """Return whether the native bag type is material storage."""

        return self.is_material_storage


class WeaponSetStruct(TargetStruct):
    """The native 0x08-byte weapon/offhand pointer pair."""

    _pack_ = 1
    _fields_ = [("weapon", c_uint32), ("offhand", c_uint32)]


class InventoryStruct(TargetStruct):
    """The native fixed-width x86 ``Inventory`` record (0x98 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("bags", c_uint32 * 23),
        ("bundle", c_uint32),
        ("storage_panes_unlocked", c_uint32),
        ("weapon_sets", WeaponSetStruct * 4),
        ("active_weapon_set", c_uint32),
        ("h0088", c_uint32 * 2),
        ("gold_character", c_uint32),
        ("gold_storage", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> InventoryStruct:
        """Attach the reader used by optional bag traversal."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    def _bag_address(self, index: int) -> int:
        """Return one bag pointer by its native array index."""

        return int(self.bags[index])

    @property
    def unused_bag(self) -> int:
        return self._bag_address(0)

    @property
    def backpack(self) -> int:
        return self._bag_address(1)

    @property
    def belt_pouch(self) -> int:
        return self._bag_address(2)

    @property
    def bag1(self) -> int:
        return self._bag_address(3)

    @property
    def bag2(self) -> int:
        return self._bag_address(4)

    @property
    def equipment_pack(self) -> int:
        return self._bag_address(5)

    @property
    def material_storage(self) -> int:
        return self._bag_address(6)

    @property
    def unclaimed_items(self) -> int:
        return self._bag_address(7)

    @property
    def storage1(self) -> int:
        return self._bag_address(8)

    @property
    def storage2(self) -> int:
        return self._bag_address(9)

    @property
    def storage3(self) -> int:
        return self._bag_address(10)

    @property
    def storage4(self) -> int:
        return self._bag_address(11)

    @property
    def storage5(self) -> int:
        return self._bag_address(12)

    @property
    def storage6(self) -> int:
        return self._bag_address(13)

    @property
    def storage7(self) -> int:
        return self._bag_address(14)

    @property
    def storage8(self) -> int:
        return self._bag_address(15)

    @property
    def storage9(self) -> int:
        return self._bag_address(16)

    @property
    def storage10(self) -> int:
        return self._bag_address(17)

    @property
    def storage11(self) -> int:
        return self._bag_address(18)

    @property
    def storage12(self) -> int:
        return self._bag_address(19)

    @property
    def storage13(self) -> int:
        return self._bag_address(20)

    @property
    def storage14(self) -> int:
        return self._bag_address(21)

    @property
    def equipped_items(self) -> int:
        return self._bag_address(22)

    @property
    def weapon_set0(self) -> int:
        return int(self.weapon_sets[0].weapon)

    @property
    def offhand_set0(self) -> int:
        return int(self.weapon_sets[0].offhand)

    @property
    def weapon_set1(self) -> int:
        return int(self.weapon_sets[1].weapon)

    @property
    def offhand_set1(self) -> int:
        return int(self.weapon_sets[1].offhand)

    @property
    def weapon_set2(self) -> int:
        return int(self.weapon_sets[2].weapon)

    @property
    def offhand_set2(self) -> int:
        return int(self.weapon_sets[2].offhand)

    @property
    def weapon_set3(self) -> int:
        return int(self.weapon_sets[3].weapon)

    @property
    def offhand_set3(self) -> int:
        return int(self.weapon_sets[3].offhand)

    @property
    def bag_addresses(self) -> list[int]:
        """Return non-null inventory bag addresses."""

        return [int(address) for address in self.bags if int(address)]

    @property
    def weapon_set_addresses(self) -> list[int]:
        """Return the eight weapon/offhand item addresses."""

        return [
            int(address)
            for weapon_set in self.weapon_sets
            for address in (weapon_set.weapon, weapon_set.offhand)
            if int(address)
        ]

    @property
    def inventory_bag_addresses(self) -> list[int]:
        """Return normal inventory-bag pointers in source order."""

        return [
            int(address)
            for index, address in enumerate(self.bags)
            if 1 <= index <= 5 and int(address)
        ]

    @property
    def storage_bag_addresses(self) -> list[int]:
        """Return storage-bag pointers in source order."""

        return [
            int(address)
            for index, address in enumerate(self.bags)
            if 8 <= index <= 21 and int(address)
        ]

    @property
    def material_storage_address(self) -> int | None:
        """Return the material-storage bag pointer, if present."""

        address = int(self.bags[6])
        return address or None

    @property
    def equipped_items_address(self) -> int | None:
        """Return the equipped-items bag pointer, if present."""

        address = int(self.bags[22])
        return address or None

    def bag_at(self, index: int) -> BagStruct | None:
        """Read one bounded inventory bag by its native zero-based index."""

        if self._remote_reader is None or index < 0 or index >= len(self.bags):
            return None
        address = int(self.bags[index])
        if address < 0x10000:
            return None
        try:
            raw_bag = self._remote_reader.read(address, ctypes.sizeof(BagStruct))
        except (OSError, ValueError):
            return None
        return BagStruct.from_buffer_copy(raw_bag).bind_reader(
            self._remote_reader, address
        )

    def bags_list(self, limit: int = 23) -> list[BagStruct]:
        """Read non-null inventory bags without exceeding the fixed array."""

        return [
            bag
            for index in range(min(max(0, limit), len(self.bags)))
            if (bag := self.bag_at(index)) is not None
        ]


class ItemFormulaStruct(TargetStruct):
    """The native 0x14 item-formula record.

    The material-cost pointer is retained as a target address.  The native
    source identifies that buffer as a cached value it does not use, so this
    reader does not dereference it.
    """

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("gold_cost", c_uint32),
        ("skill_point_cost", c_uint32),
        ("material_cost_count", c_uint32),
        ("material_cost_buffer", c_uint32),
    ]

    @property
    def material_cost_address(self) -> int | None:
        """Return the raw target address of the cached material buffer."""

        address = int(self.material_cost_buffer)
        return address or None


class PvPItemUpgradeInfoStruct(TargetStruct):
    """The native 0x28 unlocked-PvP-upgrade record."""

    _pack_ = 1
    _fields_ = [
        ("file_id", c_uint32),
        ("name_id", c_uint32),
        ("upgrade_type", c_uint32),
        ("campaign_id", c_uint32),
        ("interaction", c_uint32),
        ("is_dev", c_uint32),
        ("profession", c_uint32),
        ("h0018", c_uint32),
        ("mod_struct_size", c_uint32),
        ("mod_struct", c_uint32),
    ]

    @property
    def modifier_address(self) -> int | None:
        """Return the raw modifier-array address without dereferencing it."""

        address = int(self.mod_struct)
        return address or None


class PvPItemInfoStruct(TargetStruct):
    """The native 0x24 PvP-item metadata record."""

    _pack_ = 1
    _fields_ = [("unk", c_uint32 * 9)]


class CompositeModelInfoStruct(TargetStruct):
    """The native 0x30 composite-model lookup record."""

    _pack_ = 1
    _fields_ = [
        ("class_flags", c_uint32),
        ("file_ids", c_uint32 * 11),
    ]

    @property
    def file_id_list(self) -> list[int]:
        """Return the eleven source-defined composite file IDs."""

        return [int(file_id) for file_id in self.file_ids]


class SalvageSessionInfoStruct(TargetStruct):
    """The native 0x24-byte salvage-session record layout."""

    _pack_ = 1
    _fields_ = [
        ("vtable", c_uint32),
        ("frame_id", c_uint32),
        ("item_id", c_uint32),
        ("salvagable_1", c_uint32),
        ("salvagable_2", c_uint32),
        ("salvagable_3", c_uint32),
        ("chosen_salvagable", c_uint32),
        ("h001c", c_uint32),
        ("kit_id", c_uint32),
    ]


class ItemClickParamStruct(TargetStruct):
    """The native 0x0C-byte item-click parameter record."""

    _pack_ = 1
    _fields_ = [("unk0", c_uint32), ("slot", c_uint32), ("type", c_uint32)]


class InventoryTableEntryStruct(TargetStruct):
    """The native 0x0C-byte inventory-table entry header."""

    _pack_ = 1
    _fields_ = [("stride", c_uint32), ("end", c_uint32), ("start", c_uint32)]


class ItemContextStruct(TargetStruct):
    """The maintained fixed-width x86 0x10C item-context layout."""

    _pack_ = 1
    _fields_ = [
        ("h0000", GWArray),
        ("h0010", GWArray),
        ("h0020", c_uint32),
        ("bags_array", GWArray),
        ("h0034", c_uint32),
        ("h0038", c_uint32),
        ("h003C", c_uint32),
        ("h0040", GWArray),
        ("h0050", GWArray),
        ("h0060", c_uint32),
        ("h0064", c_uint32),
        ("h0068", c_uint32),
        ("h006C", c_uint32),
        ("h0070", c_uint32),
        ("h0074", c_uint32),
        ("h0078", c_uint32),
        ("h007C", c_uint32),
        ("h0080", c_uint32),
        ("h0084", c_uint32),
        ("h0088", c_uint32),
        ("h008C", c_uint32),
        ("h0090", c_uint32),
        ("h0094", c_uint32),
        ("h0098", c_uint32),
        ("h009C", c_uint32),
        ("h00A0", c_uint32),
        ("h00A4", c_uint32),
        ("h00A8", c_uint32),
        ("h00AC", c_uint32),
        ("h00B0", c_uint32),
        ("h00B4", c_uint32),
        ("item_array", GWArray),
        ("h00C8", c_uint32),
        ("h00CC", c_uint32),
        ("h00D0", c_uint32),
        ("h00D4", c_uint32),
        ("h00D8", c_uint32),
        ("h00DC", c_uint32),
        ("h00E0", c_uint32),
        ("inventory_table", GWArray),
        ("h00F4", c_uint32),
        ("inventory", c_uint32),
        ("h00FC", GWArray),
    ]

    _remote_address: int | None = None
    _remote_reader: _memory_reader | None = None
    _trade_context: TradeContext | None = None

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        trade_context: TradeContext | None = None,
    ) -> ItemContextStruct:
        """Attach the target address represented by this root snapshot."""

        self._remote_reader = reader
        self._remote_address = address
        self._trade_context = trade_context
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this snapshot."""

        return self._remote_address

    @property
    def inventory_ptr(self) -> int:
        """Compatibility spelling for the native ``inventory`` pointer."""

        return int(self.inventory)

    @property
    def array_sizes(self) -> dict[str, int]:
        """Return advertised sizes for the root array headers."""

        result: dict[str, int] = {}
        for field in self._fields_:
            field_name, field_type = field[0], field[1]
            if field_type is GWArray:
                result[field_name] = int(getattr(self, field_name).m_size)
        return result

    def bags(self, limit: int = 64) -> list[BagStruct]:
        """Read at most ``limit`` bag records from the maintained bag array."""

        if self._remote_reader is None:
            raise RuntimeError("ItemContext snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.bags_array, BagStruct)
        if not view.valid():
            return []
        return [
            value.bind_reader(
                self._remote_reader,
                value.address,
                self._trade_context,
            )
            for index in range(min(view.size(), max(0, limit)))
            if isinstance((value := view.get(index)), BagStruct)
        ]

    def global_items(self, limit: int = 256) -> list[ItemStruct]:
        """Read an explicit bounded sample from the raw global item array.

        This is not the normal inventory traversal.  Callers must provide an
        explicit bound because the live header may advertise a large value that
        is not an inventory-item count.
        """

        if self._remote_reader is None:
            raise RuntimeError("ItemContext snapshot is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.item_array, ItemStruct)
        if not view.valid():
            return []
        return [
            value.bind_reader(
                self._remote_reader,
                value.address,
                self._trade_context,
            )
            for index in range(min(view.size(), max(0, limit)))
            if isinstance((value := view.get(index)), ItemStruct)
        ]

    def read_inventory(self) -> InventoryStruct | None:
        """Read the optional inventory relationship from this root."""

        if self._remote_reader is None:
            raise RuntimeError("ItemContext snapshot is not bound to a reader.")
        address = int(self.inventory)
        if address < 0x10000:
            return None
        raw_inventory = self._remote_reader.read(
            address, ctypes.sizeof(InventoryStruct)
        )
        return InventoryStruct.from_buffer_copy(raw_inventory).bind_reader(
            self._remote_reader, address
        )


assert ctypes.sizeof(ItemContextStruct) == 0x10C
assert ctypes.sizeof(DyeInfoStruct) == 0x03
assert ctypes.sizeof(ItemStruct) == 0x54
assert ctypes.sizeof(BagStruct) == 0x28
assert ctypes.sizeof(InventoryStruct) == 0x98
assert ctypes.sizeof(ItemFormulaStruct) == 0x14
assert ctypes.sizeof(PvPItemUpgradeInfoStruct) == 0x28
assert ctypes.sizeof(PvPItemInfoStruct) == 0x24
assert ctypes.sizeof(CompositeModelInfoStruct) == 0x30
assert ctypes.sizeof(MaterialCostStruct) == 0x10
assert ctypes.sizeof(WeaponSetStruct) == 0x08
assert ctypes.sizeof(SalvageSessionInfoStruct) == 0x24
assert ctypes.sizeof(ItemClickParamStruct) == 0x0C
assert ctypes.sizeof(InventoryTableEntryStruct) == 0x0C
assert ItemStruct.mod_struct.offset == 0x10
assert ItemStruct.mod_struct_size.offset == 0x14
assert ItemStruct.dye.offset == 0x21
assert ItemStruct.interaction.offset == 0x28
assert ItemStruct.quantity.offset == 0x4C
assert BagStruct.items.offset == 0x18
assert ItemContextStruct.bags_array.offset == 0x24
assert ItemContextStruct.item_array.offset == 0xB8
assert ItemContextStruct.inventory_table.offset == 0xE4
assert ItemContextStruct.inventory.offset == 0xF8


class ItemContext:
    """Resolve and read the current item-context root through ``GameContext``."""

    _AUXILIARY_RESOLVERS = {
        "storage_open_address": "item.storage_open_addr",
        "pvp_item_upgrade_buffer": "item.pvp_item_upgrade_array_buffer",
        "pvp_item_upgrade_size": "item.pvp_item_upgrade_array_size",
        "pvp_item_buffer": "item.pvp_item_array_buffer",
        "pvp_item_size": "item.pvp_item_array_size",
        "composite_model_array": "item.composite_model_info_array",
        "item_formulas_address": "item.item_formulas_addr",
        "item_formulas_count": "item.item_formulas_count",
    }
    _MAX_AUXILIARY_RECORDS = 0x10000

    def __init__(
        self,
        reader: _memory_reader,
        game_context: GameContext,
        scanner: RemoteScanner | None = None,
        patterns: PatternCatalog | None = None,
    ) -> None:
        """Create a reader using the selected client's cached game context.

        ``scanner`` and ``patterns`` are optional for compatibility with a
        root-only reader.  When supplied, :meth:`initialize` resolves and
        caches the native item-global pointers once for the connection.
        """

        self._reader = reader
        self._game_context = game_context
        self._trade_context = TradeContext(reader, game_context)
        self._scanner = scanner
        self._patterns = patterns
        self._auxiliary_addresses: dict[str, int] = {}
        self._auxiliary_errors: dict[str, str] = {}
        self._auxiliary_initialized = False

    @property
    def cached_auxiliary_addresses(self) -> dict[str, int]:
        """Return the successfully resolved native item-global addresses."""

        return dict(self._auxiliary_addresses)

    @property
    def auxiliary_resolution_errors(self) -> dict[str, str]:
        """Return non-fatal resolver failures from auxiliary item globals."""

        return dict(self._auxiliary_errors)

    def initialize(self) -> dict[str, int]:
        """Resolve auxiliary item globals once and cache their locations.

        A missing optional resolver does not make the ordinary item-context
        reader unusable.  Its failure is retained in
        :attr:`auxiliary_resolution_errors` so callers can distinguish an
        unavailable source surface from an empty live array.
        """

        if self._auxiliary_initialized:
            return self.cached_auxiliary_addresses
        self._auxiliary_initialized = True
        if self._scanner is None or self._patterns is None:
            return {}
        for name, resolver_name in self._AUXILIARY_RESOLVERS.items():
            try:
                result = self._patterns.resolve(resolver_name, self._scanner)
            except (KeyError, OSError, ValueError) as error:
                self._auxiliary_errors[name] = str(error)
                continue
            if result.ok and result.value:
                self._auxiliary_addresses[name] = result.value
            else:
                self._auxiliary_errors[name] = result.message or "resolver returned no address"
        return self.cached_auxiliary_addresses

    def _ensure_auxiliary_initialized(self) -> None:
        """Initialize optional item globals when the caller has provided them."""

        if not self._auxiliary_initialized:
            self.initialize()

    def _read_array_header(self, address: int) -> GWArray | None:
        """Read and validate one target ``GWArray`` header."""

        if address < 0x10000:
            return None
        try:
            raw_header = self._reader.read(address, ctypes.sizeof(GWArray))
        except (OSError, ValueError):
            return None
        return GWArray.from_buffer_copy(raw_header)

    def _read_auxiliary_values(
        self,
        buffer_name: str,
        size_name: str,
        element_type: type[Structure],
        limit: int,
    ) -> list[Structure]:
        """Read a bounded contiguous array resolved from native globals."""

        self._ensure_auxiliary_initialized()
        buffer = self._auxiliary_addresses.get(buffer_name, 0)
        size = self._auxiliary_addresses.get(size_name, 0)
        count = min(max(0, size), max(0, limit), self._MAX_AUXILIARY_RECORDS)
        if buffer < 0x10000 or count == 0:
            return []
        array = GWArray(buffer, count, count, 0)
        view = GWArrayValueView(self._reader, array, element_type)
        return [value for value in view.to_list() if isinstance(value, Structure)]

    @property
    def storage_open_address(self) -> int | None:
        """Return the cached native storage-open flag address, if resolved."""

        self._ensure_auxiliary_initialized()
        address = self._auxiliary_addresses.get("storage_open_address", 0)
        return address or None

    @property
    def is_storage_open(self) -> bool | None:
        """Read the native storage-open flag when its pointer is available."""

        address = self.storage_open_address
        if address is None:
            return None
        try:
            return bool(int.from_bytes(self._reader.read(address, 4), "little"))
        except (OSError, ValueError):
            return None

    def read_item_formulas(self, limit: int = 4096) -> list[ItemFormulaStruct]:
        """Read the bounded native item-formula table."""

        self._ensure_auxiliary_initialized()
        address = self._auxiliary_addresses.get("item_formulas_address", 0)
        count = min(
            max(0, self._auxiliary_addresses.get("item_formulas_count", 0)),
            max(0, limit),
            self._MAX_AUXILIARY_RECORDS,
        )
        if address < 0x10000 or count == 0:
            return []
        values: list[ItemFormulaStruct] = []
        for index in range(count):
            try:
                raw_value = self._reader.read(
                    address + index * ctypes.sizeof(ItemFormulaStruct),
                    ctypes.sizeof(ItemFormulaStruct),
                )
            except (OSError, ValueError):
                break
            values.append(ItemFormulaStruct.from_buffer_copy(raw_value))
        return values

    def get_item_formula_count(self) -> int:
        """Return the count reported by the native ``GetItemFormulaCount``.

        The native helper returns the count associated with the item-formula
        pointer. Stealth resolves and caches both values during initialization;
        if that optional resolver is unavailable, its initial value is zero,
        matching the native global's startup value.
        """

        self._ensure_auxiliary_initialized()
        return int(self._auxiliary_addresses.get("item_formulas_count", 0))

    def GetItemFormulaCount(self) -> int:
        """Expose the native helper spelling for directly ported callers."""

        return self.get_item_formula_count()

    def read_item_formula(self, index: int) -> ItemFormulaStruct | None:
        """Read one item formula by its native zero-based index."""

        if index < 0:
            return None
        formulas = self.read_item_formulas(index + 1)
        return formulas[index] if index < len(formulas) else None

    def read_composite_model_infos(
        self, limit: int = 4096
    ) -> list[CompositeModelInfoStruct]:
        """Read the bounded native composite-model table."""

        self._ensure_auxiliary_initialized()
        address = self._auxiliary_addresses.get("composite_model_array", 0)
        array = self._read_array_header(address)
        if array is None or not array.m_buffer or array.m_size > array.m_capacity:
            return []
        view = GWArrayValueView(self._reader, array, CompositeModelInfoStruct)
        return [
            value
            for index in range(min(view.size(), max(0, limit), self._MAX_AUXILIARY_RECORDS))
            if (value := view.get(index)) is not None
        ]

    def read_composite_model_info(
        self, model_file_id: int
    ) -> CompositeModelInfoStruct | None:
        """Read the composite-model record indexed by model-file ID."""

        if model_file_id < 0:
            return None
        self._ensure_auxiliary_initialized()
        address = self._auxiliary_addresses.get("composite_model_array", 0)
        array = self._read_array_header(address)
        if array is None or model_file_id >= array.m_size or array.m_size > array.m_capacity:
            return None
        view = GWArrayValueView(self._reader, array, CompositeModelInfoStruct)
        value = view.get(model_file_id)
        return value if isinstance(value, CompositeModelInfoStruct) else None

    def get_composite_model_ids(self, model_file_id: int) -> list[int]:
        """Return the source-defined composite file IDs for one model ID."""

        info = self.read_composite_model_info(model_file_id)
        return [] if info is None else info.file_id_list

    def read_pvp_item_upgrades(
        self, limit: int = 4096
    ) -> list[PvPItemUpgradeInfoStruct]:
        """Read the bounded unlocked-PvP-upgrade table."""

        values = self._read_auxiliary_values(
            "pvp_item_upgrade_buffer",
            "pvp_item_upgrade_size",
            PvPItemUpgradeInfoStruct,
            limit,
        )
        return [value for value in values if isinstance(value, PvPItemUpgradeInfoStruct)]

    def read_pvp_items(self, limit: int = 4096) -> list[PvPItemInfoStruct]:
        """Read the bounded native PvP-item metadata table."""

        values = self._read_auxiliary_values(
            "pvp_item_buffer", "pvp_item_size", PvPItemInfoStruct, limit
        )
        return [value for value in values if isinstance(value, PvPItemInfoStruct)]

    def resolve_address(self) -> int | None:
        """Return the current item-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.item_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> ItemContextStruct | None:
        """Read the complete maintained item root without child traversal."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(ItemContextStruct))
        return ItemContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address, self._trade_context
        )


def get() -> ItemContextStruct | None:
    """Read the current client's item context, if one is available."""

    from ..client import current_client

    client = current_client()
    return client.read_item_context() if client is not None else None
