"""Bounded external traversal of Guild Wars' native agent pointer table."""

from __future__ import annotations

from ..enums_src.game_data_enums import Allegiance
from ..helpers.target_struct import Describable, TargetStruct

import ctypes
from dataclasses import dataclass
from enum import IntFlag
from ctypes import c_float, c_uint8, c_uint16, c_uint32
from typing import Callable, Iterator, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .acc_agent_context import AccAgentContext
from .gw_array import GWArray, GWArrayView, RemoteMemoryReader
from .gw_list import GWLinkStruct, GWListStruct, RemoteGWListView


class _memory_reader(RemoteMemoryReader, Protocol):
    """The read-only operation needed by the agent-array reader.

    An annotation only — the same declaration every ported context module carries
    (``game_context``, ``world_context``, ``item_context``, …). It names the reader protocol the
    source's own structures are read through here; it has no behaviour and nothing calls it.
    """


class AgentType(IntFlag):
    """The native type masks stored in the common agent record."""

    LIVING = 0xDB
    GADGET = 0x200
    ITEM = 0x400


@dataclass(slots=True, repr=False)
class DyeInfo(Describable):
    """Python value record corresponding to Reforged's ``DyeInfo``."""

    dye_tint: int
    dye1: int
    dye2: int
    dye3: int
    dye4: int


@dataclass(slots=True)
class ItemData:
    """Python value record corresponding to Reforged's ``ItemData``."""

    model_file_id: int
    type: int
    dye: DyeInfo
    value: int
    interaction: int


@dataclass(slots=True)
class EquipmentItemsUnion:
    """Snapshot of all nine equipment item slots and named overlays."""

    items: tuple[
        ItemData,
        ItemData,
        ItemData,
        ItemData,
        ItemData,
        ItemData,
        ItemData,
        ItemData,
        ItemData,
    ]
    weapon: ItemData
    offhand: ItemData
    chest: ItemData
    legs: ItemData
    head: ItemData
    feet: ItemData
    hands: ItemData
    costume_body: ItemData
    costume_head: ItemData


@dataclass(slots=True)
class EquipmentItemIDsUnion:
    """Snapshot of all nine equipment item IDs and named overlays."""

    item_ids: tuple[int, int, int, int, int, int, int, int, int]
    item_id_weapon: int
    item_id_offhand: int
    item_id_chest: int
    item_id_legs: int
    item_id_head: int
    item_id_feet: int
    item_id_hands: int
    item_id_costume_body: int
    item_id_costume_head: int


@dataclass(slots=True)
class Equipment:
    """Detached Python snapshot of the native equipment record."""

    vtable: int
    h0004: int
    h0008: int
    h000C: int
    h0018: int
    left_hand_map: int
    right_hand_map: int
    head_map: int
    shield_map: int
    items_union: EquipmentItemsUnion
    ids_union: EquipmentItemIDsUnion
    left_hand: ItemData | None
    right_hand: ItemData | None
    shield: ItemData | None


@dataclass(slots=True, repr=False)
class TagInfo(Describable):
    """Detached Python snapshot of the native tag record."""

    guild_id: int
    primary: int
    secondary: int
    level: int


@dataclass(slots=True)
class VisibleEffect:
    """Detached Python snapshot of one visible effect entry."""

    unk: int
    id: int
    has_ended: int


#: ``Vec2f`` and ``GamePos`` are Reforged's, from ``native_src/internals/types.py`` — the file the
#: agent records' own fields are declared with (``AgentStruct.terrain_normal`` is a ``Vec3f``,
#: ``velocity`` a ``Vec2f``, ``pos`` a ``GamePos``; ``AgentContext.py:428,431,442``). This module
#: used to declare two look-alikes of its own, ``Vec2fStruct`` and ``GamePositionStruct``, because
#: that file had never been ported; it is ported now (``py4gw/internals/types.py``) and they are
#: gone.
from ..internals.types import GamePos, Vec2f, Vec3f


@dataclass(slots=True)
class AgentNative:
    """Detached common-agent record used by Reforged's ``snapshot`` method."""

    h0004: int
    h0008: int
    h000C: list[int]
    timer: int
    timer2: int
    agent_id: int
    z: float
    width1: float
    height1: float
    width2: float
    height2: float
    width3: float
    height3: float
    rotation_angle: float
    rotation_cos: float
    rotation_sin: float
    name_properties: int
    ground: int
    h0060: int
    terrain_normal: Vec3f
    h0070: list[int]
    pos: GamePos
    h0080: list[int]
    name_tag_x: float
    name_tag_y: float
    name_tag_z: float
    visual_effects: int
    h0092: int
    h0094: list[int]
    type: int
    velocity: Vec2f
    h00A8: int
    rotation_cos2: float
    rotation_sin2: float
    h00B4: list[int]
    vtable: int
    is_item_type: bool
    is_gadget_type: bool
    is_living_type: bool
    _item_agent: AgentItem | None
    _gadget_agent: AgentGadget | None
    _living_agent: AgentLiving | None

    def GetAsAgentItem(self) -> AgentItem | None:
        """Return the item snapshot captured with this common record."""

        return self._item_agent

    def GetAsAgentGadget(self) -> AgentGadget | None:
        """Return the gadget snapshot captured with this common record."""

        return self._gadget_agent

    def GetAsAgentLiving(self) -> AgentLiving | None:
        """Return the living snapshot captured with this common record."""

        return self._living_agent


@dataclass(slots=True)
class AgentLiving:
    """Detached living-agent fields and derived values from Reforged."""

    owner: int
    h00C8: int
    h00CC: int
    h00D0: int
    h00D4: list[int]
    animation_type: float
    h00E4: list[int]
    weapon_attack_speed: float
    attack_speed_modifier: float
    player_number: int
    agent_model_type: int
    transmog_npc_id: int
    h0100: int
    h0104: int
    h010C: int
    primary: int
    secondary: int
    level: int
    team_id: int
    h0112: list[int]
    h0114: int
    energy_regen: float
    h011C: int
    energy: float
    max_energy: int
    h0128: int
    hp_pips: float
    h0130: int
    hp: float
    max_hp: int
    effects: int
    h0140: int
    hex: int
    h0145: list[int]
    model_state: int
    type_map: int
    h0160: list[int]
    in_spirit_range: int
    h0180: int
    login_number: int
    animation_speed: float
    animation_code: int
    animation_id: int
    h0194: list[int]
    dagger_status: int
    allegiance: int
    weapon_type: int
    skill: int
    h01BA: int
    weapon_item_type: int
    offhand_item_type: int
    weapon_item_id: int
    offhand_item_id: int
    equipment: Equipment | None
    tags: TagInfo | None
    visible_effects: list[VisibleEffect]
    is_bleeding: bool
    is_conditioned: bool
    is_used_corpse: bool
    is_crippled: bool
    is_dead: bool
    is_deep_wounded: bool
    is_poisoned: bool
    is_enchanted: bool
    is_degen_hexed: bool
    is_hexed: bool
    is_weapon_spelled: bool
    is_in_combat_stance: bool
    has_quest: bool
    is_dead_by_type_map: bool
    is_exploitable: bool
    is_female: bool
    has_boss_glow: bool
    is_hiding_cape: bool
    can_be_viewed_in_party_window: bool
    is_spawned: bool
    is_being_observed: bool
    is_knocked_down: bool
    is_moving: bool
    is_attacking: bool
    is_casting: bool
    is_idle: bool
    is_alive: bool
    is_player: bool
    is_npc: bool


@dataclass(slots=True)
class AgentItem:
    """Detached item-agent fields from Reforged."""

    owner: int
    item_id: int
    h00CC: int
    extra_type: int


@dataclass(slots=True)
class AgentGadget:
    """Detached gadget-agent fields from Reforged."""

    h00C4: int
    h00C8: int
    extra_type: int
    gadget_id: int
    h00D4: tuple[int, int, int, int]


class AgentStruct(TargetStruct):
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
        ("terrain_normal", Vec3f),
        ("h0070", c_uint8 * 4),
        ("pos", GamePos),
        ("h0080", c_uint8 * 4),
        ("name_tag_x", c_float),
        ("name_tag_y", c_float),
        ("name_tag_z", c_float),
        ("visual_effects", c_uint16),
        ("h0092", c_uint16),
        ("h0094", c_uint32 * 2),
        ("type", c_uint32),
        ("velocity", Vec2f),
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
        if self._remote_reader is not None and self._remote_address is not None:
            raw = self._remote_reader.read(
                self._remote_address, ctypes.sizeof(AgentItemStruct)
            )
            value = AgentItemStruct.from_buffer_copy(raw)
            value.bind_reader(self._remote_reader, self._remote_address)
        else:
            value = AgentItemStruct.from_buffer_copy(bytes(self))
        return cast(AgentItemStruct, value)

    def GetAsAgentGadget(self) -> AgentGadgetStruct | None:
        """Return this record as a gadget record when its type permits it."""

        if not self.is_gadget_type:
            return None
        if isinstance(self, AgentGadgetStruct):
            return self
        if self._remote_reader is not None and self._remote_address is not None:
            raw = self._remote_reader.read(
                self._remote_address, ctypes.sizeof(AgentGadgetStruct)
            )
            value = AgentGadgetStruct.from_buffer_copy(raw)
            value.bind_reader(self._remote_reader, self._remote_address)
        else:
            value = AgentGadgetStruct.from_buffer_copy(bytes(self))
        return cast(AgentGadgetStruct, value)

    def GetAsAgentLiving(self) -> AgentLivingStruct | None:
        """Return this record as a living record when its type permits it."""

        if not self.is_living_type:
            return None
        if isinstance(self, AgentLivingStruct):
            return self
        if self._remote_reader is not None and self._remote_address is not None:
            raw = self._remote_reader.read(
                self._remote_address, ctypes.sizeof(AgentLivingStruct)
            )
            value = AgentLivingStruct.from_buffer_copy(raw)
            value.bind_reader(self._remote_reader, self._remote_address)
        else:
            value = AgentLivingStruct.from_buffer_copy(bytes(self))
        return cast(AgentLivingStruct, value)

    def snapshot(self) -> AgentNative:
        """Copy this common record and its matching typed record to values."""

        item = self.GetAsAgentItem()
        gadget = self.GetAsAgentGadget()
        living = self.GetAsAgentLiving()
        return AgentNative(
            h0004=int(self.h0004),
            h0008=int(self.h0008),
            h000C=[int(value) for value in self.h000C],
            timer=int(self.timer),
            timer2=int(self.timer2),
            agent_id=int(self.agent_id),
            z=float(self.z),
            width1=float(self.width1),
            height1=float(self.height1),
            width2=float(self.width2),
            height2=float(self.height2),
            width3=float(self.width3),
            height3=float(self.height3),
            rotation_angle=float(self.rotation_angle),
            rotation_cos=float(self.rotation_cos),
            rotation_sin=float(self.rotation_sin),
            name_properties=int(self.name_properties),
            ground=int(self.ground),
            h0060=int(self.h0060),
            terrain_normal=Vec3f(
                float(self.terrain_normal.x),
                float(self.terrain_normal.y),
                float(self.terrain_normal.z),
            ),
            h0070=[int(value) for value in self.h0070],
            pos=self.pos,
            h0080=[int(value) for value in self.h0080],
            name_tag_x=float(self.name_tag_x),
            name_tag_y=float(self.name_tag_y),
            name_tag_z=float(self.name_tag_z),
            visual_effects=int(self.visual_effects),
            h0092=int(self.h0092),
            h0094=[int(value) for value in self.h0094],
            type=int(self.type),
            velocity=Vec2f(float(self.velocity.x), float(self.velocity.y)),
            h00A8=int(self.h00A8),
            rotation_cos2=float(self.rotation_cos2),
            rotation_sin2=float(self.rotation_sin2),
            h00B4=[int(value) for value in self.h00B4],
            vtable=self.vtable,
            is_item_type=self.is_item_type,
            is_gadget_type=self.is_gadget_type,
            is_living_type=self.is_living_type,
            _item_agent=item.snapshot_item() if item is not None else None,
            _gadget_agent=gadget.snapshot_gadget() if gadget is not None else None,
            _living_agent=living.snapshot_living() if living is not None else None,
        )


class AgentItemStruct(AgentStruct):
    """The complete native item-agent record (0xD4 bytes)."""

    _pack_ = 1
    _fields_ = [
        ("owner", c_uint32),
        ("item_id", c_uint32),
        ("h00CC", c_uint32),
        ("extra_type", c_uint32),
    ]

    def snapshot_item(self) -> AgentItem:
        """Copy item-specific fields to Reforged's value record."""

        return AgentItem(
            owner=int(self.owner),
            item_id=int(self.item_id),
            h00CC=int(self.h00CC),
            extra_type=int(self.extra_type),
        )


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

    def snapshot_gadget(self) -> AgentGadget:
        """Copy gadget-specific fields to Reforged's value record."""

        return AgentGadget(
            h00C4=int(self.h00C4),
            h00C8=int(self.h00C8),
            extra_type=int(self.extra_type),
            gadget_id=int(self.gadget_id),
            h00D4=(
                int(self.h00D4[0]),
                int(self.h00D4[1]),
                int(self.h00D4[2]),
                int(self.h00D4[3]),
            ),
        )


class DyeInfoStruct(TargetStruct):
    """Packed native dye information embedded in equipment items."""

    _pack_ = 1
    _fields_ = [
        ("dye_tint", c_uint8),
        ("dye1", c_uint8, 4),
        ("dye2", c_uint8, 4),
        ("dye3", c_uint8, 4),
        ("dye4", c_uint8, 4),
    ]

    def snapshot(self) -> DyeInfo:
        """Copy the packed bit fields into Reforged's value record."""

        return DyeInfo(
            dye_tint=int(self.dye_tint),
            dye1=int(self.dye1),
            dye2=int(self.dye2),
            dye3=int(self.dye3),
            dye4=int(self.dye4),
        )


class ItemDataStruct(TargetStruct):
    """The native C++ 0x10-byte embedded equipment item record."""

    _pack_ = 1
    _fields_ = [
        ("model_file_id", c_uint32),
        ("type", c_uint8),
        ("dye", DyeInfoStruct),
        ("value", c_uint32),
        ("interaction", c_uint32),
    ]

    def snapshot(self) -> ItemData:
        """Copy the native record to Reforged's Python value record."""

        return ItemData(
            model_file_id=int(self.model_file_id),
            type=int(self.type),
            dye=self.dye.snapshot(),
            value=int(self.value),
            interaction=int(self.interaction),
        )


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

    def snapshot(self) -> EquipmentItemsUnion:
        """Copy all equipment item slots and named union overlays."""

        return EquipmentItemsUnion(
            items=tuple(item.snapshot() for item in self.items),
            weapon=self.weapon.snapshot(),
            offhand=self.offhand.snapshot(),
            chest=self.chest.snapshot(),
            legs=self.legs.snapshot(),
            head=self.head.snapshot(),
            feet=self.feet.snapshot(),
            hands=self.hands.snapshot(),
            costume_body=self.costume_body.snapshot(),
            costume_head=self.costume_head.snapshot(),
        )


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

    def snapshot(self) -> EquipmentItemIDsUnion:
        """Copy the item ID array and all named union overlays."""

        return EquipmentItemIDsUnion(
            item_ids=(
                int(self.item_ids[0]),
                int(self.item_ids[1]),
                int(self.item_ids[2]),
                int(self.item_ids[3]),
                int(self.item_ids[4]),
                int(self.item_ids[5]),
                int(self.item_ids[6]),
                int(self.item_ids[7]),
                int(self.item_ids[8]),
            ),
            item_id_weapon=int(self.item_id_weapon),
            item_id_offhand=int(self.item_id_offhand),
            item_id_chest=int(self.item_id_chest),
            item_id_legs=int(self.item_id_legs),
            item_id_head=int(self.item_id_head),
            item_id_feet=int(self.item_id_feet),
            item_id_hands=int(self.item_id_hands),
            item_id_costume_body=int(self.item_id_costume_body),
            item_id_costume_head=int(self.item_id_costume_head),
        )


class EquipmentStruct(TargetStruct):
    """The native 0xD8-byte equipment record."""

    _pack_ = 1
    _fields_ = [
        ("vtable", c_uint32),
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

    def snapshot(self) -> Equipment:
        """Copy the full equipment record, including selected hand items."""

        left_hand = self.left_hand
        right_hand = self.right_hand
        shield = self.shield
        return Equipment(
            vtable=int(self.vtable),
            h0004=int(self.h0004),
            h0008=int(self.h0008),
            h000C=int(self.h000C),
            h0018=int(self.h0018),
            left_hand_map=int(self.left_hand_map),
            right_hand_map=int(self.right_hand_map),
            head_map=int(self.head_map),
            shield_map=int(self.shield_map),
            items_union=self.items_union.snapshot(),
            ids_union=self.ids_union.snapshot(),
            left_hand=left_hand.snapshot() if left_hand is not None else None,
            right_hand=right_hand.snapshot() if right_hand is not None else None,
            shield=shield.snapshot() if shield is not None else None,
        )


class TagInfoStruct(TargetStruct):
    """The native compact living-agent tag record."""

    _pack_ = 1
    _fields_ = [
        ("guild_id", c_uint16),
        ("primary", c_uint8),
        ("secondary", c_uint8),
        ("level", c_uint16),
    ]

    def snapshot(self) -> TagInfo:
        """Copy the packed tag fields into Reforged's value record."""

        return TagInfo(
            guild_id=int(self.guild_id),
            primary=int(self.primary),
            secondary=int(self.secondary),
            level=int(self.level),
        )


class VisibleEffectStruct(TargetStruct):
    """One native visible effect entry (0x0C bytes)."""

    _pack_ = 1
    _fields_ = [
        ("unk", c_uint32),
        ("id", c_uint32),
        ("has_ended", c_uint32),
    ]

    @property
    def effect_id(self) -> int:
        """Return the effect identifier under Stealth's descriptive alias."""

        return int(self.id)

    @property
    def is_active(self) -> bool:
        """Return whether the target effect has not entered its end state."""

        return int(self.has_ended) == 0

    def snapshot(self) -> VisibleEffect:
        """Copy this record to Reforged's Python value form."""

        return VisibleEffect(
            unk=int(self.unk), id=int(self.id), has_ended=int(self.has_ended)
        )


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
    def allegiance_enum(self) -> Allegiance | None:
        """Return the known allegiance enum, if the value is recognized."""

        try:
            return Allegiance(int(self.allegiance))
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
        """Return the source diagnostic label for the current corpse state."""

        if self.is_alive:
            return "alive"
        if self.is_used_corpse:
            return "used_corpse"
        return "exploitable"

    @property
    def corpse_exploit_signature(self) -> tuple[int, ...]:
        """Return the source fields used to compare corpse states."""

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

    def snapshot_living(self) -> AgentLiving:
        """Copy every maintained living field and derived property."""

        equipment = self.equipment
        tags = self.tags
        visible_effects = self.visible_effects
        return AgentLiving(
            owner=int(self.owner),
            h00C8=int(self.h00C8),
            h00CC=int(self.h00CC),
            h00D0=int(self.h00D0),
            h00D4=[int(value) for value in self.h00D4],
            animation_type=float(self.animation_type),
            h00E4=[int(value) for value in self.h00E4],
            weapon_attack_speed=float(self.weapon_attack_speed),
            attack_speed_modifier=float(self.attack_speed_modifier),
            player_number=int(self.player_number),
            agent_model_type=int(self.agent_model_type),
            transmog_npc_id=int(self.transmog_npc_id),
            h0100=int(self.h0100),
            h0104=int(self.h0104),
            h010C=int(self.h010C),
            primary=int(self.primary),
            secondary=int(self.secondary),
            level=int(self.level),
            team_id=int(self.team_id),
            h0112=[int(value) for value in self.h0112],
            h0114=int(self.h0114),
            energy_regen=float(self.energy_regen),
            h011C=int(self.h011C),
            energy=float(self.energy),
            max_energy=int(self.max_energy),
            h0128=int(self.h0128),
            hp_pips=float(self.hp_pips),
            h0130=int(self.h0130),
            hp=float(self.hp),
            max_hp=int(self.max_hp),
            effects=int(self.effects),
            h0140=int(self.h0140),
            hex=int(self.hex),
            h0145=[int(value) for value in self.h0145],
            model_state=int(self.model_state),
            type_map=int(self.type_map),
            h0160=[int(value) for value in self.h0160],
            in_spirit_range=int(self.in_spirit_range),
            h0180=int(self.h0180),
            login_number=int(self.login_number),
            animation_speed=float(self.animation_speed),
            animation_code=int(self.animation_code),
            animation_id=int(self.animation_id),
            h0194=[int(value) for value in self.h0194],
            dagger_status=int(self.dagger_status),
            allegiance=int(self.allegiance),
            weapon_type=int(self.weapon_type),
            skill=int(self.skill),
            h01BA=int(self.h01BA),
            weapon_item_type=int(self.weapon_item_type),
            offhand_item_type=int(self.offhand_item_type),
            weapon_item_id=int(self.weapon_item_id),
            offhand_item_id=int(self.offhand_item_id),
            equipment=equipment.snapshot() if equipment is not None else None,
            tags=tags.snapshot() if tags is not None else None,
            visible_effects=[effect.snapshot() for effect in visible_effects],
            is_bleeding=self.is_bleeding,
            is_conditioned=self.is_conditioned,
            is_used_corpse=self.is_used_corpse,
            is_crippled=self.is_crippled,
            is_dead=self.is_dead,
            is_deep_wounded=self.is_deep_wounded,
            is_poisoned=self.is_poisoned,
            is_enchanted=self.is_enchanted,
            is_degen_hexed=self.is_degen_hexed,
            is_hexed=self.is_hexed,
            is_weapon_spelled=self.is_weapon_spelled,
            is_in_combat_stance=self.is_in_combat_stance,
            has_quest=self.has_quest,
            is_dead_by_type_map=self.is_dead_by_type_map,
            is_exploitable=self.is_exploitable,
            is_female=self.is_female,
            has_boss_glow=self.has_boss_glow,
            is_hiding_cape=self.is_hiding_cape,
            can_be_viewed_in_party_window=self.can_be_viewed_in_party_window,
            is_spawned=self.is_spawned,
            is_being_observed=self.is_being_observed,
            is_knocked_down=self.is_knocked_down,
            is_moving=self.is_moving,
            is_attacking=self.is_attacking,
            is_casting=self.is_casting,
            is_idle=self.is_idle,
            is_alive=self.is_alive,
            is_player=self.is_player,
            is_npc=self.is_npc,
        )


assert ctypes.sizeof(Vec2f) == 0x08
assert ctypes.sizeof(GamePos) == 0x0C
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


class AgentArrayStruct(TargetStruct):
    """A bounded external view of Reforged's ``AgentArrayStruct``.

    The native structure contains one ``GWArray<Agent*>`` header.  The
    external view keeps that exact header, while category methods delegate to
    the validated snapshot that produced this object. Binding the view applies
    the source context gate and builds its bounded per-agent lookup cache;
    ``raw_agents`` exposes that materialized list in table-slot order.
    """

    _pack_ = 1
    _fields_ = [("agent_array", GWArray)]

    _owner: AgentArray | None = None
    _reader: RemoteMemoryReader | None = None
    _allegiance_cache: dict[str, list[int]] | None
    _agent_by_id: dict[int, AgentStruct]
    _last_instance_timer: int
    frame_counter: int
    frame_throttle: int

    def bind_external(
        self,
        owner: AgentArray,
        reader: RemoteMemoryReader,
    ) -> AgentArrayStruct:
        """Attach the owner and the reader this client reads through, then build the caches."""

        self._owner = owner
        self._reader = reader
        self._ensure_cache_up_to_date()
        return self

    def _ensure_fields(self) -> None:
        """Initialize the source cache attributes on this local view."""

        if not hasattr(self, "_allegiance_cache"):
            self._allegiance_cache = None
        if not hasattr(self, "_agent_by_id"):
            self._agent_by_id = {}
        if not hasattr(self, "_last_instance_timer"):
            self._last_instance_timer = 0
        if not hasattr(self, "frame_counter"):
            self.frame_counter = 0
        if not hasattr(self, "frame_throttle"):
            self.frame_throttle = 2

    def _drop_cache(self) -> None:
        """Clear locally cached categories and records."""

        self._ensure_fields()
        self._allegiance_cache = None
        self._agent_by_id = {}
        self._last_instance_timer = 0

    def _ensure_cache_up_to_date(self) -> None:
        """Rebuild the category caches (``AgentContext.py:1115-1149``).

        The source checks five in-process contexts and then calls ``_build_allegiance_cache``; this
        port asks the client's own equivalent check (``AgentArray._cache_contexts_are_available``,
        which validates the same context tree externally). With no owner there is nothing to read,
        so the caches are dropped rather than answered from stale data.
        """

        self._ensure_fields()
        if self._owner is None or not self._owner._cache_contexts_are_available():
            self._drop_cache()
            return
        self._build_allegiance_cache()

    def _iter_valid_agents(self) -> Iterator[AgentStruct]:
        """Yield non-null materialized records with nonzero agent IDs."""

        for agent in self.raw_agents:
            if agent is not None and int(agent.agent_id) != 0:
                yield agent

    def _build_allegiance_cache(self) -> None:
        """Populate every category in one traversal (``AgentContext.py:1160-1256``).

        The source's own order, member for member: the id gate from ``AccAgentContext``'s valid
        agents, ``all``, the gadget and item branches (with ``owned_item`` for an item whose owner
        is not zero), then the living branch and its allegiance switch — `Ally`, `Neutral`, `Enemy`
        (each with its dead list), `SpiritPet`, `Minion`, `NpcMinipet`. The source writes the switch
        over the raw numbers 1–6; this port compares against the ports of the same constants that
        Reforged's own ``Agent.py:1428`` uses (``Allegiance(living.allegiance)``).
        """

        self._ensure_fields()

        # The source reads ``AccAgentContext.get_context()`` here, and in Reforged that class-level
        # cache is refreshed once per frame by the context's own in-process callback. There is no
        # frame loop in this port, so the refresh is the source's own ``_update_ptr`` at the point
        # of use — the same treatment ``py4gw/internals/string_table.py`` gives
        # ``TextParser._update_ptr()`` and ``py4gw/context/gw_context.py`` gives every other facade
        # (``_GWContextBase.GetContext``). Without it the class cache is whatever the process
        # happens to hold; on a fresh connection that is ``None``, and this member would then drop
        # the cache and answer every category with an empty list and every id with ``None``.
        AccAgentContext._update_ptr()

        acc_agent_ctx = AccAgentContext.get_context()
        if not acc_agent_ctx:
            self._drop_cache()
            return

        valid_agents_ids = acc_agent_ctx.valid_agents_ids
        if not valid_agents_ids:
            self._drop_cache()
            return

        cache: dict[str, list[int]] = {
            "ally": [],
            "neutral": [],
            "enemy": [],
            "spirit_pet": [],
            "minion": [],
            "npc_minipet": [],
            "living": [],
            "item": [],
            "owned_item": [],
            "gadget": [],
            "dead_ally": [],
            "dead_enemy": [],
            "all": [],
        }
        agent_by_id: dict[int, AgentStruct] = {}

        # Single iteration — uses movement-valid agents only
        for agent in self._iter_valid_agents():
            if agent.agent_id not in valid_agents_ids:
                continue

            aid = int(agent.agent_id)
            if aid == 0:
                continue

            cache["all"].append(aid)
            agent_by_id[aid] = agent

            if agent.is_gadget_type:
                cache["gadget"].append(aid)
                continue

            if agent.is_item_type:
                item = agent.GetAsAgentItem()
                if item is None:
                    continue
                if item.owner != 0:
                    cache["owned_item"].append(aid)
                cache["item"].append(aid)
                continue

            # ---------- LIVING types ----------
            if not agent.is_living_type:
                continue

            living = agent.GetAsAgentLiving()
            if not living:
                continue

            cache["living"].append(aid)

            allegiance = int(living.allegiance)
            if allegiance == Allegiance.Ally:
                cache["ally"].append(aid)
                if living.is_dead:
                    cache["dead_ally"].append(aid)
            elif allegiance == Allegiance.Neutral:
                cache["neutral"].append(aid)
            elif allegiance == Allegiance.Enemy:
                cache["enemy"].append(aid)
                if living.is_dead:
                    cache["dead_enemy"].append(aid)
            elif allegiance == Allegiance.SpiritPet:
                cache["spirit_pet"].append(aid)
            elif allegiance == Allegiance.Minion:
                cache["minion"].append(aid)
            elif allegiance == Allegiance.NpcMinipet:
                cache["npc_minipet"].append(aid)

        self._allegiance_cache = cache
        self._agent_by_id = agent_by_id

    @property
    def raw_agents(self) -> list[AgentStruct | None]:
        """Every agent pointer in the array, in slot order (``AgentContext.py:1079-1108``).

        The source walks ``GW_Array_Value_View(arr, POINTER(AgentStruct))`` and takes each
        ``ptr.contents``, keeping ``None`` where the engine left a null slot. This port walks the
        same array through the ported ``GWArrayView`` — which reads the pointer and materializes the
        record through this client's reader — and keeps the slot order the same way.

        **Two external-reader differences, both recorded:** a null pointer is answered as ``None``
        instead of raising, because there is no host pointer to dereference, and a pointer whose
        bytes cannot be read is ``None`` — the source's ``except ValueError`` on a bad cast.
        """

        array = self.agent_array
        if not array.m_buffer or array.m_size == 0:
            return []
        if self._reader is None:
            return []
        view = GWArrayView(self._reader, array, AgentStruct)
        return [view.get(index) for index in range(view.size())]

    def GetAgentByID(
        self, agent_id: int
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Return one agent record by identifier (``AgentContext.py:1260-1280``).

        The source answers from its own per-id cache first — the one ``_build_allegiance_cache``
        fills — and then from the injected runtime's shared-memory channel
        (``SystemShaMemMgr.get_agent_array_wrapper()``, which this project does not have).

        **The divergence, on that fallback only:** where the source asks the shared-memory channel,
        this port rebuilds the cache from the client's own agent array — the same array the channel
        is filled from — and answers from that, or ``None`` when the id is not there. The source
        answers ``None`` on the same missing-id path.
        """

        self._ensure_fields()
        cached_agent = self._agent_by_id.get(agent_id)
        if cached_agent is not None:
            return cached_agent
        self._build_allegiance_cache()
        return self._agent_by_id.get(agent_id)

    def _ids(self, category_name: str) -> list[int]:
        self._ensure_fields()
        if self._allegiance_cache is None:
            return []
        return list(self._allegiance_cache.get(category_name, []))

    def GetAgentArray(self) -> list[int]:
        return self._ids("all")

    def GetAllyArray(self) -> list[int]:
        return self._ids("ally")

    def GetNeutralArray(self) -> list[int]:
        return self._ids("neutral")

    def GetEnemyArray(self) -> list[int]:
        return self._ids("enemy")

    def GetSpiritPetArray(self) -> list[int]:
        return self._ids("spirit_pet")

    def GetMinionArray(self) -> list[int]:
        return self._ids("minion")

    def GetNPCMinipetArray(self) -> list[int]:
        return self._ids("npc_minipet")

    def GetItemAgentArray(self) -> list[int]:
        return self._ids("item")

    def GetOwnedItemAgentArray(self) -> list[int]:
        return self._ids("owned_item")

    def GetGadgetAgentArray(self) -> list[int]:
        return self._ids("gadget")

    def GetDeadAllyArray(self) -> list[int]:
        return self._ids("dead_ally")

    def GetDeadEnemyArray(self) -> list[int]:
        return self._ids("dead_enemy")


assert ctypes.sizeof(AgentArrayStruct) == ctypes.sizeof(GWArray)


class AgentArray:
    """Resolve and traverse the native ``GWArray<Agent*>`` externally.

    The source holds one cached ``AgentArrayStruct`` pointer, refreshed by its
    ``UpdatePtr`` callback. This project has no frame loop, so the pointer is
    resolved on demand by :meth:`initialize` and the structure it addresses is
    read on demand by :meth:`read_context`, which is the same read the source's
    callback performs (``AgentContext.py:1405-1415``).
    """

    _RESOLVER = "agent.agent_array_addr"
    _callback_name_ptr = "AgentArray.UpdatePtr"
    _callback_name_cache = "AgentArray.UpdateCache"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        cache_context_validator: Callable[[], bool] | None = None,
    ) -> None:
        """Create an agent-array reader for one connected client."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._cache_context_validator = cache_context_validator
        self._array_address: int | None = None
        self._context_view: AgentArrayStruct | None = None

    @property
    def cached_array_address(self) -> int | None:
        """Return the cached native array address, if initialized."""

        return self._array_address

    def get_ptr(self) -> int:
        """Return the cached resolver result using the source facade name."""

        return self._array_address or 0

    def _update_ptr(self) -> int:
        """Resolve the array pointer using the source facade method name."""

        return self.initialize()

    def reset_cache(self) -> None:
        """Discard the cached view, as the source's ``reset_cache`` discards its pointer.

        The source clears ``_cached_ctx`` and its per-id record cache
        (``AgentContext.py:1417-1433``); this port additionally drops the caches
        the view itself holds, because the view is a local copy of the structure.
        """

        if self._context_view is not None:
            self._context_view._drop_cache()
        self._context_view = None

    def enable(self) -> None:
        """Register the source's per-frame ``UpdatePtr`` callback (``AgentContext.py:1443-1452``).

        Reforged's body is
        ``PyCallback.PyCallback.Register(AgentArray._callback_name_ptr, PyCallback.Phase.PreUpdate,
        AgentArray.reset_cache, priority=6, context=PyCallback.Context.Draw)`` — the tick that keeps
        ``_cached_ctx`` fresh and clears the per-id cache. This port has no frame loop and nothing to
        dispatch to, so that registration cannot be made here; the view is built on demand by
        :meth:`read_context` instead, which is the read-on-demand rule the rest of the port follows
        (``AGENTS.md``, ``PORTING_RULES.md``). :meth:`disable` is the source's own body, since
        clearing the pointer needs no runtime.
        """

        raise NotImplementedError(
            "AgentArray.enable requires Reforged's injected callback runtime: its body registers "
            "AgentArray.UpdatePtr at PyCallback.Phase.PreUpdate with priority 6 "
            "(AgentContext.py:1443-1452), and this port has no frame loop to register it with. "
            "The source's member works; this port raises at the call site and names the work item "
            "instead of returning a wrong value."
        )

    def disable(self) -> None:
        """Clear this reader's cached pointer and view, as the source's ``disable`` does."""

        self.reset_cache()
        self._array_address = None

    def get_context(self) -> AgentArrayStruct:
        """Return the source-shaped view, building it on first use.

        The source returns whatever its per-frame ``UpdatePtr`` callback cached
        (``AgentContext.py:1473-1474``), which can be ``None`` before the first tick. This project
        has no frame loop, so the view is built the first time it is asked for — the read-on-demand
        rule the rest of the port follows — and the answer is therefore always the view: a read that
        cannot be made raises from :meth:`read_context` instead of answering ``None``.
        """

        if self._context_view is None:
            return self.read_context()
        return self._context_view

    def _update_cache(self) -> None:
        """Run the source-named category-cache refresh on the current view."""

        context = self.get_context()
        if context is not None:
            context._ensure_cache_up_to_date()

    def _cache_contexts_are_available(self) -> bool:
        """Check the source cache's additional context-presence conditions."""

        if self._cache_context_validator is None:
            return True
        return self._cache_context_validator()

    def resolve_address(self) -> int:
        """Return the stable native array address used by the resolver."""

        if self._array_address is None:
            return self.initialize()
        return self._array_address

    def initialize(self) -> int:
        """Resolve and cache ``agent.agent_array_addr`` once."""

        if self._array_address is not None:
            return self._array_address
        result = self._patterns.resolve(self._RESOLVER, self._scanner)
        if not result.ok:
            detail = result.message or "the resolver returned no address"
            raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
        self._array_address = result.value
        return self._array_address


    def read_context(self) -> AgentArrayStruct:
        """Read the structure the cached pointer addresses and build its caches.

        The source's callback keeps the client's own ``AgentArrayStruct`` pointer and this read is
        its external equivalent (``AgentContext.py:1405-1415``): the fixed-width
        ``GWArray<Agent*>`` header (buffer, capacity, size) is read into a local copy and bound to
        this client's reader and owner. The category caches are built by the view itself, from that
        same array — ``_build_allegiance_cache``.
        """

        header = self._read_array_header(self.resolve_address(), "agent array")
        self._context_view = AgentArrayStruct.from_buffer_copy(
            bytes(header)
        ).bind_external(self, self._reader)
        return self._context_view

    def GetAgentByID(
        self, agent_id: int
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Return one agent record by identifier (``AgentContext.py:1476-1497``).

        The source's facade delegates to the context it cached; so does this one, through
        :meth:`get_context`, and the view answers from its own per-id cache first and then from the
        array (the divergence recorded on ``AgentArrayStruct.GetAgentByID``).
        """

        context = self.get_context()
        if context is None:
            return None
        return context.GetAgentByID(agent_id)


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


