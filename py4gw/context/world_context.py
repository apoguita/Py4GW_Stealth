"""External reader for the native ``WorldContext`` root.

The world structure is a large aggregate owned by :class:`GameContext`.  This
module deliberately starts with the root layout and its scalar values/array
headers.  The pointed-to records (players, NPCs, quests, titles, and skills)
are migrated as bounded child readers instead of being materialized whenever a
world snapshot is requested.
"""

from __future__ import annotations

from ..target_struct import TargetStruct

import ctypes
import math
from ctypes import Structure, c_float, c_uint8, c_uint16, c_uint32
from typing import Any, Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the world root."""


_record_type = TypeVar("_record_type", bound=Structure)
_MAX_WORLD_ARRAY_READ_BYTES = 16 * 1024 * 1024
_MAX_WORLD_STRING_CHARS = 32_768
_WORLD_STRING_CHUNK_CHARS = 64


def _read_world_array_bytes(
    reader: _memory_reader,
    array: GWArray,
    element_type: type[Any],
) -> bytes | None:
    """Read one complete, validated target array as a bounded byte block."""

    address = int(array.m_buffer)
    count = int(array.m_size)
    capacity = int(array.m_capacity)
    if address < 0x10000 or count == 0 or count > capacity:
        return None

    element_size = ctypes.sizeof(element_type)
    byte_count = count * element_size
    if byte_count > _MAX_WORLD_ARRAY_READ_BYTES:
        raise ValueError(
            "WorldContext array exceeds the per-array read limit: "
            f"count={count}, element_size={element_size}, bytes={byte_count}"
        )
    if address + byte_count > 0x1_0000_0000:
        raise ValueError(
            "WorldContext array extends beyond the 32-bit target address space: "
            f"address=0x{address:08X}, bytes={byte_count}"
        )

    raw = reader.read(address, byte_count)
    if len(raw) != byte_count:
        raise OSError(
            "WorldContext array read returned an unexpected byte count: "
            f"address=0x{address:08X}, requested={byte_count}, received={len(raw)}"
        )
    return raw


class Vec3f(TargetStruct):
    """Three target-process single-precision coordinates."""

    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        super().__init__()
        self.x = x
        self.y = y
        self.z = z

    def to_tuple(self) -> tuple[float, float, float]:
        """Return the coordinates as a three-value tuple."""

        return float(self.x), float(self.y), float(self.z)

    def to_list(self) -> list[float]:
        """Return the coordinates as a three-value list."""

        return [float(self.x), float(self.y), float(self.z)]


Vec3fStruct = Vec3f


class Vec2f(TargetStruct):
    """Two target-process single-precision coordinates."""

    _fields_ = [("x", c_float), ("y", c_float)]

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        super().__init__()
        self.x = x
        self.y = y

    def to_tuple(self) -> tuple[float, float]:
        """Return the coordinates as a two-value tuple."""

        return float(self.x), float(self.y)

    def to_list(self) -> list[float]:
        """Return the coordinates as a two-value list."""

        return [float(self.x), float(self.y)]

    def __add__(self, other: object) -> Vec2f:
        if isinstance(other, Vec2f):
            return Vec2f(float(self.x) + float(other.x), float(self.y) + float(other.y))
        return NotImplemented

    def __sub__(self, other: object) -> Vec2f:
        if isinstance(other, Vec2f):
            return Vec2f(float(self.x) - float(other.x), float(self.y) - float(other.y))
        return NotImplemented

    def __mul__(self, scalar: float) -> Vec2f:
        return Vec2f(float(self.x) * scalar, float(self.y) * scalar)

    def __truediv__(self, scalar: float) -> Vec2f:
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return Vec2f(float(self.x) / scalar, float(self.y) / scalar)

    def __repr__(self) -> str:
        return f"Vec2f(x={self.x}, y={self.y})"

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value)


Vec2fStruct = Vec2f

class AccountInfoStruct(TargetStruct):
    """The native account-summary record owned by ``WorldContext``."""

    _pack_ = 1
    _fields_ = [
        ("account_name_ptr", c_uint32),
        ("wins", c_uint32),
        ("losses", c_uint32),
        ("rating", c_uint32),
        ("qualifier_points", c_uint32),
        ("rank", c_uint32),
        ("tournament_reward_points", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AccountInfoStruct:
        """Attach the reader used by the account-name pointer."""

        self._remote_reader = reader
        return self

    @property
    def account_name_str(self) -> str | None:
        """Read the bounded encoded account name."""

        if not self.account_name_ptr:
            return None
        return _read_target_text(self._remote_reader, int(self.account_name_ptr))


class MapAgentStruct(TargetStruct):
    """The native 0x34 map-agent status record."""

    _pack_ = 1
    _fields_ = [
        ("cur_energy", c_float),
        ("max_energy", c_float),
        ("energy_regen", c_float),
        ("skill_timestamp", c_uint32),
        ("h0010", c_float),
        ("max_energy2", c_float),
        ("h0018", c_float),
        ("h001C", c_uint32),
        ("cur_health", c_float),
        ("max_health", c_float),
        ("health_regen", c_float),
        ("h002C", c_uint32),
        ("effects", c_uint32),
    ]

    @property
    def is_bleeding(self) -> bool:
        return bool(int(self.effects) & 0x0001)

    @property
    def is_conditioned(self) -> bool:
        return bool(int(self.effects) & 0x0002)

    @property
    def is_crippled(self) -> bool:
        return int(self.effects) & 0x000A == 0x000A

    @property
    def is_dead(self) -> bool:
        return bool(int(self.effects) & 0x0010)

    @property
    def is_deep_wounded(self) -> bool:
        return bool(int(self.effects) & 0x0020)

    @property
    def is_poisoned(self) -> bool:
        return bool(int(self.effects) & 0x0040)

    @property
    def is_enchanted(self) -> bool:
        return bool(int(self.effects) & 0x0080)

    @property
    def is_degen_hexed(self) -> bool:
        return bool(int(self.effects) & 0x0400)

    @property
    def is_hexed(self) -> bool:
        return bool(int(self.effects) & 0x0800)

    @property
    def is_weapon_spelled(self) -> bool:
        return bool(int(self.effects) & 0x8000)


class PartyAllyStruct(TargetStruct):
    """The native 0x0C party-ally record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("unk", c_uint32),
        ("composite_id", c_uint32),
    ]


class AttributeStruct(TargetStruct):
    """The native 0x14 party-attribute record."""

    _pack_ = 1
    _fields_ = [
        ("attribute_id", c_uint32),
        ("level_base", c_uint32),
        ("level", c_uint32),
        ("decrement_points", c_uint32),
        ("increment_points", c_uint32),
    ]

    @property
    def is_valid(self) -> bool:
        """Return whether the record contains any allocated attribute data."""

        return any(
            int(value) > 0
            for value in (
                self.level_base,
                self.level,
                self.decrement_points,
                self.increment_points,
            )
        )

    @property
    def name(self) -> str:
        """Return the maintained source name for this attribute identifier."""

        return _ATTRIBUTE_NAMES.get(int(self.attribute_id), "Unknown")

    def GetName(self) -> str:
        """Return the source compatibility spelling."""

        return self.name

class PartyAttributeStruct(TargetStruct):
    """The native 0x43C attribute block for one party agent."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("attribute_array", AttributeStruct * 54),
    ]

    @property
    def attributes(self) -> list[AttributeStruct]:
        """Return the inline attribute records without remote reads."""

        return [self.attribute_array[index] for index in range(54)]

    @property
    def valid_attributes(self) -> list[AttributeStruct]:
        """Return only populated attribute records."""

        return [attribute for attribute in self.attributes if attribute.is_valid]


class EffectStruct(TargetStruct):
    """The native 0x18 active-effect record."""

    _pack_ = 1
    _fields_ = [
        ("skill_id", c_uint32),
        ("attribute_level", c_uint32),
        ("effect_id", c_uint32),
        ("agent_id", c_uint32),
        ("duration", c_float),
        ("timestamp", c_uint32),
    ]

    @property
    def is_maintained(self) -> bool:
        """Return whether the effect has a non-zero caster agent."""

        return bool(int(self.agent_id))


class BuffStruct(TargetStruct):
    """The native 0x10 maintained-buff record."""

    _pack_ = 1
    _fields_ = [
        ("skill_id", c_uint32),
        ("h0004", c_uint32),
        ("buff_id", c_uint32),
        ("target_agent_id", c_uint32),
    ]


class AgentEffectsStruct(TargetStruct):
    """The native 0x24 effects block owned by one party agent."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("buff_array", GWArray),
        ("effect_array", GWArray),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AgentEffectsStruct:
        """Attach the reader used by the nested buff/effect arrays."""

        self._remote_reader = reader
        return self

    def _values(
        self,
        array: GWArray,
        element_type: type[Structure],
    ) -> list[Structure]:
        if self._remote_reader is None:
            raise RuntimeError("AgentEffects snapshot is not bound to a reader.")
        raw = _read_world_array_bytes(self._remote_reader, array, element_type)
        if raw is None:
            return []
        element_size = ctypes.sizeof(element_type)
        return [
            element_type.from_buffer_copy(raw, offset)
            for offset in range(0, len(raw), element_size)
        ]

    @property
    def buffs(self) -> list[BuffStruct]:
        """Read all maintained buffs for this agent."""

        return [
            value
            for value in self._values(self.buff_array, BuffStruct)
            if isinstance(value, BuffStruct)
        ]

    @property
    def effects(self) -> list[EffectStruct]:
        """Read all active effects for this agent."""

        return [
            value
            for value in self._values(self.effect_array, EffectStruct)
            if isinstance(value, EffectStruct)
        ]


def _read_target_text(reader: _memory_reader | None, address: int) -> str | None:
    """Read a complete NUL-terminated UTF-16 string within the safety limit."""

    if reader is None or address < 0x10000:
        return None
    raw = bytearray()
    for start in range(0, _MAX_WORLD_STRING_CHARS, _WORLD_STRING_CHUNK_CHARS):
        chunk_chars = min(
            _WORLD_STRING_CHUNK_CHARS, _MAX_WORLD_STRING_CHARS - start
        )
        chunk_address = address + start * 2
        try:
            chunk = reader.read(chunk_address, chunk_chars * 2)
        except OSError:
            chunk = b""

        if len(chunk) == chunk_chars * 2:
            for offset in range(0, len(chunk), 2):
                if chunk[offset : offset + 2] == b"\x00\x00":
                    raw.extend(chunk[:offset])
                    return bytes(raw).decode("utf-16-le", errors="replace")
            raw.extend(chunk)
            continue

        # If a chunk crosses into unreadable memory, retry only the current
        # chunk one UTF-16 code unit at a time and stop as soon as its NUL is
        # reached. This avoids reading beyond a valid terminator.
        for index in range(chunk_chars):
            pair = reader.read(chunk_address + index * 2, 2)
            if pair == b"\x00\x00":
                return bytes(raw).decode("utf-16-le", errors="replace")
            if len(pair) != 2:
                raise OSError(
                    "WorldContext string read returned an unexpected byte count: "
                    f"address=0x{chunk_address + index * 2:08X}, received={len(pair)}"
                )
            raw.extend(pair)

    raise ValueError(
        "WorldContext UTF-16 string is not terminated within "
        f"{_MAX_WORLD_STRING_CHARS} characters at 0x{address:08X}"
    )


def _format_encoded_text(value: str | None) -> str | None:
    """Return the source project's printable representation of encoded text."""

    if value is None:
        return None
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


_ATTRIBUTE_NAMES = {
    0: "Fast Casting", 1: "Illusion Magic", 2: "Domination Magic",
    3: "Inspiration Magic", 4: "Blood Magic", 5: "Death Magic",
    6: "Soul Reaping", 7: "Curses", 8: "Air Magic", 9: "Earth Magic",
    10: "Fire Magic", 11: "Water Magic", 12: "Energy Storage",
    13: "Healing Prayers", 14: "Smiting Prayers", 15: "Protection Prayers",
    16: "Divine Favor", 17: "Strength", 18: "Axe Mastery",
    19: "Hammer Mastery", 20: "Swordsmanship", 21: "Tactics",
    22: "Beast Mastery", 23: "Expertise", 24: "Wilderness Survival",
    25: "Marksmanship", 26: "Unknown1", 27: "Unknown2", 28: "Unknown3",
    29: "Dagger Mastery", 30: "Deadly Arts", 31: "Shadow Arts",
    32: "Communing", 33: "Restoration Magic", 34: "Channeling Magic",
    35: "Critical Strikes", 36: "Spawning Power", 37: "Spear Mastery",
    38: "Command", 39: "Motivation", 40: "Leadership", 41: "Scythe Mastery",
    42: "Wind Prayers", 43: "Earth Prayers", 44: "Mysticism", 45: "None",
}


class NPC_ModelStruct(TargetStruct):
    """The native 0x30 NPC model record."""

    _pack_ = 1
    _fields_ = [
        ("model_file_id", c_uint32),
        ("h0004", c_uint32),
        ("scale", c_uint32),
        ("sex", c_uint32),
        ("npc_flags", c_uint32),
        ("primary", c_uint32),
        ("h0018", c_uint32),
        ("default_level", c_uint8),
        ("padding1", c_uint8),
        ("padding2", c_uint16),
        ("name_enc_ptr", c_uint32),
        ("model_files_ptr", c_uint32),
        ("files_count", c_uint32),
        ("files_capacity", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> NPC_ModelStruct:
        """Attach the reader used by the indirect name/model fields."""

        self._remote_reader = reader
        return self

    @property
    def is_valid(self) -> bool:
        """Return whether the model record has a model identifier."""

        return bool(int(self.model_file_id))

    @property
    def is_henchman(self) -> bool:
        """Return whether the native NPC flags identify a henchman."""

        return bool(int(self.npc_flags) & 0x10)

    @property
    def is_hero(self) -> bool:
        """Return whether the native NPC flags identify a hero."""

        return bool(int(self.npc_flags) & 0x20)

    @property
    def is_spirit(self) -> bool:
        """Return whether the native NPC flags identify a spirit."""

        return bool(int(self.npc_flags) & 0x4000)

    @property
    def is_minion(self) -> bool:
        """Return whether the native NPC flags identify a minion."""

        return bool(int(self.npc_flags) & 0x100)

    @property
    def is_pet(self) -> bool:
        """Return whether the native NPC flags identify a pet."""

        return int(self.npc_flags) == 0xD

    @property
    def is_fleshy(self) -> bool:
        """Return whether the native NPC flags allow a corpse."""

        return bool(int(self.npc_flags) & 0x8)

    @property
    def name_encoded_str(self) -> str | None:
        """Return the encoded NPC name."""

        return _read_target_text(self._remote_reader, int(self.name_enc_ptr))

    @property
    def name_str(self) -> str | None:
        """Return the display-safe NPC name."""

        return _format_encoded_text(
            _read_target_text(self._remote_reader, int(self.name_enc_ptr))
        )

    @property
    def name(self) -> str:
        """Read the bounded NPC name through its target pointer."""

        return _read_target_text(self._remote_reader, int(self.name_enc_ptr)) or ""

    @property
    def model_file_ids(self) -> list[int]:
        """Read every model-file identifier declared by the source record."""

        if self._remote_reader is None or not self.model_files_ptr:
            return []
        count = int(self.files_count)
        capacity = int(self.files_capacity)
        if count > capacity:
            raise ValueError(
                "NPC model-file count exceeds its capacity: "
                f"count={count}, capacity={capacity}"
            )
        array = GWArray(int(self.model_files_ptr), capacity, count, 0)
        raw = _read_world_array_bytes(self._remote_reader, array, c_uint32)
        if raw is None:
            return []
        return [
            int(c_uint32.from_buffer_copy(raw, offset).value)
            for offset in range(0, len(raw), ctypes.sizeof(c_uint32))
        ]

    @property
    def model_files(self) -> list[int]:
        """Return the source-compatible model-file list."""

        return self.model_file_ids


class PlayerStruct(TargetStruct):
    """The native 0x50 player record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("h0004", c_uint32 * 3),
        ("appearance_bitmap", c_uint32),
        ("flags", c_uint32),
        ("primary", c_uint32),
        ("secondary", c_uint32),
        ("h0020", c_uint32),
        ("name_enc_ptr", c_uint32),
        ("name_ptr", c_uint32),
        ("party_leader_player_number", c_uint32),
        ("active_title_tier", c_uint32),
        ("reforged_or_dhuums_flags", c_uint32),
        ("player_number", c_uint32),
        ("party_size", c_uint32),
        ("h0040_array", GWArray),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> PlayerStruct:
        """Attach the reader used by the indirect names and pointer array."""

        self._remote_reader = reader
        return self

    @property
    def is_pvp(self) -> bool:
        """Return whether the player flags identify a PvP character."""

        return bool(int(self.flags) & 0x800)

    @property
    def is_dhuums_covenant(self) -> bool:
        """Return the native Dhuum's Covenant flag."""

        return bool(int(self.reforged_or_dhuums_flags) & 0x1)

    @property
    def is_melandrus_accord(self) -> bool:
        """Return the native Melandru's Accord flag."""

        return bool(int(self.reforged_or_dhuums_flags) & 0x2)

    @property
    def is_reforged(self) -> bool:
        """Return the native Reforged flag."""

        return bool(int(self.reforged_or_dhuums_flags) & 0x4)

    @property
    def name_encoded(self) -> str:
        """Read the target name pointer without applying game text mapping."""

        return _read_target_text(self._remote_reader, int(self.name_ptr)) or ""

    @property
    def name_enc_encoded_str(self) -> str | None:
        """Read the encoded name-pointer field used by Reforged."""

        return _read_target_text(self._remote_reader, int(self.name_enc_ptr))

    @property
    def name_enc_str(self) -> str | None:
        """Return the source display name read from ``name_ptr``."""

        return _format_encoded_text(self.name_encoded_str)

    @property
    def name_encoded_str(self) -> str | None:
        """Return the encoded player name under the source property name."""

        return _read_target_text(self._remote_reader, int(self.name_ptr))

    @property
    def name_str(self) -> str | None:
        """Return the display-safe player name."""

        return _format_encoded_text(self.name_encoded_str)

    @property
    def name(self) -> str:
        """Return the bounded player name."""

        return self.name_encoded

    @property
    def auxiliary_pointers(self) -> list[int]:
        """Read every source auxiliary pointer value."""

        if self._remote_reader is None:
            return []
        raw = _read_world_array_bytes(self._remote_reader, self.h0040_array, c_uint32)
        if raw is None:
            return []
        return [
            int(c_uint32.from_buffer_copy(raw, offset).value)
            for offset in range(0, len(raw), ctypes.sizeof(c_uint32))
        ]

    @property
    def h0040_ptrs(self) -> list[int] | None:
        """Return the source-compatible auxiliary pointer list."""

        if self._remote_reader is None or not self.h0040_array.m_buffer:
            return None
        values = self.auxiliary_pointers
        return values or None


class HeroFlagStruct(TargetStruct):
    """The native 0x24 hero flag record."""

    _pack_ = 1
    _fields_ = [
        ("hero_id", c_uint32),
        ("agent_id", c_uint32),
        ("level", c_uint32),
        ("hero_behavior", c_uint32),
        ("flag_ptr", Vec2f),
        ("h0018", c_uint32),
        ("locked_target_id", c_uint32),
        ("h0020", c_uint32),
    ]

    @property
    def flag(self) -> Vec2f | None:
        """Return finite hero-flag target coordinates."""

        if not math.isfinite(float(self.flag_ptr.x)) or not math.isfinite(float(self.flag_ptr.y)):
            return None
        return self.flag_ptr


class HeroInfoStruct(TargetStruct):
    """The native 0x78 hero information record."""

    _pack_ = 1
    _fields_ = [
        ("hero_id", c_uint32),
        ("agent_id", c_uint32),
        ("level", c_uint32),
        ("primary", c_uint32),
        ("secondary", c_uint32),
        ("hero_file_id", c_uint32),
        ("model_file_id", c_uint32),
        ("h001C", c_uint8 * 52),
        ("name_encoded_str", c_uint16 * 20),
    ]

    @property
    def name(self) -> str:
        """Decode the fixed-width UTF-16 hero name."""

        raw = bytes(self.name_encoded_str)
        return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]

    @property
    def name_enc(self) -> ctypes.Array[c_uint16]:
        """Compatibility alias for the source ``name_encoded_str`` field."""

        return self.name_encoded_str

    @property
    def name_str(self) -> str:
        """Return the display-safe hero name."""

        return _format_encoded_text(self.name) or ""


class ControlledMinionsStruct(TargetStruct):
    """The native controlled-minion count record."""

    _pack_ = 1
    _fields_ = [("agent_id", c_uint32), ("minion_count", c_uint32)]


class PartyMemberMoraleInfoStruct(TargetStruct):
    """The maintained player morale record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("agent_id_dupe", c_uint32),
        ("unk", c_uint32 * 4),
        ("morale", c_uint32),
    ]


class PartyMoraleLinkStruct(TargetStruct):
    """The party-morale link containing a target morale record pointer."""

    _pack_ = 1
    _fields_ = [
        ("unk", c_uint32),
        ("unk2", c_uint32),
        ("party_member_info_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> PartyMoraleLinkStruct:
        """Attach the reader used by the morale-record pointer."""

        self._remote_reader = reader
        return self

    @property
    def party_member_info(self) -> PartyMemberMoraleInfoStruct | None:
        """Read the linked morale record when its pointer is valid."""

        address = int(self.party_member_info_ptr)
        if address < 0x10000:
            return None
        if self._remote_reader is None:
            raise RuntimeError("PartyMoraleLink is not bound to a memory reader.")
        raw_value = self._remote_reader.read(
            address, ctypes.sizeof(PartyMemberMoraleInfoStruct)
        )
        return PartyMemberMoraleInfoStruct.from_buffer_copy(raw_value)


class PlayerControlledCharacterStruct(TargetStruct):
    """The maintained 0x134 player-controlled-character record."""

    _pack_ = 1
    _fields_ = [
        ("field0_0x0", c_uint32),
        ("field1_0x4", c_uint32),
        ("field2_0x8", c_uint32),
        ("field3_0xc", c_uint32),
        ("field4_0x10", c_uint32),
        ("agent_id", c_uint32),
        ("composite_id", c_uint32),
        ("field7_0x1c", c_uint32),
        ("field8_0x20", c_uint32),
        ("field9_0x24", c_uint32),
        ("field10_0x28", c_uint32),
        ("field11_0x2c", c_uint32),
        ("field12_0x30", c_uint32),
        ("field13_0x34", c_uint32),
        ("field14_0x38", c_uint32),
        ("field15_0x3c", c_uint32),
        ("field16_0x40", c_uint32),
        ("field17_0x44", c_uint32),
        ("field18_0x48", c_uint32),
        ("field19_0x4c", c_float),
        ("field20_0x50", c_float),
        ("field21_0x54", c_uint32),
        ("field22_0x58", c_uint32),
        ("field23_0x5c", c_uint32),
        ("field24_0x60", c_uint32),
        ("more_flags", c_uint32),
        ("field26_0x68", c_uint32),
        ("field27_0x6c", c_uint32),
        ("field28_0x70", c_uint32),
        ("field29_0x74", c_uint32),
        ("field30_0x78", c_uint32),
        ("field31_0x7c", c_uint32),
        ("field32_0x80", c_uint32),
        ("field33_0x84", c_uint32),
        ("field34_0x88", c_uint32),
        ("field35_0x8c", c_uint32),
        ("field36_0x90", c_uint32),
        ("field37_0x94", c_uint32),
        ("field38_0x98", c_uint32),
        ("field39_0x9c", c_uint32),
        ("field40_0xa0", c_uint32),
        ("field41_0xa4", c_uint32),
        ("field42_0xa8", c_uint32),
        ("field43_0xac", c_uint32),
        ("field44_0xb0", c_uint32),
        ("field45_0xb4", c_uint32),
        ("field46_0xb8", c_uint32),
        ("field47_0xbc", c_uint32),
        ("field48_0xc0", c_uint32),
        ("field49_0xc4", c_uint32),
        ("field50_0xc8", c_uint32),
        ("field51_0xcc", c_uint32),
        ("field52_0xd0", c_uint32),
        ("field53_0xd4", c_uint32),
        ("field54_0xd8", c_uint32),
        ("field55_0xdc", c_uint32),
        ("field56_0xe0", c_uint32),
        ("field57_0xe4", c_uint32),
        ("field58_0xe8", c_uint32),
        ("field59_0xec", c_uint32),
        ("field60_0xf0", c_uint32),
        ("field61_0xf4", c_uint32),
        ("field62_0xf8", c_uint32),
        ("field63_0xfc", c_uint32),
        ("field64_0x100", c_uint32),
        ("field65_0x104", c_uint32),
        ("field66_0x108", c_uint32),
        ("flags", c_uint32),
        ("field68_0x110", c_uint32),
        ("field69_0x114", c_uint32),
        ("field70_0x118", c_uint32),
        ("field71_0x11c", c_uint32),
        ("field72_0x120", c_uint32),
        ("field73_0x124", c_uint32),
        ("field74_0x128", c_uint32),
        ("field75_0x12c", c_uint32),
        ("field76_0x130", c_uint32),
    ]


class ProfessionStateStruct(TargetStruct):
    """The native party profession-unlock record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("primary", c_uint32),
        ("secondary", c_uint32),
        ("unlocked_professions", c_uint32),
        ("unk", c_uint32),
    ]

    def is_profession_unlocked(self, profession: int) -> bool:
        """Return whether one profession bit is set."""

        return bool(int(self.unlocked_professions) & (1 << profession))

    def IsProfessionUnlocked(self, profession: int) -> bool:
        """Return the Reforged compatibility spelling."""

        return self.is_profession_unlocked(profession)


class PetInfoStruct(TargetStruct):
    """The native 0x1C pet record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("owner_agent_id", c_uint32),
        ("pet_name_ptr", c_uint32),
        ("model_file_id1", c_uint32),
        ("model_file_id2", c_uint32),
        ("behavior", c_uint32),
        ("locked_target_id", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> PetInfoStruct:
        """Attach the reader used by the indirect pet name."""

        self._remote_reader = reader
        return self

    @property
    def name(self) -> str:
        """Read the bounded pet name through its target pointer."""

        return _read_target_text(self._remote_reader, int(self.pet_name_ptr)) or ""

    @property
    def pet_name_encoded_str(self) -> str | None:
        """Return the encoded pet name."""

        return _read_target_text(self._remote_reader, int(self.pet_name_ptr))

    @property
    def pet_name_str(self) -> str | None:
        """Return the display-safe pet name."""

        return _format_encoded_text(
            _read_target_text(self._remote_reader, int(self.pet_name_ptr))
        )


class AgentNameInfoStruct(TargetStruct):
    """The native agent-name pointer record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 13),
        ("name_enc_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AgentNameInfoStruct:
        """Attach the reader used by the name pointer."""

        self._remote_reader = reader
        return self

    @property
    def name_encoded_str(self) -> str | None:
        """Read the encoded agent name."""

        return _read_target_text(self._remote_reader, int(self.name_enc_ptr))

    @property
    def name_str(self) -> str | None:
        """Return the display-safe agent name."""

        return _format_encoded_text(self.name_encoded_str)


class MissionMapIconStruct(TargetStruct):
    """The native 0x28 mission-map icon record."""

    _pack_ = 1
    _fields_ = [
        ("index", c_uint32),
        ("X", c_float),
        ("Y", c_float),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("option", c_uint32),
        ("h0018", c_uint32),
        ("model_id", c_uint32),
        ("h0020", c_uint32),
        ("h0024", c_uint32),
    ]

    @property
    def position(self) -> Vec2f:
        """Return the icon position as the source ``Vec2f`` value."""

        return Vec2f(float(self.X), float(self.Y))

    @property
    def x(self) -> float:
        """Readable lowercase alias for source field ``X``."""

        return float(self.X)

    @property
    def y(self) -> float:
        """Readable lowercase alias for source field ``Y``."""

        return float(self.Y)


class SkillbarSkillStruct(TargetStruct):
    """The native 0x14 skillbar-slot record."""

    _pack_ = 1
    _fields_ = [
        ("adrenaline_a", c_uint32),
        ("adrenaline_b", c_uint32),
        ("recharge", c_uint32),
        ("skill_id", c_uint32),
        ("event", c_uint32),
    ]


class SkillbarCastStruct(TargetStruct):
    """The native 0x08 queued-skill record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint16),
        ("skill_id", c_uint16),
        ("h0004", c_uint32),
    ]


class SkillbarStruct(TargetStruct):
    """The native 0xBC skillbar record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("skills", SkillbarSkillStruct * 8),
        ("disabled", c_uint32),
        ("cast_array", GWArray),
        ("h00B8", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> SkillbarStruct:
        """Attach the reader used by the queued-skill array."""

        self._remote_reader = reader
        return self

    @property
    def is_valid(self) -> bool:
        """Return whether the skillbar belongs to an agent."""

        return bool(int(self.agent_id))

    @property
    def skill_ids(self) -> list[int]:
        """Return the eight maintained skill identifiers."""

        return [int(skill.skill_id) for skill in self.skills]

    def get_skill_by_id(self, skill_id: int) -> SkillbarSkillStruct | None:
        """Return one maintained skill slot by identifier."""

        for skill in self.skills:
            if int(skill.skill_id) == skill_id:
                return skill
        return None

    def GetSkillById(self, skill_id: int) -> SkillbarSkillStruct | None:
        """Return the Reforged compatibility spelling."""

        return self.get_skill_by_id(skill_id)

    @property
    def casted_skills(self) -> list[SkillbarCastStruct]:
        """Read the bounded queued-skill records."""

        if self._remote_reader is None:
            raise RuntimeError("Skillbar snapshot is not bound to a memory reader.")
        raw = _read_world_array_bytes(
            self._remote_reader, self.cast_array, SkillbarCastStruct
        )
        if raw is None:
            return []
        element_size = ctypes.sizeof(SkillbarCastStruct)
        return [
            SkillbarCastStruct.from_buffer_copy(raw, offset)
            for offset in range(0, len(raw), element_size)
        ]


class DupeSkillStruct(TargetStruct):
    """The native 0x08 duplicate-skill record."""

    _pack_ = 1
    _fields_ = [("skill_id", c_uint32), ("count", c_uint32)]


class GamePos(TargetStruct):
    """The native 0x0C quest marker position."""

    _fields_ = [("x", c_float), ("y", c_float), ("zplane", c_uint32)]

    def __init__(self, x: float = 0.0, y: float = 0.0, zplane: int = 0) -> None:
        super().__init__()
        self.x = x
        self.y = y
        self.zplane = zplane

    def to_tuple(self) -> tuple[float, float, int]:
        """Return the coordinates as an x/y/z-plane tuple."""

        return float(self.x), float(self.y), int(self.zplane)


GamePosStruct = GamePos


class QuestStruct(TargetStruct):
    """The native 0x34 quest-log record."""

    _pack_ = 1
    _fields_ = [
        ("quest_id", c_uint32),
        ("log_state", c_uint32),
        ("location_ptr", c_uint32),
        ("name_ptr", c_uint32),
        ("npc_ptr", c_uint32),
        ("map_from", c_uint32),
        ("marker_ptr", GamePos),
        ("h0024", c_uint32),
        ("map_to", c_uint32),
        ("description_ptr", c_uint32),
        ("objectives_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> QuestStruct:
        """Attach the reader used by indirect quest strings."""

        self._remote_reader = reader
        return self

    @property
    def is_completed(self) -> bool:
        """Return whether the quest log state is completed."""

        return bool(int(self.log_state) & 0x2)

    @property
    def is_current_mission_quest(self) -> bool:
        """Return whether this is the current mission quest."""

        return bool(int(self.log_state) & 0x10)

    @property
    def is_primary(self) -> bool:
        """Return whether this quest is marked primary."""

        return bool(int(self.log_state) & 0x20)

    @property
    def is_area_primary(self) -> bool:
        """Return whether this is a primary area quest."""

        return bool(int(self.log_state) & 0x40)

    def _text(self, pointer: int) -> str | None:
        return _read_target_text(self._remote_reader, int(pointer))

    @property
    def location(self) -> str:
        """Read the bounded quest location/category string."""

        return self._text(self.location_ptr) or ""

    @property
    def location_encoded_str(self) -> str | None:
        return self._text(self.location_ptr)

    @property
    def location_str(self) -> str | None:
        return _format_encoded_text(self.location_encoded_str)

    @property
    def name(self) -> str:
        """Read the bounded quest name string."""

        return self._text(self.name_ptr) or ""

    @property
    def name_encoded_str(self) -> str | None:
        return self._text(self.name_ptr)

    @property
    def name_str(self) -> str | None:
        return _format_encoded_text(self.name_encoded_str)

    @property
    def npc(self) -> str:
        """Read the bounded quest NPC string."""

        return self._text(self.npc_ptr) or ""

    @property
    def npc_encoded_str(self) -> str | None:
        return self._text(self.npc_ptr)

    @property
    def npc_str(self) -> str | None:
        return _format_encoded_text(self.npc_encoded_str)

    @property
    def description_encoded_str(self) -> str | None:
        return self._text(self.description_ptr)

    @property
    def description_str(self) -> str | None:
        return _format_encoded_text(self.description_encoded_str)

    @property
    def objectives_encoded_str(self) -> str | None:
        return self._text(self.objectives_ptr)

    @property
    def objectives_str(self) -> str | None:
        return _format_encoded_text(self.objectives_encoded_str)

    @property
    def marker(self) -> GamePos | None:
        values = (
            float(self.marker_ptr.x),
            float(self.marker_ptr.y),
            float(self.marker_ptr.zplane),
        )
        if not all(math.isfinite(value) for value in values):
            return None
        return GamePos(float(self.marker_ptr.x), float(self.marker_ptr.y), int(self.marker_ptr.zplane))


class MissionObjectiveStruct(TargetStruct):
    """The native 0x0C mission-objective record."""

    _pack_ = 1
    _fields_ = [
        ("objective_id", c_uint32),
        ("enc_str_ptr", c_uint32),
        ("type", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> MissionObjectiveStruct:
        """Attach the reader used by the objective text pointer."""

        self._remote_reader = reader
        return self

    @property
    def text(self) -> str:
        """Read the bounded encoded objective text."""

        return _read_target_text(self._remote_reader, int(self.enc_str_ptr)) or ""

    @property
    def enc_str_encoded_str(self) -> str | None:
        return _read_target_text(self._remote_reader, int(self.enc_str_ptr))

    @property
    def enc_str(self) -> str | None:
        return _format_encoded_text(self.enc_str_encoded_str)


class TitleStruct(TargetStruct):
    """The native 0x2C title-progress record."""

    _pack_ = 1
    _fields_ = [
        ("props", c_uint32),
        ("current_points", c_uint32),
        ("current_title_tier_index", c_uint32),
        ("points_needed_current_rank", c_uint32),
        ("next_title_tier_index", c_uint32),
        ("points_needed_next_rank", c_uint32),
        ("max_title_rank", c_uint32),
        ("max_title_tier_index", c_uint32),
        ("h0020", c_uint32),
        ("points_desc_ptr", c_uint32),
        ("h0028_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> TitleStruct:
        """Attach the reader used by indirect title descriptions."""

        self._remote_reader = reader
        return self

    @property
    def is_percentage_based(self) -> bool:
        """Return whether the title uses percentage progress."""

        return bool(int(self.props) & 0x1)

    @property
    def has_tiers(self) -> bool:
        """Return whether the title has tiers."""

        return (int(self.props) & 0x3) == 0x2

    @property
    def points_description(self) -> str:
        """Read the bounded points description."""

        return _read_target_text(self._remote_reader, int(self.points_desc_ptr)) or ""

    @property
    def points_desc_encoded_str(self) -> str | None:
        return _read_target_text(self._remote_reader, int(self.points_desc_ptr))

    @property
    def points_desc_str(self) -> str | None:
        return _format_encoded_text(self.points_desc_encoded_str)

    @property
    def h0028_encoded_str(self) -> str | None:
        return _read_target_text(self._remote_reader, int(self.h0028_ptr))

    @property
    def h0028_str(self) -> str | None:
        return _format_encoded_text(self.h0028_encoded_str)


class TitleTierStruct(TargetStruct):
    """The native 0x0C title-tier record."""

    _pack_ = 1
    _fields_ = [
        ("props", c_uint32),
        ("tier_number", c_uint32),
        ("tier_name_enc_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> TitleTierStruct:
        """Attach the reader used by the tier name pointer."""

        self._remote_reader = reader
        return self

    @property
    def is_valid(self) -> bool:
        """Return whether the tier number is populated."""

        return bool(int(self.tier_number))

    @property
    def name(self) -> str:
        """Read the bounded tier name."""

        return _read_target_text(self._remote_reader, int(self.tier_name_enc_ptr)) or ""

    @property
    def tier_name_ptr(self) -> int:
        """Compatibility alias for the source ``tier_name_enc_ptr`` field."""

        return int(self.tier_name_enc_ptr)

    @property
    def tier_name_encoded_str(self) -> str | None:
        return _read_target_text(self._remote_reader, int(self.tier_name_enc_ptr))

    @property
    def tier_name_str(self) -> str | None:
        return _format_encoded_text(self.tier_name_encoded_str)

    @property
    def is_percentage_based(self) -> bool:
        return bool(int(self.props) & 0x1)

class WorldContextStruct(TargetStruct):
    """The maintained fixed-width x86 ``WorldContext`` root layout.

    Every pointer is represented as a four-byte target address.  The array
    members are only headers; following their buffers is an explicit bounded
    operation on the bound snapshot.
    """

    _pack_ = 1
    _fields_ = [
        ("account_info_ptr", c_uint32),
        ("message_buff_array", GWArray),
        ("dialog_buff_array", GWArray),
        ("merch_items_array", GWArray),
        ("merch_items2_array", GWArray),
        ("accumMapInitUnk0", c_uint32),
        ("accumMapInitUnk1", c_uint32),
        ("accumMapInitOffset", c_uint32),
        ("accumMapInitLength", c_uint32),
        ("h0054", c_uint32),
        ("accumMapInitUnk2", c_uint32),
        ("h005C", c_uint32 * 8),
        ("map_agents_array", GWArray),
        ("party_allies_array", GWArray),
        ("all_flag_array", c_float * 3),
        ("h00A8", c_uint32),
        ("party_attributes_array", GWArray),
        ("h00BC", c_uint32 * 255),
        ("h04B8_array", GWArray),
        ("h04C8_array", GWArray),
        ("h04D8", c_uint32),
        ("h04DC_array", GWArray),
        ("h04EC", c_uint32 * 7),
        ("party_effects_array", GWArray),
        ("h0518_array", GWArray),
        ("active_quest_id", c_uint32),
        ("quest_log_array", GWArray),
        ("h053C", c_uint32 * 10),
        ("mission_objectives_array", GWArray),
        ("henchmen_agent_ids_array", GWArray),
        ("hero_flags_array", GWArray),
        ("hero_info_array", GWArray),
        ("cartographed_areas_array", GWArray),
        ("h05B4", c_uint32 * 2),
        ("controlled_minion_count_array", GWArray),
        ("missions_completed_array", GWArray),
        ("missions_bonus_array", GWArray),
        ("missions_completed_hm_array", GWArray),
        ("missions_bonus_hm_array", GWArray),
        ("unlocked_map_array", GWArray),
        ("h061C", c_uint32 * 2),
        ("player_morale_ptr", c_uint32),
        ("h028C", c_uint32),
        ("party_morale_array", GWArray),
        ("h063C", c_uint32 * 16),
        ("player_number", c_uint32),
        ("playerControlledChar_ptr", c_uint32),
        ("is_hard_mode_unlocked", c_uint32),
        ("h0688", c_uint32 * 2),
        ("salvage_session_id", c_uint32),
        ("h0694", c_uint32 * 5),
        ("playerTeamToken", c_uint32),
        ("pets_array", GWArray),
        ("party_profession_states_array", GWArray),
        ("h06CC_array", GWArray),
        ("h06DC", c_uint32),
        ("h06E0_array", GWArray),
        ("party_skillbar_array", GWArray),
        ("learnable_character_skills_array", GWArray),
        ("unlocked_character_skills_array", GWArray),
        ("duplicated_character_skills_array", GWArray),
        ("h0730_array", GWArray),
        ("experience", c_uint32),
        ("experience_dupe", c_uint32),
        ("current_kurzick", c_uint32),
        ("current_kurzick_dupe", c_uint32),
        ("total_earned_kurzick", c_uint32),
        ("total_earned_kurzick_dupe", c_uint32),
        ("current_luxon", c_uint32),
        ("current_luxon_dupe", c_uint32),
        ("total_earned_luxon", c_uint32),
        ("total_earned_luxon_dupe", c_uint32),
        ("current_imperial", c_uint32),
        ("current_imperial_dupe", c_uint32),
        ("total_earned_imperial", c_uint32),
        ("total_earned_imperial_dupe", c_uint32),
        ("unk_faction4", c_uint32),
        ("unk_faction4_dupe", c_uint32),
        ("unk_faction5", c_uint32),
        ("unk_faction5_dupe", c_uint32),
        ("level", c_uint32),
        ("level_dupe", c_uint32),
        ("morale", c_uint32),
        ("morale_dupe", c_uint32),
        ("current_balth", c_uint32),
        ("current_balth_dupe", c_uint32),
        ("total_earned_balth", c_uint32),
        ("total_earned_balth_dupe", c_uint32),
        ("current_skill_points", c_uint32),
        ("current_skill_points_dupe", c_uint32),
        ("total_earned_skill_points", c_uint32),
        ("total_earned_skill_points_dupe", c_uint32),
        ("max_kurzick", c_uint32),
        ("max_luxon", c_uint32),
        ("max_balth", c_uint32),
        ("max_imperial", c_uint32),
        ("equipment_status", c_uint32),
        ("agent_name_info_array", GWArray),
        ("h07DC_array", GWArray),
        ("mission_map_icons_array", GWArray),
        ("npc_models_array", GWArray),
        ("players_array", GWArray),
        ("titles_array", GWArray),
        ("title_tiers_array", GWArray),
        ("vanquished_areas_array", GWArray),
        ("foes_killed", c_uint32),
        ("foes_to_kill", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> WorldContextStruct:
        """Attach the reader and target address used by root properties."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    @property
    def address(self) -> int | None:
        """Return the target address from which this snapshot was read."""

        return self._remote_address

    @property
    def accum_map_init_unk0(self) -> int:
        return int(self.accumMapInitUnk0)

    @property
    def accum_map_init_unk1(self) -> int:
        return int(self.accumMapInitUnk1)

    @property
    def accum_map_init_offset(self) -> int:
        return int(self.accumMapInitOffset)

    @property
    def accum_map_init_length(self) -> int:
        return int(self.accumMapInitLength)

    @property
    def accum_map_init_unk2(self) -> int:
        return int(self.accumMapInitUnk2)

    @property
    def h0628(self) -> int:
        """Native-layout spelling for source field ``h028C``."""

        return int(self.h028C)

    @property
    def player_controlled_character_ptr(self) -> int:
        return int(self.playerControlledChar_ptr)

    @property
    def player_team_token(self) -> int:
        return int(self.playerTeamToken)

    @property
    def all_flag_value(self) -> tuple[float, float, float] | None:
        """Return the party flag coordinates when they are finite."""

        values = (
            float(self.all_flag_array[0]),
            float(self.all_flag_array[1]),
            float(self.all_flag_array[2]),
        )
        return values if all(math.isfinite(value) for value in values) else None

    @property
    def all_flag(self) -> Vec3f | None:
        """Return the party flag as the source ``Vec3f`` value."""

        values = self.all_flag_value
        if values is None:
            return None
        return Vec3f(*values)

    def _read_struct(
        self, address: int, structure_type: type[Structure]
    ) -> Structure | None:
        """Read one bounded pointed-to structure from the target process."""

        if address < 0x10000:
            return None
        if self._remote_reader is None:
            raise RuntimeError("WorldContext snapshot is not bound to a reader.")
        raw_value = self._remote_reader.read(address, ctypes.sizeof(structure_type))
        value = cast(Structure, structure_type.from_buffer_copy(raw_value))
        bind_reader = getattr(value, "bind_reader", None)
        if callable(bind_reader):
            bound_value = bind_reader(self._remote_reader, address)
            return cast(Structure, bound_value)
        return value

    @property
    def account_info(self) -> AccountInfoStruct | None:
        """Read the account summary record."""

        value = self._read_struct(int(self.account_info_ptr), AccountInfoStruct)
        return value if isinstance(value, AccountInfoStruct) else None

    @property
    def map_agents(self) -> list[MapAgentStruct] | None:
        """Read every map-agent status record in the source array."""

        return self._records("map_agents_array", MapAgentStruct)

    @property
    def party_allies(self) -> list[PartyAllyStruct] | None:
        """Read every party-ally record in the source array."""

        return self._records("party_allies_array", PartyAllyStruct)

    @property
    def merch_items(self) -> list[int] | None:
        """Read the current merchant item identifiers."""

        return self._array_values("merch_items_array", c_uint32)

    @property
    def merch_items2(self) -> list[int] | None:
        """Read the second merchant item identifier array."""

        return self._array_values("merch_items2_array", c_uint32)

    def _array_values(
        self,
        name: str,
        element_type: type[ctypes._SimpleCData],
    ) -> list[int] | None:
        """Read every scalar value in a validated source array."""

        if self._remote_reader is None:
            raise RuntimeError("WorldContext snapshot is not bound to a reader.")
        array = getattr(self, name)
        raw = _read_world_array_bytes(self._remote_reader, array, element_type)
        if raw is None:
            return None
        element_size = ctypes.sizeof(element_type)
        return [
            int(element_type.from_buffer_copy(raw, offset).value)
            for offset in range(0, len(raw), element_size)
        ]

    def _pointer_values(self, name: str) -> list[int] | None:
        """Read a source ``Array<void*>`` as target-width integer addresses."""

        return self._array_values(name, c_uint32)

    @property
    def h04B8_ptrs(self) -> list[int] | None:
        return self._pointer_values("h04B8_array")

    @property
    def h04C8_ptrs(self) -> list[int] | None:
        return self._pointer_values("h04C8_array")

    @property
    def h04DC_ptrs(self) -> list[int] | None:
        return self._pointer_values("h04DC_array")

    @property
    def h0518_ptrs(self) -> list[int | None] | None:
        values = self._pointer_values("h0518_array")
        return [value or None for value in values] if values else None

    @property
    def h06CC_ptrs(self) -> list[int] | None:
        return self._pointer_values("h06CC_array")

    @property
    def h06E0_ptrs(self) -> list[int] | None:
        return self._pointer_values("h06E0_array")

    @property
    def h0730_ptrs(self) -> list[int] | None:
        return self._pointer_values("h0730_array")

    @property
    def h07DC_ptrs(self) -> list[int] | None:
        return self._pointer_values("h07DC_array")

    def _records(
        self,
        name: str,
        element_type: type[_record_type],
    ) -> list[_record_type] | None:
        """Read every record in a validated source array."""

        if self._remote_reader is None:
            raise RuntimeError("WorldContext snapshot is not bound to a reader.")
        array = getattr(self, name)
        raw = _read_world_array_bytes(self._remote_reader, array, element_type)
        if raw is None:
            return None
        element_size = ctypes.sizeof(element_type)
        records: list[_record_type] = []
        for offset in range(0, len(raw), element_size):
            value = element_type.from_buffer_copy(raw, offset)
            bind_reader = getattr(value, "bind_reader", None)
            if callable(bind_reader):
                value = cast(
                    _record_type,
                    bind_reader(self._remote_reader, int(array.m_buffer) + offset),
                )
            records.append(value)
        return records

    @property
    def party_attributes(self) -> list[PartyAttributeStruct] | None:
        """Read every party attribute block in the source array."""

        return self._records("party_attributes_array", PartyAttributeStruct)

    @staticmethod
    def _is_valid_attribute(attribute: AttributeStruct) -> bool:
        return attribute.is_valid

    def get_attributes_by_agent_id(self, agent_id: int) -> list[AttributeStruct]:
        """Return populated attributes for one party agent."""

        for block in self.party_attributes or []:
            if int(block.agent_id) == agent_id:
                return [
                    attribute
                    for index, attribute in enumerate(block.attributes)
                    if index < 45 and self._is_valid_attribute(attribute)
                ]
        return []

    def get_party_attributes(self) -> dict[int, list[AttributeStruct]]:
        """Return populated attributes grouped by party agent identifier."""

        result: dict[int, list[AttributeStruct]] = {}
        for block in self.party_attributes or []:
            attributes = [
                attribute
                for index, attribute in enumerate(block.attributes)
                if index < 45 and self._is_valid_attribute(attribute)
            ]
            if attributes:
                result[int(block.agent_id)] = attributes
        return result

    @property
    def party_effects(self) -> list[AgentEffectsStruct] | None:
        """Read every party effect block in the source array."""

        return self._records("party_effects_array", AgentEffectsStruct)

    @property
    def henchmen_agent_ids(self) -> list[int] | None:
        """Read the source party henchman agent-id array."""

        return self._array_values("henchmen_agent_ids_array", c_uint32)

    @property
    def npc_models(self) -> list[NPCStruct] | None:
        """Read every NPC model record in the source array."""

        return self._records("npc_models_array", NPCStruct)

    @property
    def players(self) -> list[PlayerStruct] | None:
        """Read every player record in the source array."""

        return self._records("players_array", PlayerStruct)

    @property
    def hero_flags(self) -> list[HeroFlagStruct] | None:
        """Read every hero flag record in the source array."""

        return self._records("hero_flags_array", HeroFlagStruct)

    @property
    def hero_info(self) -> list[HeroInfoStruct] | None:
        """Read every hero record in the source array."""

        return self._records("hero_info_array", HeroInfoStruct)

    @property
    def controlled_minions(self) -> list[ControlledMinionsStruct] | None:
        """Read every controlled-minion record in the source array."""

        return self._records("controlled_minion_count_array", ControlledMinionsStruct)

    @property
    def pets(self) -> list[PetInfoStruct] | None:
        """Read every pet record in the source array."""

        return self._records("pets_array", PetInfoStruct)

    @property
    def skillbars(self) -> list[SkillbarStruct] | None:
        """Read every party skillbar record in the source array."""

        return self._records("party_skillbar_array", SkillbarStruct)

    @property
    def party_skillbars(self) -> list[SkillbarStruct] | None:
        """Return the source-compatible party-skillbar list."""

        return self.skillbars

    @property
    def party_profession_states(self) -> list[ProfessionStateStruct] | None:
        """Read every party profession-state record in the source array."""

        return self._records("party_profession_states_array", ProfessionStateStruct)

    @property
    def player_morale(self) -> PartyMemberMoraleInfoStruct | None:
        """Read the current player's morale record."""

        value = self._read_struct(int(self.player_morale_ptr), PartyMemberMoraleInfoStruct)
        return value if isinstance(value, PartyMemberMoraleInfoStruct) else None

    @property
    def party_morale(self) -> list[PartyMoraleLinkStruct] | None:
        """Read every party morale link in the source array."""

        return self._records("party_morale_array", PartyMoraleLinkStruct)

    @property
    def player_controlled_character(self) -> PlayerControlledCharacterStruct | None:
        """Read the current player-controlled-character record."""

        value = self._read_struct(
            int(self.player_controlled_character_ptr),
            PlayerControlledCharacterStruct,
        )
        return value if isinstance(value, PlayerControlledCharacterStruct) else None

    @property
    def learnable_character_skills(self) -> list[int] | None:
        """Read every learnable skill identifier in the source array."""

        return self._array_values("learnable_character_skills_array", c_uint32)

    @property
    def unlocked_character_skills(self) -> list[int] | None:
        """Read every unlocked-skill value in the source array."""

        return self._array_values("unlocked_character_skills_array", c_uint32)

    @property
    def duplicated_character_skills(self) -> list[DupeSkillStruct] | None:
        """Read every duplicate-skill record in the source array."""

        return self._records("duplicated_character_skills_array", DupeSkillStruct)

    @property
    def cartographed_areas(self) -> list[int | None] | None:
        """Read every cartographed-area identifier in the source array."""

        values = self._array_values("cartographed_areas_array", c_uint32)
        return [value or None for value in values] if values else None

    @property
    def missions_completed(self) -> list[int] | None:
        """Read every completed-mission identifier in the source array."""

        return self._array_values("missions_completed_array", c_uint32)

    @property
    def missions_bonus(self) -> list[int] | None:
        """Read every completed-bonus identifier in the source array."""

        return self._array_values("missions_bonus_array", c_uint32)

    @property
    def missions_completed_hm(self) -> list[int] | None:
        """Read every hard-mode completed-mission identifier in the source array."""

        return self._array_values("missions_completed_hm_array", c_uint32)

    @property
    def missions_bonus_hm(self) -> list[int] | None:
        """Read every hard-mode completed-bonus identifier in the source array."""

        return self._array_values("missions_bonus_hm_array", c_uint32)

    @property
    def unlocked_maps(self) -> list[int] | None:
        """Read every unlocked-map identifier in the source array."""

        return self._array_values("unlocked_map_array", c_uint32)

    @property
    def quests(self) -> list[QuestStruct] | None:
        """Read every quest-log record in the source array."""

        return self._records("quest_log_array", QuestStruct)

    @property
    def quest_log(self) -> list[QuestStruct] | None:
        """Expose the quest list under Reforged's source property name."""

        return self.quests

    @property
    def mission_objectives(self) -> list[MissionObjectiveStruct] | None:
        """Read every mission-objective record in the source array."""

        return self._records("mission_objectives_array", MissionObjectiveStruct)

    @property
    def titles(self) -> list[TitleStruct] | None:
        """Read every title-progress record in the source array."""

        return self._records("titles_array", TitleStruct)

    @property
    def title_tiers(self) -> list[TitleTierStruct] | None:
        """Read every title-tier record in the source array."""

        return self._records("title_tiers_array", TitleTierStruct)

    @property
    def agent_name_info(self) -> list[AgentNameInfoStruct] | None:
        """Read every agent-name pointer record in the source array."""

        return self._records("agent_name_info_array", AgentNameInfoStruct)

    @property
    def mission_map_icons(self) -> list[MissionMapIconStruct] | None:
        """Read every mission-map icon record in the source array."""

        return self._records("mission_map_icons_array", MissionMapIconStruct)

    @property
    def vanquished_areas(self) -> list[int] | None:
        """Return the source accessor's current result.

        Reforged's ``WorldContext.py`` currently returns ``None`` before its
        array-reading code, so preserve that behavior even though the native
        root declares ``vanquished_areas_array``.
        """

        return None

    def get_player_by_id(self, player_id: int) -> PlayerStruct | None:
        """Return the player whose source ``player_number`` matches the ID."""

        for player in self.players or []:
            if int(player.player_number) == player_id:
                return player
        return None

    def GetPlayerById(self, player_id: int) -> PlayerStruct | None:
        """Return the Reforged compatibility spelling."""

        return self.get_player_by_id(player_id)

    @property
    def message_buffer(self) -> str:
        """Read the bounded UTF-16 message buffer as one display string."""

        values = self._array_values("message_buff_array", c_uint16) or []
        return bytes().join(int(value).to_bytes(2, "little") for value in values).decode(
            "utf-16-le", errors="replace"
        ).split("\x00", 1)[0]

    @property
    def message_buff(self) -> list[str] | None:
        """Return the source character-list form of the message buffer."""

        values = self._array_values("message_buff_array", c_uint16)
        if not values:
            return None
        return [chr(value) for value in values]

    @property
    def dialog_buffer(self) -> str:
        """Read the bounded UTF-16 dialog buffer as one display string."""

        values = self._array_values("dialog_buff_array", c_uint16) or []
        return bytes().join(int(value).to_bytes(2, "little") for value in values).decode(
            "utf-16-le", errors="replace"
        ).split("\x00", 1)[0]

    @property
    def dialog_buff(self) -> list[str] | None:
        """Return the source character-list form of the dialog buffer."""

        values = self._array_values("dialog_buff_array", c_uint16)
        if not values:
            return None
        return [chr(value) for value in values]

    @property
    def array_sizes(self) -> dict[str, int]:
        """Return advertised sizes for every root ``GWArray`` field."""

        result: dict[str, int] = {}
        for field in self._fields_:
            field_name, field_type = field[0], field[1]
            if field_type is GWArray:
                array = getattr(self, field_name)
                result[field_name] = int(array.m_size)
        return result


assert ctypes.sizeof(Vec3fStruct) == 0x0C
assert ctypes.sizeof(Vec2fStruct) == 0x08
assert ctypes.sizeof(AccountInfoStruct) == 0x1C
assert ctypes.sizeof(MapAgentStruct) == 0x34
assert ctypes.sizeof(PartyAllyStruct) == 0x0C
assert ctypes.sizeof(AttributeStruct) == 0x14
assert ctypes.sizeof(PartyAttributeStruct) == 0x43C
assert ctypes.sizeof(EffectStruct) == 0x18
assert ctypes.sizeof(BuffStruct) == 0x10
assert ctypes.sizeof(AgentEffectsStruct) == 0x24
assert ctypes.sizeof(NPC_ModelStruct) == 0x30
assert ctypes.sizeof(PlayerStruct) == 0x50
assert ctypes.sizeof(HeroFlagStruct) == 0x24
assert ctypes.sizeof(HeroInfoStruct) == 0x78
assert ctypes.sizeof(ControlledMinionsStruct) == 0x08
assert ctypes.sizeof(PartyMemberMoraleInfoStruct) == 0x1C
assert ctypes.sizeof(PartyMoraleLinkStruct) == 0x0C
assert ctypes.sizeof(PlayerControlledCharacterStruct) == 0x134
assert ctypes.sizeof(ProfessionStateStruct) == 0x14
assert ctypes.sizeof(PetInfoStruct) == 0x1C
assert ctypes.sizeof(SkillbarSkillStruct) == 0x14
assert ctypes.sizeof(SkillbarStruct) == 0xBC
assert ctypes.sizeof(DupeSkillStruct) == 0x08
assert ctypes.sizeof(AgentNameInfoStruct) == 0x38
assert ctypes.sizeof(MissionMapIconStruct) == 0x28
assert ctypes.sizeof(GamePosStruct) == 0x0C
assert ctypes.sizeof(QuestStruct) == 0x34
assert ctypes.sizeof(MissionObjectiveStruct) == 0x0C
assert ctypes.sizeof(TitleStruct) == 0x2C
assert ctypes.sizeof(TitleTierStruct) == 0x0C
assert ctypes.sizeof(WorldContextStruct) == 0x854
assert WorldContextStruct.message_buff_array.offset == 0x04
assert WorldContextStruct.party_effects_array.offset == 0x508
assert WorldContextStruct.players_array.offset == 0x80C
assert WorldContextStruct.foes_killed.offset == 0x84C

# Previous Stealth spelling retained as an alias for the source class.
NPCStruct = NPC_ModelStruct


class WorldContext:
    """Resolve and read the current ``WorldContext`` through ``GameContext``."""

    _ptr: int = 0
    _cached_ctx: WorldContextStruct | None = None
    _callback_name = "WorldContext.UpdatePtr"

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the selected client's cached game context."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current world-context address, if the client has one."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.world_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> WorldContextStruct | None:
        """Read the complete maintained root layout without child arrays."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(WorldContextStruct))
        return WorldContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )

    @staticmethod
    def get_ptr() -> int:
        """Return the most recently refreshed source-compatible address."""

        return WorldContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the external facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            WorldContext._ptr = 0
            WorldContext._cached_ctx = None
            return
        try:
            context = client.world_context
            address = context.resolve_address()
            WorldContext._ptr = address or 0
            WorldContext._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            WorldContext._ptr = 0
            WorldContext._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare source callback registration, which requires in-client code."""

        raise NotImplementedError(
            "WorldContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade snapshot and address."""

        WorldContext._ptr = 0
        WorldContext._cached_ctx = None

    @staticmethod
    def get_context() -> WorldContextStruct | None:
        """Return the most recently refreshed external snapshot."""

        return WorldContext._cached_ctx


def get() -> WorldContextStruct | None:
    """Read the current client's world context, if one is connected."""

    from ..client import current_client

    client = current_client()
    return client.read_world_context() if client is not None else None
