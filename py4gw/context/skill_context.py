"""External read-only reader for the client's skill constant table.

**Source:** native ``GW::Context::GetSkillArray()`` (``context_methods.cpp:148-150``) returns
``g_skill_array_addr``, and the game's own accessor indexes that array with the record's own size.
The function this project's catalog resolves as ``skillbar.skill_array_addr`` is that accessor's
callee — verified offline against ``F:\\GW\\GW1\\Gw.exe`` with ``tools/resolve_offline.py`` and a
byte read, and it is the whole of the addressing:

```asm
005a8d20  55                push ebp
005a8d21  8b ec             mov  ebp, esp
005a8d23  56                push esi
005a8d24  8b 75 08          mov  esi, [ebp+8]        ; esi = skill_id
005a8d27  81 fe 94 0d 00 00 cmp  esi, 0xD94          ; the table's own bound (3476)
005a8d2d  72 14             jb   +0x14
...        (the client's own assert)
005a8d40  69 c6 a4 00 00 00 imul eax, esi, 0xA4     ; eax = skill_id * sizeof(Skill)
005a8d46  5e                pop  esi
005a8d47  05 70 a3 98 00    add  eax, 0x98A370       ; eax = &skill_array[skill_id]
005a8d4c  5d                pop  ebp
005a8d4d  c3                ret
```

So the table is static data the client compiles in — ``0x98A370`` is in ``.rdata``, the records are
``0xA4`` bytes apart, and the first word of each record is its own skill id (checked: records 0..11
begin ``0, 1, 2, … 11``). Reading it needs no call, no hook and no state.

**The record.** ``py4gw/context/skill_context.py`` declares ``SkillStruct`` from native
``include/GW/context/skill.h`` (``static_assert(sizeof(Skill) == 0xA4)``). The declaration was
checked field by field against the client's own bytes for skills with known data: strides of
``0xA4``, ``campaign``/``type``/``special`` at ``0x08``/``0x0C``/``0x10`` (Power Block and Mantra of
Celerity carry the elite bit ``0x4``), the byte-packed ``profession``/``attribute``/``title`` at
``0x28``, ``energy_cost`` at ``0x35`` with the client's own ``11 → 15`` and ``12 → 25`` encoding
(Meteor Shower reads ``0x0C``), ``health_cost`` at ``0x36`` (Blood Renewal reads ``0x0F``, its 15%
sacrifice), ``overcast`` at ``0x34`` **only where ``special & 0x1``** — the 25 records that carry
that bit are exactly the exhaustion skills (Gale, Earthquake, Meteor Shower, …) — ``activation`` at
``0x3C`` (Healing Signet reads ``2.0``), ``recharge`` at ``0x4C`` (Meteor Shower reads ``60``), and
the name/short-description/description string ids at ``0x98``/``0x9C``/``0xA0``.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import c_float, c_uint8, c_uint16, c_uint32
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the skill-table reader."""


#: ``sizeof(GW::Context::Skill)`` — the stride the client's own accessor multiplies by.
SKILL_RECORD_SIZE = 0xA4

#: The bound the client's accessor asserts against (``cmp esi, 0xD94`` at ``005a8d27``): the table
#: holds 3476 records. The client's function asserts; this reader refuses the read instead, which is
#: the project's rule for an address range before interpreting it.
SKILL_ARRAY_LENGTH = 0xD94

#: ``GW::Constants::unused_skill_ids`` (``common/constants/skills.h``), as the client's own ids: 64
#: entries in the header's order — ``2511..2539``, then ``1380, 1580, 1581``, ``2303..2325``, then
#: ``11, 1299, 1292, 1413, 1412, 1290, 775, 1578, 1125``.
UNUSED_SKILL_IDS = frozenset(
    (
        *range(2511, 2540),
        1380,
        1580,
        1581,
        *range(2303, 2326),
        11,
        1299,
        1292,
        1413,
        1412,
        1290,
        775,
        1578,
        1125,
    )
)


class SkillStruct(TargetStruct):
    """The native ``GW::Context::Skill`` record (``skill.h:17-87``): 0xA4 bytes, statically laid out."""

    _pack_ = 1
    _fields_ = [
        ("skill_id", c_uint32),
        ("h0004", c_uint32),
        ("campaign", c_uint32),
        ("type", c_uint32),
        ("special", c_uint32),
        ("combo_req", c_uint32),
        ("effect1", c_uint32),
        ("condition", c_uint32),
        ("effect2", c_uint32),
        ("weapon_req", c_uint32),
        ("profession", c_uint8),
        ("attribute", c_uint8),
        ("title", c_uint16),
        ("skill_id_pvp", c_uint32),
        ("combo", c_uint8),
        ("target", c_uint8),
        ("h0032", c_uint8),
        ("skill_equip_type", c_uint8),
        ("overcast", c_uint8),
        ("energy_cost", c_uint8),
        ("health_cost", c_uint8),
        ("h0037", c_uint8),
        ("adrenaline", c_uint32),
        ("activation", c_float),
        ("aftercast", c_float),
        ("duration0", c_uint32),
        ("duration15", c_uint32),
        ("recharge", c_uint32),
        ("h0050", c_uint16 * 4),
        ("skill_arguments", c_uint32),
        ("scale0", c_uint32),
        ("scale15", c_uint32),
        ("bonus_scale0", c_uint32),
        ("bonus_scale15", c_uint32),
        ("aoe_range", c_float),
        ("const_effect", c_float),
        ("caster_overhead_animation_id", c_uint32),
        ("caster_body_animation_id", c_uint32),
        ("target_body_animation_id", c_uint32),
        ("target_overhead_animation_id", c_uint32),
        ("projectile_animation_1_id", c_uint32),
        ("projectile_animation_2_id", c_uint32),
        ("icon_file_id", c_uint32),
        ("icon_file_id_2", c_uint32),
        ("icon_file_id_hi_res", c_uint32),
        ("name", c_uint32),
        ("concise", c_uint32),
        ("description", c_uint32),
    ]

    def GetEnergyCost(self) -> int:
        """``Skill::GetEnergyCost`` (``skill.h:67-73``): ``11 → 15``, ``12 → 25``, else the byte."""

        if self.energy_cost == 11:
            return 15
        if self.energy_cost == 12:
            return 25
        return int(self.energy_cost)

    def IsTouchRange(self) -> bool:
        """``Skill::IsTouchRange`` (``skill.h:75``)."""

        return (int(self.special) & 0x2) != 0

    def IsElite(self) -> bool:
        """``Skill::IsElite`` (``skill.h:76``)."""

        return (int(self.special) & 0x4) != 0

    def IsHalfRange(self) -> bool:
        """``Skill::IsHalfRange`` (``skill.h:77``)."""

        return (int(self.special) & 0x8) != 0

    def IsPvP(self) -> bool:
        """``Skill::IsPvP`` (``skill.h:78``)."""

        return (int(self.special) & 0x400000) != 0

    def IsPvE(self) -> bool:
        """``Skill::IsPvE`` (``skill.h:79``)."""

        return (int(self.special) & 0x80000) != 0

    def IsPlayable(self) -> bool:
        """``Skill::IsPlayable`` (``skill.h:80``) — the flag is inverted."""

        return (int(self.special) & 0x2000000) == 0

    def IsStacking(self) -> bool:
        """``Skill::IsStacking`` (``skill.h:83``)."""

        return (int(self.special) & 0x10000) != 0

    def IsNonStacking(self) -> bool:
        """``Skill::IsNonStacking`` (``skill.h:84``)."""

        return (int(self.special) & 0x20000) != 0

    def IsUnused(self) -> bool:
        """``Skill::IsUnused`` (``skill.cpp:11-18``): membership in ``unused_skill_ids``.

        The list is ``GW::Constants::unused_skill_ids`` (``common/constants/skills.h``), 64 entries
        in the header's own order — ``2511..2539``, then ``1380, 1580, 1581``, ``2303..2325``, then
        ``11, 1299, 1292, 1413, 1412, 1290, 775, 1578, 1125``.
        """

        return int(self.skill_id) in UNUSED_SKILL_IDS


assert ctypes.sizeof(SkillStruct) == SKILL_RECORD_SIZE
assert SkillStruct.skill_id.offset == 0x00
assert SkillStruct.campaign.offset == 0x08
assert SkillStruct.type.offset == 0x0C
assert SkillStruct.special.offset == 0x10
assert SkillStruct.profession.offset == 0x28
assert SkillStruct.attribute.offset == 0x29
assert SkillStruct.title.offset == 0x2A
assert SkillStruct.skill_id_pvp.offset == 0x2C
assert SkillStruct.skill_equip_type.offset == 0x33
assert SkillStruct.overcast.offset == 0x34
assert SkillStruct.energy_cost.offset == 0x35
assert SkillStruct.health_cost.offset == 0x36
assert SkillStruct.adrenaline.offset == 0x38
assert SkillStruct.activation.offset == 0x3C
assert SkillStruct.aftercast.offset == 0x40
assert SkillStruct.duration0.offset == 0x44
assert SkillStruct.duration15.offset == 0x48
assert SkillStruct.recharge.offset == 0x4C
assert SkillStruct.h0050.offset == 0x50
assert SkillStruct.skill_arguments.offset == 0x58
assert SkillStruct.scale0.offset == 0x5C
assert SkillStruct.scale15.offset == 0x60
assert SkillStruct.bonus_scale0.offset == 0x64
assert SkillStruct.bonus_scale15.offset == 0x68
assert SkillStruct.aoe_range.offset == 0x6C
assert SkillStruct.const_effect.offset == 0x70
assert SkillStruct.caster_overhead_animation_id.offset == 0x74
assert SkillStruct.icon_file_id.offset == 0x8C
assert SkillStruct.icon_file_id_2.offset == 0x90
assert SkillStruct.icon_file_id_hi_res.offset == 0x94
assert SkillStruct.name.offset == 0x98
assert SkillStruct.concise.offset == 0x9C
assert SkillStruct.description.offset == 0xA0


class SkillConstantArray:
    """The client's skill constant table: resolve the array once, read a record per call."""

    _RESOLVER = "skillbar.skill_array_addr"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader backed by one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._array_address: int | None = None

    def initialize(self) -> int | None:
        """Scan once and cache the table's base address, which is static data."""

        if self._array_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._array_address = result.value
        return self._array_address or None

    def resolve_address(self) -> int | None:
        """Return the cached table address, if it is available."""

        if self._array_address is None:
            return self.initialize()
        return self._array_address or None

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the cached table address, if initialized."""

        return self._array_address

    def read(self, skill_id: int) -> SkillStruct | None:
        """Read one ``Skill`` record, or ``None`` when the id or the read is out of range.

        ``None`` is the source's own null: native ``GetSkillConstantData`` (``skillbar_methods.cpp``
        :73-76) answers null for a missing array, and the binding behind Reforged's ``Skill`` then
        leaves its fields at their defaults. The bound is the client's (``SKILL_ARRAY_LENGTH``).
        """

        address = self.resolve_address()
        if address is None:
            return None
        if skill_id < 0 or skill_id >= SKILL_ARRAY_LENGTH:
            return None
        try:
            raw = self._reader.read(address + skill_id * SKILL_RECORD_SIZE, SKILL_RECORD_SIZE)
        except OSError:
            return None
        return SkillStruct.from_buffer_copy(raw)
