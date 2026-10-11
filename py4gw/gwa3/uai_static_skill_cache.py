"""GwAu3's ``UtilityAI_StaticSkillCache.au3``: the skillbar's skill data, read when it is asked for.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the file is.** GwAu3 fills a 9x43 table once per skillbar change -- ``UAI_CacheSkillBar`` walks the
eight slots, asks ``Skill_GetSkillbarInfo`` for each slot's skill id, reads that skill's record through a
43-field structure, and stores the row; ``UAI_GetStaticSkillInfo(slot, column)`` then answers from the
table. It is how the whole plugin knows what its own skills *are*: the slot loop's first read, the
priority test, and every per-skill decision behind them.

**What this port does instead, and it is the same one substitution the rest of the layer makes.** There
is no frame loop here and nothing to dispatch to, so there is no table to fill and no staleness to
manage: `UAI_GetStaticSkillInfo` reads the slot's skill id from the live skillbar (routed in
`py4gw/gwa3/data_skill.py`) and that skill's field from the client's own skill record, at the point of
use. A caller sees one number either way -- GwAu3's answer from a row it filled a moment ago, this
layer's answer from the same record now -- and the *values* are the source's, including the three
transformations the source performs while caching rather than while reading (see `_transform`).

**Three of the source's own quirks are kept**, because each one is what a caller observes:

* the row has **43** columns while the enum declares **44** names, and the guard refuses 43
  (``:210``) -- so ``Description``, the last name, can never be read and was never copied
  (``:144`` clamps the copy at ``42``). It answers ``0`` here for the same reason;
* the plugin's ``Name`` column is the dword at struct ``+0x98``, which GwAu3's own data module calls
  ``NameID`` (``GwAu3_Data_Skill.au3:143-144``) -- the same word under two names, and this layer reads it
  through the skill key that exists;
* the copy stops at column 42 and the eleven ``Description``-adjacent fields GwAu3's structure declares
  past it are simply not part of the row.

**`UAI_CacheSkillBar` is the one member that has nothing to do here, and it says so.** It is a script's
"refresh my skillbar data" call and it is called from GwAu3's own examples. The data it fills is
answered live by the two accessors above, so the only observable effects it has in this port are its
own **failure paths** -- which are reproduced, because a script branches on them: no skillbar array, or
no controlled character, answers ``False`` exactly as the source does (``:119``, ``:122``). On success
it answers ``None``, which is what the source's own ``EndFunc`` without a value answers a caller.
"""

from __future__ import annotations

from typing import Any

from . import constants as _constants
from .data_agent import Agent_GetMyID
from .data_skill import Skill_GetSkillInfo, Skill_GetSkillbarInfo

__all__ = [
    "UAI_CacheSkillBar",
    "UAI_GetStaticSkillInfo",
    "UAI_SlotIsPriority",
    "UAI_StaticDataSkill",
]

#: ``{column value: the skill-table key that answers it}``, read from the generated constants module so
#: the numbers come from GwAu3's own ``Global Enum`` rather than from a transcription of it.
#:
#: **One alias, and it is a name difference between two GwAu3 files rather than a choice here**: the
#: plugin's ``$GC_UAI_STATIC_SKILL_Name`` is the dword at ``+0x98``, which the data module spells
#: ``NameID`` (``GwAu3_Data_Skill.au3:143-144``). The column keeps GwAu3's key string; the read uses the
#: key this layer has.
_KEY_ALIASES: dict[str, str] = {"Name": "NameID"}

_STATIC_SKILL_FIELDS: dict[int, str] = {
    getattr(_constants, name): _KEY_ALIASES.get(name[len("GC_UAI_STATIC_SKILL_") :], name[len("GC_UAI_STATIC_SKILL_") :])
    for name in _constants.__all__
    if name.startswith("GC_UAI_STATIC_SKILL_")
}

#: The last column the source can answer: its table is ``[9][43]`` and its guard refuses ``> 42``
#: (``:5``, ``:210``).
_LAST_COLUMN = 42

_OVERCAST_KEEP = (5, 10)
_ENERGY_COST_OVERRIDES = {11: 15, 12: 25}


def _column_key(info_type: Any) -> str:
    """The skill-table key for a ``$GC_UAI_STATIC_SKILL_*`` column, or ``""`` when there is none."""

    return _STATIC_SKILL_FIELDS.get(int(info_type), "")


def _transform(info_type: Any, value: Any) -> Any:
    """The three conversions the source performs **while caching** (``:150-171``).

    They are part of the value a caller reads, so a port that reads live has to perform them too, in the
    same place in the sequence:

    * ``Overcast`` keeps ``5`` and ``10`` and zeroes anything else -- GwAu3's ``Switch`` with a
      ``Case Else`` of ``0``;
    * ``EnergyCost`` maps ``11`` to ``15`` and ``12`` to ``25`` (the two pip costs), leaving the rest;
    * ``Aftercast`` is multiplied by ``1000``, the source's conversion from seconds to milliseconds.
    """

    overcast = _constants.GC_UAI_STATIC_SKILL_Overcast
    energy_cost = _constants.GC_UAI_STATIC_SKILL_EnergyCost
    aftercast = _constants.GC_UAI_STATIC_SKILL_Aftercast

    if int(info_type) == overcast:
        return int(value) if int(value) in _OVERCAST_KEEP else 0
    if int(info_type) == energy_cost:
        return _ENERGY_COST_OVERRIDES.get(int(value), value)
    if int(info_type) == aftercast:
        return value * 1000
    return value


def UAI_GetStaticSkillInfo(slot: Any, info_type: Any) -> Any:
    """One column of one skillbar slot's skill (``UtilityAI_StaticSkillCache.au3:208-212``).

    GwAu3 answers it from its table; this layer answers it from the live slot and the live skill record,
    which is the same two reads its cache used -- the slot's ``SkillID`` then that skill's field. The
    guards are the source's, in its order: a slot outside ``1..8`` answers ``0``, a column outside
    ``0..42`` answers ``0``, and an **empty slot answers ``0``** -- which is what the source's zeroed row
    holds (``:113``, ``:138``).
    """

    if slot < 1 or slot > 8:
        return 0
    if info_type < 0 or info_type > _LAST_COLUMN:
        return 0

    key = _column_key(info_type)
    if key == "":
        return 0

    skill_id = Skill_GetSkillbarInfo(slot, "SkillID")
    if skill_id == 0:
        return 0

    return _transform(info_type, Skill_GetSkillInfo(skill_id, key))


def UAI_StaticDataSkill(skill_id: Any) -> list[Any]:
    """A skill's whole 43-column row (``UtilityAI_StaticSkillCache.au3:56-107``).

    The source reads the client's skill record through a structure of exactly these fields and returns it
    as an array; that array is what `UAI_CacheSkillBar` copies into its table. Here the row is built from
    the same skill record through this layer's per-field reader, in the enum's own column order, with the
    same three conversions applied.

    **A skill the client does not hold answers an all-zero row rather than raising**, which is the
    source's own path: its ``Skill_GetSkillPtr`` answers ``0`` for an id outside the table and its
    ``SetError(1, 0, 0)`` is read by the caller as "skip this slot" (``:104``, ``:141``).
    """

    row: list[Any] = []
    for column in range(_LAST_COLUMN + 1):
        key = _column_key(column)
        if key == "":
            row.append(0)
            continue
        value = Skill_GetSkillInfo(skill_id, key)
        row.append(_transform(column, value))
    return row


def UAI_SlotIsPriority(slot: Any) -> bool:
    """Whether an already-read slot is a priority skill (``UtilityAI_StaticSkillCache.au3:185-206``).

    Three groups of flags over three columns, in the source's order: any ``Special`` flag
    (resurrection, elite, PvE), then any ``Effect2`` flag (energy steal, energy gain, hex removal,
    condition removal), then an exact ``SkillType`` match (well, glyph, preparation, item spell). The
    slot's skill is read the same way `UAI_GetStaticSkillInfo` reads it, so this is a live test of the
    live skillbar rather than of a cached row.
    """

    special_flags = (
        _constants.GC_I_SKILL_SPECIAL_FLAG_RESURRECTION,
        _constants.GC_I_SKILL_SPECIAL_FLAG_ELITE,
        _constants.GC_I_SKILL_SPECIAL_FLAG_PVE,
    )
    effect2_flags = (
        _constants.GC_I_SKILL_EFFECT2_ENERGY_STEAL,
        _constants.GC_I_SKILL_EFFECT2_ENERGY_GAIN,
        _constants.GC_I_SKILL_EFFECT2_HEX_REMOVAL,
        _constants.GC_I_SKILL_EFFECT2_CONDITION_REMOVAL,
    )
    priority_types = (
        _constants.GC_I_SKILL_TYPE_WELL,
        _constants.GC_I_SKILL_TYPE_GLYPH,
        _constants.GC_I_SKILL_TYPE_PREPARATION,
        _constants.GC_I_SKILL_TYPE_ITEM_SPELL,
    )

    special = int(UAI_GetStaticSkillInfo(slot, _constants.GC_UAI_STATIC_SKILL_Special))
    effect2 = int(UAI_GetStaticSkillInfo(slot, _constants.GC_UAI_STATIC_SKILL_Effect2))
    skill_type = int(UAI_GetStaticSkillInfo(slot, _constants.GC_UAI_STATIC_SKILL_SkillType))

    for flag in special_flags:
        if special & flag:
            return True
    for flag in effect2_flags:
        if effect2 & flag:
            return True
    for priority_type in priority_types:
        if skill_type == priority_type:
            return True

    return False


def UAI_CacheSkillBar() -> Any:
    """**NOT APPLICABLE in this port: the data it fills is read when it is asked for.**

    This is the member GwAu3's own examples call to refresh the static skillbar table
    (``UtilityAI_StaticSkillCache.au3:109-181``), and it is kept because a migrating script calls it --
    but what it *does* in GwAu3 is fill ``$g_amx2_StaticSkillCache``, and this layer has no such table:
    `UAI_GetStaticSkillInfo` and `UAI_StaticDataSkill` read the live skillbar and the live skill record
    at the point of use, so there is nothing a refresh could make fresher.

    **Its two failure paths are reproduced, because a script branches on them.** No skillbar array, or no
    controlled character, answers ``False`` exactly as the source does (``:119``, ``:122``); on success it
    answers ``None``, which is what the source's own ``EndFunc`` without a value answers. A caller that
    checks the result -- as GwAu3's examples do -- gets the same answer for the same situation, and a
    caller that does not is unaffected by the missing table, because the table's *contents* are answered
    live by the two accessors above.

    This is a documented divergence, not a stand-in: the cache is the one GwAu3 mechanism this project's
    execution model does not have (``docs/GWA3_COMPAT_SPEC.md``, *Caching*), and the layer states it on
    the member rather than shipping a table that would go stale for the same reason a TTL would.
    """

    # The two preconditions the source checks before it fills anything (`:117-122`).
    from ..client import require_client

    world = require_client().read_world_context()
    if world is None:
        return False
    if int(world.party_skillbar_array.m_size) == 0:
        return False
    if Agent_GetMyID() == 0:
        return False

    return None
