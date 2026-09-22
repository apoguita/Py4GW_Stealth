"""Bounded external traversal of Guild Wars' native agent pointer table."""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from ctypes import Structure, c_float, c_uint8, c_uint16, c_uint32
from contextlib import nullcontext
from typing import Protocol, TypeVar, cast

from ..performance import PerfCounter
from ..scanner import PatternCatalog, RemoteScanner
from .acc_agent_context import AccAgentContext, Vec3fStruct
from .gw_array import GWArray, RemoteMemoryReader
from .gw_list import GWLinkStruct, GWListStruct, RemoteGWListView


class _memory_reader(RemoteMemoryReader, Protocol):
    """The read-only operation needed by the agent-array reader."""


class AgentKind(str, Enum):
    """The native top-level type selected from an agent's type flags."""

    LIVING = "living"
    GADGET = "gadget"
    ITEM = "item"
    UNKNOWN = "unknown"


class AgentType(IntFlag):
    """The native type masks stored in the common agent record."""

    LIVING = 0xDB
    GADGET = 0x200
    ITEM = 0x400


class AgentAllegiance(IntEnum):
    """The native living-agent allegiance values."""

    ALLY_NON_ATTACKABLE = 1
    NEUTRAL = 2
    ENEMY = 3
    SPIRIT_PET = 4
    MINION = 5
    NPC_MINIPET = 6


class StaleAgentReferenceError(RuntimeError):
    """Raised when a reference changed before its complete record was read."""


class Vec2fStruct(Structure):
    """The native two-float agent velocity value."""

    _pack_ = 1
    _fields_ = [("x", c_float), ("y", c_float)]


class GamePositionStruct(Structure):
    """The native agent position value."""

    _pack_ = 1
    _fields_ = [("x", c_float), ("y", c_float), ("zplane", c_uint32)]


class AgentStruct(Structure):
    """The complete common native ``Agent`` record (0xC4 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("vtable_ptr", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000C", c_uint32 * 2),
        ("timer", c_uint32),
        ("timer2", c_uint32),
        ("link_link", GWLinkStruct),
        ("link2_link", GWLinkStruct),
        ("agent_id", c_uint32),
        ("z", c_float),
        ("width1", c_float),
        ("height1", c_float),
        ("width2", c_float),
        ("height2", c_float),
        ("width3", c_float),
        ("height3", c_float),
        ("rotation_angle", c_float),
        ("rotation_cos", c_float),
        ("rotation_sin", c_float),
        ("name_properties", c_uint32),
        ("ground", c_uint32),
        ("h0060", c_uint32),
        ("terrain_normal", Vec3fStruct),
        ("h0070", c_uint8 * 4),
        ("pos", GamePositionStruct),
        ("h0080", c_uint8 * 4),
        ("name_tag_x", c_float),
        ("name_tag_y", c_float),
        ("name_tag_z", c_float),
        ("visual_effects", c_uint16),
        ("h0092", c_uint16),
        ("h0094", c_uint32 * 2),
        ("type", c_uint32),
        ("velocity", Vec2fStruct),
        ("h00A8", c_uint32),
        ("rotation_cos2", c_float),
        ("rotation_sin2", c_float),
        ("h00B4", c_uint32 * 4),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AgentStruct:
        """Attach the reader and address represented by this snapshot."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    @property
    def remote_address(self) -> int | None:
        """Return the target address represented by this record."""

        return self._remote_address

    @property
    def vtable(self) -> int:
        """Return the target vtable address as a fixed-width integer."""

        return int(self.vtable_ptr)

    @property
    def is_item_type(self) -> bool:
        """Return whether the native type flags identify an item."""

        return bool(int(self.type) & AgentType.ITEM)

    @property
    def is_gadget_type(self) -> bool:
        """Return whether the native type flags identify a gadget."""

        return bool(int(self.type) & AgentType.GADGET)

    @property
    def is_living_type(self) -> bool:
        """Return whether the native type flags identify a living agent."""

        return bool(int(self.type) & AgentType.LIVING)

    @property
    def position(self) -> tuple[float, float, int]:
        """Return the agent's x, y, and plane values."""

        return (float(self.pos.x), float(self.pos.y), int(self.pos.zplane))

    @property
    def xy(self) -> tuple[float, float]:
        """Return the agent's x and y coordinates."""

        return (float(self.pos.x), float(self.pos.y))

    @property
    def velocity_xy(self) -> tuple[float, float]:
        """Return the agent's movement velocity."""

        return (float(self.velocity.x), float(self.velocity.y))

    def GetAsAgentItem(self) -> AgentItemStruct | None:
        """Return this record as an item record when its type permits it."""

        if not self.is_item_type:
            return None
        if isinstance(self, AgentItemStruct):
            return self
        value = AgentItemStruct.from_buffer_copy(bytes(self))
        if self._remote_reader is not None:
            value.bind_reader(self._remote_reader, self._remote_address)
        return cast(AgentItemStruct, value)

    def GetAsAgentGadget(self) -> AgentGadgetStruct | None:
        """Return this record as a gadget record when its type permits it."""

        if not self.is_gadget_type:
            return None
        if isinstance(self, AgentGadgetStruct):
            return self
        value = AgentGadgetStruct.from_buffer_copy(bytes(self))
        if self._remote_reader is not None:
            value.bind_reader(self._remote_reader, self._remote_address)
        return cast(AgentGadgetStruct, value)

    def GetAsAgentLiving(self) -> AgentLivingStruct | None:
        """Return this record as a living record when its type permits it."""

        if not self.is_living_type:
            return None
        if isinstance(self, AgentLivingStruct):
            return self
        value = AgentLivingStruct.from_buffer_copy(bytes(self))
        if self._remote_reader is not None:
            value.bind_reader(self._remote_reader, self._remote_address)
        return cast(AgentLivingStruct, value)


class AgentItemStruct(AgentStruct):
    """The complete native item-agent record (0xD4 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("owner", c_uint32),
        ("item_id", c_uint32),
        ("h00CC", c_uint32),
        ("extra_type", c_uint32),
    ]


class AgentGadgetStruct(AgentStruct):
    """The complete native gadget-agent record (0xE4 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("h00C4", c_uint32),
        ("h00C8", c_uint32),
        ("extra_type", c_uint32),
        ("gadget_id", c_uint32),
        ("h00D4", c_uint32 * 4),
    ]


class DyeInfoStruct(Structure):
    """Packed native dye information embedded in equipment items."""

    _pack_ = 1
    _fields_ = [
        ("dye_tint", c_uint8),
        ("dye1", c_uint8, 4),
        ("dye2", c_uint8, 4),
        ("dye3", c_uint8, 4),
        ("dye4", c_uint8, 4),
    ]


class ItemDataStruct(Structure):
    """The native 0x10-byte embedded equipment item record."""

    _pack_ = 1
    _fields_ = [
        ("model_file_id", c_uint32),
        ("type", c_uint8),
        ("dye", DyeInfoStruct),
        ("value", c_uint32),
        ("interaction", c_uint32),
    ]


class EquipmentItemsUnionStruct(ctypes.Union):
    """The nine embedded equipment item slots."""

    _pack_ = 1
    _fields_ = [
        ("items", ItemDataStruct * 9),
        ("weapon", ItemDataStruct),
        ("offhand", ItemDataStruct),
        ("chest", ItemDataStruct),
        ("legs", ItemDataStruct),
        ("head", ItemDataStruct),
        ("feet", ItemDataStruct),
        ("hands", ItemDataStruct),
        ("costume_body", ItemDataStruct),
        ("costume_head", ItemDataStruct),
    ]


class EquipmentItemIDsUnionStruct(ctypes.Union):
    """The nine embedded equipment item IDs."""

    _pack_ = 1
    _fields_ = [
        ("item_ids", c_uint32 * 9),
        ("item_id_weapon", c_uint32),
        ("item_id_offhand", c_uint32),
        ("item_id_chest", c_uint32),
        ("item_id_legs", c_uint32),
        ("item_id_head", c_uint32),
        ("item_id_feet", c_uint32),
        ("item_id_hands", c_uint32),
        ("item_id_costume_body", c_uint32),
        ("item_id_costume_head", c_uint32),
    ]


class EquipmentStruct(Structure):
    """The native 0xD8-byte equipment record."""

    _pack_ = 1
    _fields_ = [
        ("vtable_ptr", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000C", c_uint32),
        ("left_hand_ptr", c_uint32),
        ("right_hand_ptr", c_uint32),
        ("h0018", c_uint32),
        ("shield_ptr", c_uint32),
        ("left_hand_map", c_uint8),
        ("right_hand_map", c_uint8),
        ("head_map", c_uint8),
        ("shield_map", c_uint8),
        ("items_union", EquipmentItemsUnionStruct),
        ("ids_union", EquipmentItemIDsUnionStruct),
    ]

    @property
    def left_hand(self) -> ItemDataStruct | None:
        """Return the embedded item selected by the left-hand map."""

        index = int(self.left_hand_map)
        return self.items_union.items[index] if index < 9 else None

    @property
    def right_hand(self) -> ItemDataStruct | None:
        """Return the embedded item selected by the right-hand map."""

        index = int(self.right_hand_map)
        return self.items_union.items[index] if index < 9 else None

    @property
    def shield(self) -> ItemDataStruct | None:
        """Return the embedded item selected by the shield map."""

        index = int(self.shield_map)
        return self.items_union.items[index] if index < 9 else None

    @property
    def item_ids(self) -> tuple[int, ...]:
        """Return all nine embedded equipment item IDs."""

        return tuple(int(value) for value in self.ids_union.item_ids)


class TagInfoStruct(Structure):
    """The native compact living-agent tag record."""

    _pack_ = 1
    _fields_ = [
        ("guild_id", c_uint16),
        ("primary", c_uint8),
        ("secondary", c_uint8),
        ("level", c_uint16),
    ]


class VisibleEffectStruct(Structure):
    """One native visible effect entry (0x0C bytes)."""

    _pack_ = 1
    _fields_ = [
        ("unk", c_uint32),
        ("effect_id", c_uint32),
        ("has_ended", c_uint32),
    ]

    @property
    def is_active(self) -> bool:
        """Return whether the target effect has not entered its end state."""

        return int(self.has_ended) == 0


class AgentLivingStruct(AgentStruct):
    """The complete native living-agent record (0x1C4 bytes)."""

    _MAX_VISIBLE_EFFECTS = 128

    _pack_ = 1
    _fields_ = [
        ("owner", c_uint32),
        ("h00C8", c_uint32),
        ("h00CC", c_uint32),
        ("h00D0", c_uint32),
        ("h00D4", c_uint32 * 3),
        ("animation_type", c_float),
        ("h00E4", c_uint32 * 2),
        ("weapon_attack_speed", c_float),
        ("attack_speed_modifier", c_float),
        ("player_number", c_uint16),
        ("agent_model_type", c_uint16),
        ("transmog_npc_id", c_uint32),
        ("equipment_ptr_ptr", c_uint32),
        ("h0100", c_uint32),
        ("h0104", c_uint32),
        ("tags_ptr", c_uint32),
        ("h010C", c_uint16),
        ("primary", c_uint8),
        ("secondary", c_uint8),
        ("level", c_uint8),
        ("team_id", c_uint8),
        ("h0112", c_uint8 * 2),
        ("h0114", c_uint32),
        ("energy_regen", c_float),
        ("h011C", c_uint32),
        ("energy", c_float),
        ("max_energy", c_uint32),
        ("h0128", c_uint32),
        ("hp_pips", c_float),
        ("h0130", c_uint32),
        ("hp", c_float),
        ("max_hp", c_uint32),
        ("effects", c_uint32),
        ("h0140", c_uint32),
        ("hex", c_uint8),
        ("h0145", c_uint8 * 19),
        ("model_state", c_uint32),
        ("type_map", c_uint32),
        ("h0160", c_uint32 * 4),
        ("in_spirit_range", c_uint32),
        ("visible_effects_list", GWListStruct),
        ("h0180", c_uint32),
        ("login_number", c_uint32),
        ("animation_speed", c_float),
        ("animation_code", c_uint32),
        ("animation_id", c_uint32),
        ("h0194", c_uint8 * 32),
        ("dagger_status", c_uint8),
        ("allegiance", c_uint8),
        ("weapon_type", c_uint16),
        ("skill", c_uint16),
        ("h01BA", c_uint16),
        ("weapon_item_type", c_uint8),
        ("offhand_item_type", c_uint8),
        ("weapon_item_id", c_uint16),
        ("offhand_item_id", c_uint16),
        ("h01C2", c_uint8 * 2),
    ]

    @property
    def equipment(self) -> EquipmentStruct | None:
        """Read the optional equipment object through its pointer-to-pointer."""

        if self._remote_reader is None:
            raise RuntimeError("This living agent is not bound to a memory reader.")
        pointer_address = int(self.equipment_ptr_ptr)
        if pointer_address < 0x10000:
            return None
        raw_pointer = self._remote_reader.read(pointer_address, 4)
        equipment_address = int.from_bytes(raw_pointer, "little")
        if equipment_address < 0x10000:
            return None
        raw_equipment = self._remote_reader.read(
            equipment_address, ctypes.sizeof(EquipmentStruct)
        )
        return EquipmentStruct.from_buffer_copy(raw_equipment)

    @property
    def tags(self) -> TagInfoStruct | None:
        """Read the optional tag record through its target pointer."""

        if self._remote_reader is None:
            raise RuntimeError("This living agent is not bound to a memory reader.")
        tag_address = int(self.tags_ptr)
        if tag_address < 0x10000:
            return None
        raw_tags = self._remote_reader.read(tag_address, ctypes.sizeof(TagInfoStruct))
        return TagInfoStruct.from_buffer_copy(raw_tags)

    @property
    def visible_effects(self) -> list[VisibleEffectStruct]:
        """Read the bounded native visible-effects list for this record."""

        if self._remote_reader is None or self._remote_address is None:
            raise RuntimeError("This living agent is not bound to a target address.")
        list_address = self._remote_address + AgentLivingStruct.visible_effects_list.offset
        return list(
            RemoteGWListView(
                self._remote_reader,
                self.visible_effects_list,
                list_address,
                VisibleEffectStruct,
                max_entries=self._MAX_VISIBLE_EFFECTS,
            )
        )

    @property
    def is_bleeding(self) -> bool:
        """Return whether the native effects bitmap marks bleeding."""

        return bool(int(self.effects) & 0x0001)

    @property
    def is_conditioned(self) -> bool:
        """Return whether the native effects bitmap marks condition."""

        return bool(int(self.effects) & 0x0002)

    @property
    def is_used_corpse(self) -> bool:
        """Return whether the native effects bitmap marks a used corpse."""

        return bool(int(self.effects) & 0x0004)

    @property
    def is_crippled(self) -> bool:
        """Return whether the native crippled combination is present."""

        return (int(self.effects) & 0x000A) == 0x000A

    @property
    def allegiance_enum(self) -> AgentAllegiance | None:
        """Return the known allegiance enum, if the value is recognized."""

        try:
            return AgentAllegiance(int(self.allegiance))
        except ValueError:
            return None

    @property
    def is_dead(self) -> bool:
        """Return whether the native effects field marks this agent dead."""

        return bool(int(self.effects) & 0x10)

    @property
    def is_deep_wounded(self) -> bool:
        """Return whether the native effects bitmap marks deep wound."""

        return bool(int(self.effects) & 0x0020)

    @property
    def is_poisoned(self) -> bool:
        """Return whether the native effects bitmap marks poison."""

        return bool(int(self.effects) & 0x0040)

    @property
    def is_enchanted(self) -> bool:
        """Return whether the native effects bitmap marks enchantment."""

        return bool(int(self.effects) & 0x0080)

    @property
    def is_degen_hexed(self) -> bool:
        """Return whether the native effects bitmap marks degeneration hex."""

        return bool(int(self.effects) & 0x0400)

    @property
    def is_hexed(self) -> bool:
        """Return whether the native effects bitmap marks hex."""

        return bool(int(self.effects) & 0x0800)

    @property
    def is_weapon_spelled(self) -> bool:
        """Return whether the native effects bitmap marks weapon spell."""

        return bool(int(self.effects) & 0x8000)

    @property
    def is_alive(self) -> bool:
        """Return the Reforged composite alive state."""

        return not self.is_dead and float(self.hp) > 0.0

    @property
    def is_player(self) -> bool:
        """Return whether the agent has a non-zero login number."""

        return int(self.login_number) != 0

    @property
    def is_npc(self) -> bool:
        """Return whether the agent has no player login number."""

        return not self.is_player

    @property
    def is_dead_by_type_map(self) -> bool:
        """Return whether the native type-map dead bit is set."""

        return bool(int(self.type_map) & 0x8)

    @property
    def is_in_combat_stance(self) -> bool:
        """Return whether the type map marks combat stance."""

        return bool(int(self.type_map) & 0x000001)

    @property
    def has_quest(self) -> bool:
        """Return whether the type map marks a quest."""

        return bool(int(self.type_map) & 0x000002)

    @property
    def is_female(self) -> bool:
        """Return whether the type map marks a female model."""

        return bool(int(self.type_map) & 0x000200)

    @property
    def has_boss_glow(self) -> bool:
        """Return whether the type map marks a boss glow."""

        return bool(int(self.type_map) & 0x000400)

    @property
    def is_hiding_cape(self) -> bool:
        """Return whether the type map marks a hidden cape."""

        return bool(int(self.type_map) & 0x001000)

    @property
    def can_be_viewed_in_party_window(self) -> bool:
        """Return whether the type map permits party-window display."""

        return bool(int(self.type_map) & 0x020000)

    @property
    def is_spawned(self) -> bool:
        """Return whether the type map marks the agent as spawned."""

        return bool(int(self.type_map) & 0x040000)

    @property
    def is_being_observed(self) -> bool:
        """Return whether the type map marks the agent as observed."""

        return bool(int(self.type_map) & 0x400000)

    @property
    def is_knocked_down(self) -> bool:
        """Return whether the native model state is knocked down."""

        return int(self.model_state) == 1104

    @property
    def is_moving(self) -> bool:
        """Return whether the native model state is a moving state."""

        return int(self.model_state) in {12, 76, 204}

    @property
    def is_attacking(self) -> bool:
        """Return whether the native model state is an attacking state."""

        return int(self.model_state) in {96, 1088, 1120}

    @property
    def is_casting(self) -> bool:
        """Return whether the native model state is a casting state."""

        return int(self.model_state) in {65, 581}

    @property
    def is_idle(self) -> bool:
        """Return whether the native model state is idle."""

        return int(self.model_state) in {68, 64, 100}

    @property
    def is_exploitable(self) -> bool:
        """Return whether this dead agent is not marked as a used corpse."""

        return not self.is_alive and not self.is_used_corpse

    @property
    def corpse_exploit_state(self) -> str:
        """Return the Reforged corpse-state label."""

        if self.is_alive:
            return "alive"
        if self.is_used_corpse:
            return "used_corpse"
        return "exploitable"

    @property
    def corpse_exploit_signature(self) -> tuple[int, ...]:
        """Return the native fields used to compare corpse states."""

        return (
            int(self.effects),
            int(self.model_state),
            int(self.type_map),
            int(self.player_number),
            int(self.agent_model_type),
            int(self.animation_code),
            int(self.animation_id),
            int(self.h00D4[0]),
            int(self.h00D4[1]),
            int(self.h00D4[2]),
            int(self.h00E4[0]),
            int(self.h00E4[1]),
            int(self.h0140),
            int(self.h0160[0]),
            int(self.h0160[1]),
            int(self.h0160[2]),
            int(self.h0160[3]),
            int(self.h0180),
        )


assert ctypes.sizeof(Vec2fStruct) == 0x08
assert ctypes.sizeof(GamePositionStruct) == 0x0C
assert ctypes.sizeof(AgentStruct) == 0xC4
assert AgentStruct.agent_id.offset == 0x2C
assert AgentStruct.pos.offset == 0x74
assert AgentStruct.type.offset == 0x9C
assert ctypes.sizeof(AgentItemStruct) == 0xD4
assert ctypes.sizeof(AgentGadgetStruct) == 0xE4
assert ctypes.sizeof(DyeInfoStruct) == 0x03
assert ctypes.sizeof(ItemDataStruct) == 0x10
assert ctypes.sizeof(EquipmentStruct) == 0xD8
assert ctypes.sizeof(TagInfoStruct) == 0x06
assert ctypes.sizeof(VisibleEffectStruct) == 0x0C
assert ctypes.sizeof(AgentLivingStruct) == 0x1C4
assert AgentLivingStruct.allegiance.offset == 0x1B5

_agent_record_type = TypeVar("_agent_record_type", bound=AgentStruct)


@dataclass(frozen=True)
class AgentReference:
    """A lightweight reference to one current remote agent record."""

    agent_id: int
    address: int
    slot: int
    type_flags: int = 0
    kind: AgentKind = AgentKind.UNKNOWN
    allegiance: AgentAllegiance | None = None
    owner_id: int | None = None
    is_dead: bool | None = None

    @property
    def is_living(self) -> bool:
        """Return whether the native type flags identify a living agent."""

        return self.kind is AgentKind.LIVING

    @property
    def is_gadget(self) -> bool:
        """Return whether the native type flags identify a gadget."""

        return self.kind is AgentKind.GADGET

    @property
    def is_item(self) -> bool:
        """Return whether the native type flags identify an item."""

        return self.kind is AgentKind.ITEM

    @property
    def is_owned_item(self) -> bool:
        """Return whether an item has a non-zero native owner ID."""

        return self.is_item and bool(self.owner_id)


@dataclass(frozen=True)
class AgentArraySnapshot:
    """One bounded view of the native agent pointer table."""

    references: tuple[AgentReference, ...]
    reported_size: int
    reported_capacity: int
    scanned_slots: int
    non_null_slots: int
    invalid_pointer_slots: int
    zero_id_slots: int
    stale_slots: int
    unreadable_slots: int
    pointer_table_truncated: bool
    reference_limit_reached: bool

    @property
    def count(self) -> int:
        """Return the number of accepted current-agent references."""

        return len(self.references)

    @property
    def all(self) -> tuple[AgentReference, ...]:
        """Return all accepted references in native array order."""

        return self.references

    @property
    def truncated(self) -> bool:
        """Return whether either configured safety limit shortened the view."""

        return self.pointer_table_truncated or self.reference_limit_reached

    @property
    def living(self) -> tuple[AgentReference, ...]:
        """Return references classified as living agents."""

        return tuple(reference for reference in self.references if reference.is_living)

    @property
    def gadgets(self) -> tuple[AgentReference, ...]:
        """Return references classified as gadgets."""

        return tuple(reference for reference in self.references if reference.is_gadget)

    @property
    def items(self) -> tuple[AgentReference, ...]:
        """Return references classified as items."""

        return tuple(reference for reference in self.references if reference.is_item)

    @property
    def owned_items(self) -> tuple[AgentReference, ...]:
        """Return item references with a non-zero owner ID."""

        return tuple(
            reference for reference in self.references if reference.is_owned_item
        )

    @property
    def alive(self) -> tuple[AgentReference, ...]:
        """Return living references whose effects bitmap is not dead."""

        return tuple(
            reference
            for reference in self.living
            if reference.is_dead is False
        )

    @property
    def dead(self) -> tuple[AgentReference, ...]:
        """Return living references whose effects bitmap marks dead."""

        return tuple(
            reference
            for reference in self.living
            if reference.is_dead is True
        )

    def by_allegiance(
        self, allegiance: AgentAllegiance
    ) -> tuple[AgentReference, ...]:
        """Return living references with one native allegiance value."""

        return tuple(
            reference
            for reference in self.references
            if reference.allegiance == allegiance
        )

    @property
    def allies(self) -> tuple[AgentReference, ...]:
        """Return ally/non-attackable living references."""

        return self.by_allegiance(AgentAllegiance.ALLY_NON_ATTACKABLE)

    @property
    def neutral(self) -> tuple[AgentReference, ...]:
        """Return neutral living references."""

        return self.by_allegiance(AgentAllegiance.NEUTRAL)

    @property
    def enemies(self) -> tuple[AgentReference, ...]:
        """Return enemy living references."""

        return self.by_allegiance(AgentAllegiance.ENEMY)

    @property
    def spirit_pets(self) -> tuple[AgentReference, ...]:
        """Return spirit or pet living references."""

        return self.by_allegiance(AgentAllegiance.SPIRIT_PET)

    @property
    def minions(self) -> tuple[AgentReference, ...]:
        """Return minion living references."""

        return self.by_allegiance(AgentAllegiance.MINION)

    @property
    def npc_minipets(self) -> tuple[AgentReference, ...]:
        """Return NPC or minipet living references."""

        return self.by_allegiance(AgentAllegiance.NPC_MINIPET)

    @property
    def dead_allies(self) -> tuple[AgentReference, ...]:
        """Return dead living references with ally allegiance."""

        return tuple(
            reference
            for reference in self.allies
            if reference.is_dead is True
        )

    @property
    def dead_enemies(self) -> tuple[AgentReference, ...]:
        """Return dead living references with enemy allegiance."""

        return tuple(
            reference
            for reference in self.enemies
            if reference.is_dead is True
        )

    def GetAgentArray(self) -> list[int]:
        """Return all accepted agent identifiers in table order."""

        return [reference.agent_id for reference in self.references]

    def GetAllyArray(self) -> list[int]:
        """Return accepted ally identifiers."""

        return [reference.agent_id for reference in self.allies]

    def GetNeutralArray(self) -> list[int]:
        """Return accepted neutral identifiers."""

        return [reference.agent_id for reference in self.neutral]

    def GetEnemyArray(self) -> list[int]:
        """Return accepted enemy identifiers."""

        return [reference.agent_id for reference in self.enemies]

    def GetSpiritPetArray(self) -> list[int]:
        """Return accepted spirit/pet identifiers."""

        return [reference.agent_id for reference in self.spirit_pets]

    def GetMinionArray(self) -> list[int]:
        """Return accepted minion identifiers."""

        return [reference.agent_id for reference in self.minions]

    def GetNPCMinipetArray(self) -> list[int]:
        """Return accepted NPC/minipet identifiers."""

        return [reference.agent_id for reference in self.npc_minipets]

    def GetItemAgentArray(self) -> list[int]:
        """Return accepted item-agent identifiers."""

        return [reference.agent_id for reference in self.items]

    def GetOwnedItemAgentArray(self) -> list[int]:
        """Return accepted owned-item identifiers."""

        return [reference.agent_id for reference in self.owned_items]

    def GetGadgetAgentArray(self) -> list[int]:
        """Return accepted gadget identifiers."""

        return [reference.agent_id for reference in self.gadgets]

    def GetDeadAllyArray(self) -> list[int]:
        """Return accepted dead-ally identifiers."""

        return [reference.agent_id for reference in self.dead_allies]

    def GetDeadEnemyArray(self) -> list[int]:
        """Return accepted dead-enemy identifiers."""

        return [reference.agent_id for reference in self.dead_enemies]


class AgentArrayStruct(Structure):
    """A bounded external view of Reforged's ``AgentArrayStruct``.

    The native structure contains one ``GWArray<Agent*>`` header.  The
    external view keeps that exact header, while category methods delegate to
    the validated snapshot that produced this object.  ``raw_agents`` is an
    explicit materialization operation and is bounded by the owning reader's
    configured pointer limit.
    """

    _pack_ = 1
    _fields_ = [("agent_array", GWArray)]

    _owner: AgentArray | None = None
    _snapshot: AgentArraySnapshot | None = None

    def bind_external(
        self, owner: AgentArray, snapshot: AgentArraySnapshot
    ) -> AgentArrayStruct:
        """Attach the external reader and validated snapshot to this view."""

        self._owner = owner
        self._snapshot = snapshot
        return self

    @property
    def raw_agents(self) -> list[AgentStruct | None]:
        """Materialize accepted agent records in current table-slot order."""

        if self._owner is None or self._snapshot is None:
            return []
        records: list[AgentStruct | None] = []
        references_by_slot = {
            reference.slot: reference for reference in self._snapshot.references
        }
        for slot in range(self._snapshot.scanned_slots):
            reference = references_by_slot.get(slot)
            if reference is None:
                records.append(None)
                continue
            try:
                records.append(self._owner.read_agent(reference))
            except (OSError, StaleAgentReferenceError):
                records.append(None)
        return records

    def GetAgentByID(
        self, agent_id: int
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Return one complete validated record by agent identifier."""

        if self._owner is None:
            return None
        return self._owner.read_agent_by_id(agent_id, self._snapshot)

    def _ids(self, method_name: str) -> list[int]:
        if self._snapshot is None:
            return []
        method = getattr(self._snapshot, method_name)
        return cast(list[int], method())

    def GetAgentArray(self) -> list[int]:
        return self._ids("GetAgentArray")

    def GetAllyArray(self) -> list[int]:
        return self._ids("GetAllyArray")

    def GetNeutralArray(self) -> list[int]:
        return self._ids("GetNeutralArray")

    def GetEnemyArray(self) -> list[int]:
        return self._ids("GetEnemyArray")

    def GetSpiritPetArray(self) -> list[int]:
        return self._ids("GetSpiritPetArray")

    def GetMinionArray(self) -> list[int]:
        return self._ids("GetMinionArray")

    def GetNPCMinipetArray(self) -> list[int]:
        return self._ids("GetNPCMinipetArray")

    def GetItemAgentArray(self) -> list[int]:
        return self._ids("GetItemAgentArray")

    def GetOwnedItemAgentArray(self) -> list[int]:
        return self._ids("GetOwnedItemAgentArray")

    def GetGadgetAgentArray(self) -> list[int]:
        return self._ids("GetGadgetAgentArray")

    def GetDeadAllyArray(self) -> list[int]:
        return self._ids("GetDeadAllyArray")

    def GetDeadEnemyArray(self) -> list[int]:
        return self._ids("GetDeadEnemyArray")


assert ctypes.sizeof(AgentArrayStruct) == ctypes.sizeof(GWArray)


@dataclass(frozen=True)
class LivingAgentSnapshot:
    """Complete living-agent records captured during one refresh cycle.

    The records retain the complete native ``AgentLiving`` layout. This is a
    local snapshot: callers can query fields repeatedly without another
    process read until they request a new refresh.
    """

    generation: int
    captured_at_ns: int
    records: tuple[AgentLivingStruct, ...]
    stale_count: int
    unreadable_count: int

    @property
    def count(self) -> int:
        """Return the number of complete records captured."""

        return len(self.records)

    def get(self, agent_id: int) -> AgentLivingStruct | None:
        """Return one cached record by agent ID, if present."""

        return next(
            (record for record in self.records if int(record.agent_id) == agent_id),
            None,
        )

    @property
    def age_ms(self) -> float:
        """Return the local age of this snapshot in milliseconds."""

        return max(0.0, (time.perf_counter_ns() - self.captured_at_ns) / 1_000_000.0)


class AgentArray:
    """Resolve and traverse the native ``GWArray<Agent*>`` externally.

    The pointer table is read in one bounded operation. Candidate agent IDs
    are then read from the common native record, and the movement table is
    used as the native stale-pointer validity gate. Complete agent structures
    are materialized only through the explicit ``read_agent`` methods, never
    during an ordinary reference snapshot.
    """

    _RESOLVER = "agent.agent_array_addr"
    _AGENT_ID_OFFSET = 0x2C
    _OWNER_OFFSET = 0xC4
    _TYPE_OFFSET = 0x9C
    _EFFECTS_OFFSET = 0x13C
    _ALLEGIANCE_OFFSET = 0x1B5
    _MIN_REMOTE_ADDRESS = 0x10000
    _DEFAULT_MAX_POINTER_SLOTS = 4096
    _DEFAULT_MAX_REFERENCES = 300

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        agent_context: AccAgentContext,
        max_pointer_slots: int = _DEFAULT_MAX_POINTER_SLOTS,
        max_references: int = _DEFAULT_MAX_REFERENCES,
    ) -> None:
        """Create an agent-array reader for one connected client."""

        if max_pointer_slots <= 0:
            raise ValueError("max_pointer_slots must be positive.")
        if max_references <= 0:
            raise ValueError("max_references must be positive.")
        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._agent_context = agent_context
        self._max_pointer_slots = max_pointer_slots
        self._max_references = max_references
        self._array_address: int | None = None
        self._snapshot: AgentArraySnapshot | None = None
        self._living_snapshot: LivingAgentSnapshot | None = None
        self._living_generation = 0

    @property
    def max_pointer_slots(self) -> int:
        """Return the maximum number of target slots inspected per snapshot."""

        return self._max_pointer_slots

    @property
    def max_references(self) -> int:
        """Return the maximum number of accepted references returned."""

        return self._max_references

    @property
    def cached_array_address(self) -> int | None:
        """Return the cached native array address, if initialized."""

        return self._array_address

    @property
    def snapshot(self) -> AgentArraySnapshot | None:
        """Return the most recent validated pointer-table snapshot."""

        return self._snapshot

    def resolve_address(self, perf_counter: PerfCounter | None = None) -> int:
        """Return the stable native array address used by the resolver."""

        if self._array_address is None:
            return self.initialize(perf_counter)
        return self._array_address

    def initialize(self, perf_counter: PerfCounter | None = None) -> int:
        """Resolve and cache ``agent.agent_array_addr`` once."""

        if self._array_address is not None:
            return self._array_address
        if perf_counter is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
        else:
            with perf_counter.measure("agent_array.resolver"):
                result = self._patterns.resolve(self._RESOLVER, self._scanner)
        if not result.ok:
            detail = result.message or "the resolver returned no address"
            raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
        self._array_address = result.value
        return self._array_address

    def read(self, perf_counter: PerfCounter | None = None) -> AgentArraySnapshot | None:
        """Read a bounded set of current agent references.

        A client without an active ``AgentContext`` returns ``None``. A
        malformed live array raises an error with its target address so the
        caller cannot mistake it for an empty agent list.
        """

        if perf_counter is None:
            snapshot = self._read_snapshot(None)
        else:
            with perf_counter.measure("agent_array.read"):
                snapshot = self._read_snapshot(perf_counter)
        self._snapshot = snapshot
        self._living_snapshot = None
        return snapshot

    def read_context(
        self, perf_counter: PerfCounter | None = None
    ) -> AgentArrayStruct | None:
        """Return a source-shaped view bound to the latest validated snapshot."""

        snapshot = self.read(perf_counter)
        if snapshot is None:
            return None
        header = self._read_array_header(self.resolve_address(), "agent array")
        return AgentArrayStruct.from_buffer_copy(bytes(header)).bind_external(
            self, snapshot
        )

    def _current_snapshot(self) -> AgentArraySnapshot | None:
        """Use the cached snapshot, refreshing only when none exists."""

        return self._snapshot if self._snapshot is not None else self.read()

    def GetAgentByID(
        self, agent_id: int
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Return one complete validated record by agent identifier."""

        snapshot = self._current_snapshot()
        return self.read_agent_by_id(agent_id, snapshot)

    def _category_ids(self, method_name: str) -> list[int]:
        snapshot = self._current_snapshot()
        if snapshot is None:
            return []
        method = getattr(snapshot, method_name)
        return cast(list[int], method())

    def GetAgentArray(self) -> list[int]:
        return self._category_ids("GetAgentArray")

    def GetAllyArray(self) -> list[int]:
        return self._category_ids("GetAllyArray")

    def GetNeutralArray(self) -> list[int]:
        return self._category_ids("GetNeutralArray")

    def GetEnemyArray(self) -> list[int]:
        return self._category_ids("GetEnemyArray")

    def GetSpiritPetArray(self) -> list[int]:
        return self._category_ids("GetSpiritPetArray")

    def GetMinionArray(self) -> list[int]:
        return self._category_ids("GetMinionArray")

    def GetNPCMinipetArray(self) -> list[int]:
        return self._category_ids("GetNPCMinipetArray")

    def GetItemAgentArray(self) -> list[int]:
        return self._category_ids("GetItemAgentArray")

    def GetOwnedItemAgentArray(self) -> list[int]:
        return self._category_ids("GetOwnedItemAgentArray")

    def GetGadgetAgentArray(self) -> list[int]:
        return self._category_ids("GetGadgetAgentArray")

    def GetDeadAllyArray(self) -> list[int]:
        return self._category_ids("GetDeadAllyArray")

    def GetDeadEnemyArray(self) -> list[int]:
        return self._category_ids("GetDeadEnemyArray")

    @property
    def living_snapshot(self) -> LivingAgentSnapshot | None:
        """Return the most recently refreshed complete living snapshot."""

        return self._living_snapshot

    def invalidate_living_snapshot(self) -> None:
        """Discard cached living records without reading the target."""

        self._living_snapshot = None

    def refresh_living_agents(
        self, perf_counter: PerfCounter | None = None
    ) -> LivingAgentSnapshot | None:
        """Read and cache complete records for the current living references.

        The AgentArray is refreshed first. Each complete living record is then
        validated against the current pointer and movement tables before being
        copied locally. References that disappear during this refresh are
        counted and omitted rather than reused from an older snapshot.
        """

        refresh_context = (
            perf_counter.measure("agent_array.living_refresh")
            if perf_counter is not None
            else nullcontext()
        )
        with refresh_context:
            array_snapshot = self.read(perf_counter)
            if array_snapshot is None:
                self._living_snapshot = None
                return None
            records: list[AgentLivingStruct] = []
            stale_count = 0
            unreadable_count = 0
            for reference in array_snapshot.living:
                try:
                    record = self.read_agent(reference, perf_counter)
                except StaleAgentReferenceError:
                    stale_count += 1
                    continue
                except OSError:
                    unreadable_count += 1
                    continue
                if not isinstance(record, AgentLivingStruct):
                    continue
                records.append(record)
            self._living_generation += 1
            self._living_snapshot = LivingAgentSnapshot(
                generation=self._living_generation,
                captured_at_ns=time.perf_counter_ns(),
                records=tuple(records),
                stale_count=stale_count,
                unreadable_count=unreadable_count,
            )
            return self._living_snapshot

    def get_living_agent(
        self,
        agent_id: int,
        refresh: bool = False,
        perf_counter: PerfCounter | None = None,
    ) -> AgentLivingStruct | None:
        """Return one complete cached living record by ID.

        Set ``refresh`` to capture a new complete living snapshot first. A
        missing cache is also refreshed automatically for convenience.
        """

        if agent_id <= 0:
            raise ValueError("agent_id must be positive.")
        if refresh or self._living_snapshot is None:
            snapshot = self.refresh_living_agents(perf_counter)
        else:
            snapshot = self._living_snapshot
        return snapshot.get(agent_id) if snapshot is not None else None

    def _read_snapshot(self, perf_counter: PerfCounter | None) -> AgentArraySnapshot | None:
        """Read one snapshot, optionally recording each traversal stage."""

        array_address = self.resolve_address(perf_counter)
        pointer_context = (
            perf_counter.measure("agent_array.pointer_table")
            if perf_counter is not None
            else nullcontext()
        )
        with pointer_context:
            agent_array = self._read_array_header(array_address, "agent array")
            reported_size = int(agent_array.m_size)
            reported_capacity = int(agent_array.m_capacity)
            if reported_size > reported_capacity:
                raise RuntimeError(
                    f"Agent array at 0x{array_address:08X} reports size "
                    f"{reported_size} greater than capacity {reported_capacity}."
                )
            pointer_count = min(reported_size, self._max_pointer_slots)
            pointer_table_truncated = reported_size > self._max_pointer_slots
            pointers = self._read_pointer_values(
                    agent_array,
                    pointer_count,
                    array_address,
                    "agent pointer table",
            )

        movement_context = (
            perf_counter.measure("agent_array.context_read")
            if perf_counter is not None
            else nullcontext()
        )
        with movement_context:
            context = self._agent_context.read()
        if context is None:
            return None
        movement_array = context.agent_movement_array
        movement_count = min(
            int(movement_array.m_size), self._max_pointer_slots
        ) if int(movement_array.m_size) <= int(movement_array.m_capacity) else 0
        movement_context = (
            perf_counter.measure("agent_array.movement_table")
            if perf_counter is not None
            else nullcontext()
        )
        with movement_context:
            movement_pointers = self._read_pointer_values(
                movement_array,
                movement_count,
                context.remote_address or 0,
                "agent movement table",
                allow_null_buffer=True,
            )

        references: list[AgentReference] = []
        non_null_slots = 0
        invalid_pointer_slots = 0
        zero_id_slots = 0
        stale_slots = 0
        unreadable_slots = 0
        scanned_slots = 0
        stopped_by_reference_limit = False

        classification_context = (
            perf_counter.measure("agent_array.classification")
            if perf_counter is not None
            else nullcontext()
        )
        with classification_context:
            for slot, pointer in enumerate(pointers):
                scanned_slots += 1
                if pointer == 0:
                    continue
                if pointer < self._MIN_REMOTE_ADDRESS:
                    invalid_pointer_slots += 1
                    continue
                non_null_slots += 1
                try:
                    agent_id = int.from_bytes(
                        self._reader.read(pointer + self._AGENT_ID_OFFSET, 4),
                        "little",
                    )
                except OSError:
                    unreadable_slots += 1
                    continue
                if agent_id == 0:
                    zero_id_slots += 1
                    continue
                if agent_id >= len(movement_pointers) or not movement_pointers[agent_id]:
                    stale_slots += 1
                    continue
                if len(references) >= self._max_references:
                    stopped_by_reference_limit = True
                    break
                type_flags = 0
                kind = AgentKind.UNKNOWN
                allegiance: AgentAllegiance | None = None
                owner_id: int | None = None
                is_dead: bool | None = None
                try:
                    type_flags = int.from_bytes(
                        self._reader.read(pointer + self._TYPE_OFFSET, 4),
                        "little",
                    )
                    kind = self._kind_from_type_flags(type_flags)
                    if kind is AgentKind.ITEM:
                        owner_id = int.from_bytes(
                            self._reader.read(pointer + self._OWNER_OFFSET, 4),
                            "little",
                        )
                    elif kind is AgentKind.LIVING:
                        raw_allegiance = self._reader.read(
                            pointer + self._ALLEGIANCE_OFFSET, 1
                        )
                        allegiance_value = int.from_bytes(raw_allegiance, "little")
                        try:
                            allegiance = AgentAllegiance(allegiance_value)
                        except ValueError:
                            allegiance = None
                        effects = int.from_bytes(
                            self._reader.read(pointer + self._EFFECTS_OFFSET, 4),
                            "little",
                        )
                        is_dead = bool(effects & 0x0010)
                except OSError:
                    unreadable_slots += 1
                references.append(
                    AgentReference(
                        agent_id,
                        pointer,
                        slot,
                        type_flags,
                        kind,
                        allegiance,
                        owner_id,
                        is_dead,
                    )
                )

        return AgentArraySnapshot(
            references=tuple(references),
            reported_size=reported_size,
            reported_capacity=reported_capacity,
            scanned_slots=scanned_slots,
            non_null_slots=non_null_slots,
            invalid_pointer_slots=invalid_pointer_slots,
            zero_id_slots=zero_id_slots,
            stale_slots=stale_slots,
            unreadable_slots=unreadable_slots,
            pointer_table_truncated=pointer_table_truncated,
            reference_limit_reached=stopped_by_reference_limit,
        )

    def read_agent(
        self, reference: AgentReference, perf_counter: PerfCounter | None = None
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct:
        """Read one complete typed agent record for a selected reference."""

        if reference.address < self._MIN_REMOTE_ADDRESS:
            raise ValueError("The agent reference address is not valid.")
        validation_context = (
            perf_counter.measure("agent_array.reference_validation")
            if perf_counter is not None
            else nullcontext()
        )
        with validation_context:
            self._validate_reference_current(reference)
        record_type: type[AgentStruct]
        if reference.kind is AgentKind.LIVING:
            record_type = AgentLivingStruct
        elif reference.kind is AgentKind.ITEM:
            record_type = AgentItemStruct
        elif reference.kind is AgentKind.GADGET:
            record_type = AgentGadgetStruct
        else:
            record_type = AgentStruct
        if perf_counter is None:
            record = self._read_record(reference.address, record_type)
        else:
            with perf_counter.measure("agent_array.agent_record"):
                record = self._read_record(reference.address, record_type)
        if int(record.agent_id) != reference.agent_id:
            raise StaleAgentReferenceError(
                f"Agent reference changed at 0x{reference.address:08X}: "
                f"expected ID {reference.agent_id}, read {int(record.agent_id)}."
            )
        return record

    def _validate_reference_current(self, reference: AgentReference) -> None:
        """Confirm that a snapshot reference is still current in the target.

        The pointer table and movement table can change independently of a
        previously returned snapshot. This check narrows that race window
        before a complete record is materialized; ``read_agent`` still
        revalidates the record's ID after the structure read.
        """

        array_address = self.resolve_address()
        agent_array = self._read_array_header(array_address, "agent array")
        reported_size = int(agent_array.m_size)
        reported_capacity = int(agent_array.m_capacity)
        if reported_size > reported_capacity:
            raise RuntimeError(
                f"Agent array at 0x{array_address:08X} reports size "
                f"{reported_size} greater than capacity {reported_capacity}."
            )
        if reference.slot < 0 or reference.slot >= reported_size:
            raise StaleAgentReferenceError(
                f"Agent reference ID {reference.agent_id} is stale: "
                f"slot {reference.slot} is outside the current array size "
                f"{reported_size}."
            )
        if reference.slot >= self._max_pointer_slots:
            raise RuntimeError(
                f"Agent reference ID {reference.agent_id} is outside the "
                "configured pointer-table validation limit."
            )
        current_pointer = self._read_pointer_at(
            agent_array,
            reference.slot,
            array_address,
            "agent pointer table",
        )
        if current_pointer != reference.address:
            raise StaleAgentReferenceError(
                f"Agent reference ID {reference.agent_id} is stale: "
                f"slot {reference.slot} now points to 0x{current_pointer:08X}, "
                f"not 0x{reference.address:08X}."
            )

        context = self._agent_context.read()
        if context is None:
            raise StaleAgentReferenceError(
                f"Agent reference ID {reference.agent_id} is stale: "
                "the movement context is unavailable."
            )
        movement_array = context.agent_movement_array
        movement_size = int(movement_array.m_size)
        movement_capacity = int(movement_array.m_capacity)
        if movement_size > movement_capacity:
            raise RuntimeError(
                f"Movement array at 0x{context.remote_address or 0:08X} "
                f"reports size {movement_size} greater than capacity "
                f"{movement_capacity}."
            )
        if reference.agent_id >= movement_size:
            raise StaleAgentReferenceError(
                f"Agent reference ID {reference.agent_id} is stale: "
                f"movement array size is {movement_size}."
            )
        movement_pointer = self._read_pointer_at(
            movement_array,
            reference.agent_id,
            context.remote_address or 0,
            "agent movement table",
            allow_null_buffer=True,
        )
        if movement_pointer == 0:
            raise StaleAgentReferenceError(
                f"Agent reference ID {reference.agent_id} is stale: "
                "its movement entry is null."
            )

    def read_agent_by_id(
        self, agent_id: int, snapshot: AgentArraySnapshot | None = None
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Find an ID in one snapshot and lazily read its complete record."""

        if agent_id <= 0:
            raise ValueError("agent_id must be positive.")
        current = snapshot if snapshot is not None else self.read()
        if current is None:
            return None
        reference = next(
            (value for value in current.references if value.agent_id == agent_id),
            None,
        )
        return self.read_agent(reference) if reference is not None else None

    def _read_record(
        self, address: int, record_type: type[_agent_record_type]
    ) -> _agent_record_type:
        """Read one fixed-width record and bind its remote address."""

        raw = self._reader.read(address, ctypes.sizeof(record_type))
        record = record_type.from_buffer_copy(raw)
        return cast(_agent_record_type, record.bind_reader(self._reader, address))

    def _read_array_header(self, address: int, description: str) -> GWArray:
        """Read and decode one fixed-width target array header."""

        try:
            raw = self._reader.read(address, ctypes.sizeof(GWArray))
        except OSError as error:
            raise OSError(
                error.errno,
                f"Could not read {description} header at 0x{address:08X}: {error}",
            ) from error
        return GWArray.from_buffer_copy(raw)

    def _read_pointer_values(
        self,
        array: GWArray,
        count: int,
        owner_address: int,
        description: str,
        allow_null_buffer: bool = False,
    ) -> tuple[int, ...]:
        """Read a bounded target pointer array in one bulk operation."""

        if count <= 0:
            return ()
        buffer_address = int(array.m_buffer)
        if buffer_address < self._MIN_REMOTE_ADDRESS:
            if allow_null_buffer:
                return (0,) * count
            raise RuntimeError(
                f"{description} at 0x{owner_address:08X} has a null buffer."
            )
        raw = self._reader.read(buffer_address, count * 4)
        if len(raw) != count * 4:
            raise OSError(
                299,
                f"{description} returned 0x{len(raw):X} of 0x{count * 4:X} "
                f"bytes at 0x{buffer_address:08X}.",
            )
        return tuple(
            int.from_bytes(raw[index : index + 4], "little")
            for index in range(0, len(raw), 4)
        )

    def _read_pointer_at(
        self,
        array: GWArray,
        index: int,
        owner_address: int,
        description: str,
        allow_null_buffer: bool = False,
    ) -> int:
        """Read one fixed-width pointer from a validated target array."""

        if index < 0 or index >= int(array.m_size):
            raise IndexError(index)
        buffer_address = int(array.m_buffer)
        if buffer_address < self._MIN_REMOTE_ADDRESS:
            if allow_null_buffer:
                return 0
            raise RuntimeError(
                f"{description} at 0x{owner_address:08X} has a null buffer."
            )
        raw = self._reader.read(buffer_address + index * 4, 4)
        if len(raw) != 4:
            raise OSError(
                299,
                f"{description} returned 0x{len(raw):X} of 0x4 bytes at "
                f"0x{buffer_address + index * 4:08X}.",
            )
        return int.from_bytes(raw, "little")

    @staticmethod
    def _kind_from_type_flags(type_flags: int) -> AgentKind:
        """Apply the native gadget/item/living classification order."""

        if type_flags & AgentType.GADGET:
            return AgentKind.GADGET
        if type_flags & AgentType.ITEM:
            return AgentKind.ITEM
        if type_flags & AgentType.LIVING:
            return AgentKind.LIVING
        return AgentKind.UNKNOWN


def get() -> AgentArraySnapshot | None:
    """Read the agent references from the current selected client."""

    from ..client import current_client

    client = current_client()
    return client.read_agent_array() if client is not None else None
