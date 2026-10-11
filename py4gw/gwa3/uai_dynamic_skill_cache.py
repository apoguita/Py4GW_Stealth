"""GwAu3's ``Cache/UtilityAI_DynamicSkillCache.au3``: a skillbar slot's live words.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the file is, and what this port does instead.** GwAu3 fills a 9x7 table once per frame from the
skillbar -- ``UAI_CacheDynamicSkillbarInfo`` reads eight fixed records (``0x14`` each, at
``$g_p_StaticSkillbarPtr + 0x4``) and stores each slot's adrenaline, skill id, event word and **recharge**
state, which it computes from the slot's timestamp and the client's skill timer.
``UAI_GetDynamicSkillInfo(slot, column)`` then answers from that table. There is no frame loop here, so
there is no table: the same slot is read when it is asked for, from the same record -- this layer's
skillbar read, `py4gw/gwa3/data_skill.py`'s `Skill_GetSkillbarInfo`, which walks the **same** structure at
the **same** two strides.

**The record is the same record, and the arithmetic is the same arithmetic.** GwAu3's struct template
(``:18-24``) declares ``Adrenaline`` at ``+0x0``, ``AdrenalineB`` at ``+0x4``, ``Timestamp`` at ``+0x8``,
``SkillID`` at ``+0xC`` and ``Event`` at ``+0x10`` -- which are `SkillbarSkillStruct`'s own fields, in the
same order, at the same offsets (`py4gw/context/world_context.py:1059-1069`). And its recharge pair is
``Utils_MakeInt32(timestamp) - Utils_MakeInt32(Skill_GetSkillTimer())``, clamped at zero (``:55-62``): the
same signed subtraction `Skill_GetSkillbarInfo`'s ``RechargeTime``/``IsRecharged`` keys make, over the
same routed timer.
"""

from __future__ import annotations

from typing import Any

from . import constants as _constants
from .data_skill import Skill_GetSkillbarInfo, Skill_GetSkillTimer

__all__ = [
    "UAI_CacheDynamicSkillbarInfo",
    "UAI_GetDynamicSkillInfo",
    "UAI_GetDynamicSkillStruct",
]

#: ``{column value: the field of `SkillbarSkillStruct` that answers it}``, read from the generated
#: constants module so the numbers come from GwAu3's own ``Global Enum``.
#:
#: The four are *read*; ``IsRecharged`` and ``RechargeTime`` are computed below, which is what GwAu3's
#: own fill does with them.
_READ_COLUMNS: dict[int, str] = {
    _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline: "adrenaline_a",
    _constants.GC_UAI_DYNAMIC_SKILL_AdrenalineB: "adrenaline_b",
    _constants.GC_UAI_DYNAMIC_SKILL_SkillID: "skill_id",
    _constants.GC_UAI_DYNAMIC_SKILL_Event: "event",
}

_SLOTS = 8


def _slot(skill_slot: Any) -> Any:
    """The live skillbar slot record, or ``None`` for a slot number outside ``1..8``.

    GwAu3 reads it out of ``$g_p_StaticSkillbarPtr + 0x4`` with a fixed stride; this layer asks its own
    skillbar reader for the slot, which is the same record the same walk reaches.
    """

    if int(skill_slot) < 1 or int(skill_slot) > _SLOTS:
        return None

    from ..client import require_client

    world = require_client().read_world_context()
    if world is None:
        return None

    skillbars = world.skillbars
    if not skillbars:
        return None

    from .data_agent import Agent_GetMyID

    mine = int(Agent_GetMyID())
    for skillbar in skillbars:
        if int(skillbar.agent_id) == mine:
            return skillbar.skills[int(skill_slot) - 1]
    return None


def _signed(value: int) -> int:
    """``Utils_MakeInt32``: the same 32-bit word read as a signed integer (``:38``, ``:55``)."""

    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


def UAI_GetDynamicSkillInfo(skill_slot: Any, info_type: Any) -> Any:
    """One column of one slot's live words (``UtilityAI_DynamicSkillCache.au3:68-72``).

    GwAu3's guards, in its order: a slot outside ``1..8`` answers ``0`` and a column outside
    ``0..$GC_UAI_DYNAMIC_SKILL_COUNT-1`` answers ``0`` (``:69-70``) -- and they answer **before** the
    record is touched, which is the order the source has.

    The two recharge columns are the source's own computation, not a field: ``IsRecharged`` is true when
    the slot's timestamp is ``0`` **or** the signed remaining time is not positive, and ``RechargeTime``
    is that remaining time when it is positive and ``0`` otherwise (``:49-62``).
    """

    if info_type < 0 or info_type >= _constants.GC_UAI_DYNAMIC_SKILL_COUNT:
        return 0

    record = _slot(skill_slot)
    if record is None:
        return 0

    if info_type == _constants.GC_UAI_DYNAMIC_SKILL_IsRecharged:
        timestamp = int(record.recharge)
        if timestamp == 0:
            return True
        return (_signed(timestamp) - _signed(int(Skill_GetSkillTimer()))) <= 0

    if info_type == _constants.GC_UAI_DYNAMIC_SKILL_RechargeTime:
        timestamp = int(record.recharge)
        if timestamp == 0:
            return 0
        remaining = _signed(timestamp) - _signed(int(Skill_GetSkillTimer()))
        if remaining <= 0:
            return 0
        return remaining

    field = _READ_COLUMNS.get(int(info_type))
    if field is None:
        return 0

    if field == "adrenaline_a":
        return int(record.adrenaline_a)
    if field == "adrenaline_b":
        return int(record.adrenaline_b)
    if field == "skill_id":
        return int(record.skill_id)
    return int(record.event)


def UAI_CacheDynamicSkillbarInfo() -> Any:
    """**NOT APPLICABLE in this port: the table it fills is read when it is asked for.**

    ``:29-66`` zeroes a 9x7 array, bails out with ``SetError(1, 0, False)`` when the static skillbar
    pointer is not resolved, reads the eight slot records, and stores each slot's adrenaline words, skill
    id, event and recharge state -- the last computed from the slot's timestamp and the client's timer.
    This layer keeps no such table: `UAI_GetDynamicSkillInfo` performs those same reads and that same
    arithmetic when a caller asks, so there is nothing a refresh could make fresher.

    **Its two failure paths are kept**, because they are the parts a caller branches on: a skillbar the
    client does not hold -- GwAu3's own unresolved-pointer case -- answers ``False``, as does a slot read
    that cannot be made. On success it answers ``True``, which is what the source answers.
    """

    skillbars = None
    try:
        from ..client import require_client

        world = require_client().read_world_context()
        skillbars = None if world is None else world.skillbars
    except Exception:
        return False

    return bool(skillbars)


def UAI_GetDynamicSkillStruct() -> Any:
    """**NOT APPLICABLE: the record it describes is a declared structure here.**

    ``:17-26`` builds a *runtime* memory-structure descriptor so that ``Memory_ReadArrayStruct`` can read
    a byte layout GwAu3 has no compiled type for. This project has the type: `SkillbarSkillStruct`
    (`py4gw/context/world_context.py:1059-1069`) declares ``adrenaline_a``, ``adrenaline_b``,
    ``recharge``, ``skill_id`` and ``event`` at exactly the offsets the descriptor names, and its size is
    asserted (``assert ctypes.sizeof(SkillbarSkillStruct) == 0x14``). A caller that wants the record here
    wants that structure -- or simply `UAI_GetDynamicSkillInfo`, which answers its fields.

    It answers ``None`` for the same reason the other two NOT APPLICABLE members answer theirs: there is
    no descriptor to hand back, and a stand-in would be a different object under the source's name.
    """

    return None
