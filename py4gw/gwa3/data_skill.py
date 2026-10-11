"""GwAu3's `Skill_GetSkillInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's skill-table reader. The record is the client's own constant skill table, one 0xA4-byte entry per skill id, which this project reads as `SkillStruct`.

The file's **skillbar** reader is carried as a snippet (`tools/gwa3_snippets/data_skill_skillbar.py`): `Skill_GetSkillbarInfo` -- the stride walk UtilityAI's slot loop asks what is on a skillbar -- and `Skill_GetSkillTimer`, the clock a slot's recharge timestamp is measured against. Both are over the port's own structures, whose strides are GwAu3's: `SkillbarStruct` ``0xBC`` and `SkillbarSkillStruct` ``0x14``.

`Skill_GetSkillInfo` is one ``Switch`` over 63 keys in GwAu3
(``GwAu3_Data_Skill.au3``). 59 of the 63 field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct

from typing import Any

from ..client import require_client
from ..context import SkillStruct
from .data_agent import Agent_GetMyID
from .data_party import Party_GetMyPartyHeroInfo
_UNIMPLEMENTED: dict[str, str] = {}

_COMPUTED: frozenset[str] = frozenset([])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Activation": lambda record: record.activation,
        "Adrenaline": lambda record: record.adrenaline,
        "Aftercast": lambda record: record.aftercast,
        "AoeRange": lambda record: record.aoe_range,
        "Attribute": lambda record: record.attribute,
        "BonusScale0": lambda record: record.bonus_scale0,
        "BonusScale15": lambda record: record.bonus_scale15,
        "Campaign": lambda record: record.campaign,
        "CasterBodyAnimationID": lambda record: record.caster_body_animation_id,
        "CasterOverheadAnimationID": lambda record: record.caster_overhead_animation_id,
        "Combo": lambda record: record.combo,
        "ComboReq": lambda record: record.combo_req,
        "CompleteConcise": lambda record: record.concise,
        "CompleteDescription": lambda record: record.description,
        "Concise": lambda record: record.concise,
        "ConciseID": lambda record: record.concise,
        "Condition": lambda record: record.condition,
        "ConstEffect": lambda record: record.const_effect,
        "Description": lambda record: record.description,
        "DescriptionID": lambda record: record.description,
        "Duration0": lambda record: record.duration0,
        "Duration15": lambda record: record.duration15,
        "Effect1": lambda record: record.effect1,
        "Effect2": lambda record: record.effect2,
        "EffectConstant1": lambda record: record.aoe_range,
        "EffectConstant2": lambda record: record.const_effect,
        "EffectFlag": lambda record: record.effect2,
        "EnergyCost": lambda record: record.energy_cost,
        "GwVersion": lambda record: record.h0004,
        "HealthCost": lambda record: record.health_cost,
        "IconFileID": lambda record: record.icon_file_id,
        "IconFileID2": lambda record: record.icon_file_id_2,
        "IconFileIDHD": lambda record: record.icon_file_id_hi_res,
        "InflictsCondition": lambda record: record.effect1,
        "NameID": lambda record: record.name,
        "Overcast": lambda record: record.overcast,
        "Profession": lambda record: record.profession,
        "ProjectileAnimation1ID": lambda record: record.projectile_animation_1_id,
        "ProjectileAnimation2ID": lambda record: record.projectile_animation_2_id,
        "Recharge": lambda record: record.recharge,
        "RequireCondition": lambda record: record.condition,
        "Scale0": lambda record: record.scale0,
        "Scale15": lambda record: record.scale15,
        "SkillArguments": lambda record: record.skill_arguments,
        "SkillEquipType": lambda record: record.skill_equip_type,
        "SkillID": lambda record: record.skill_id,
        "SkillIDPvP": lambda record: record.skill_id_pvp,
        "SkillName": lambda record: record.name,
        "SkillNameID": lambda record: record.name,
        "SkillType": lambda record: record.type,
        "Special": lambda record: record.special,
        "Target": lambda record: record.target,
        "TargetBodyAnimationID": lambda record: record.target_body_animation_id,
        "TargetOverheadAnimationID": lambda record: record.target_overhead_animation_id,
        "Title": lambda record: record.title,
        "WeaponReq": lambda record: record.weapon_req,
        "h0004": lambda record: record.h0004,
        "h0032": lambda record: record.h0032,
        "h0037": lambda record: record.h0037,
        "h0050": lambda record: _read_raw(record, 0x0050, "<H"),
        "h0052": lambda record: _read_raw(record, 0x0052, "<H"),
        "h0054": lambda record: _read_raw(record, 0x0054, "<H"),
        "h0056": lambda record: _read_raw(record, 0x0056, "<H"),
    }
)


def Skill_GetSkillInfo(record_id: Any, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Skill.au3``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record(record_id)
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, record_id)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``client.read_skill(int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return client.read_skill(int(record_id))

"""``GwAu3_Data_Skill.au3``'s **skillbar** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_party`'s member
accessors and the item resolvers use: ``data_skill.py`` is rewritten whole on every run.

**What it is, and why the whole engine wanted it.** ``Skill_GetSkillbarInfo``
(``GwAu3_Data_Skill.au3:210-304``) is how every part of UtilityAI learns what is on a skillbar: the slot
loop in `UAI_UseSkills` asks it for a slot's ``SkillID``, `Skill_GetSlotByID` and `Skill_CheckSlotByID`
walk it, and the static skill cache is built from it. It is a stride walk over the **world's** skillbar
array -- ``0xBC`` bytes per skillbar, ``0x14`` per slot -- matching a skillbar's agent id against the
player's own or a hero's.

**The port's structures are the same two strides**, so the walk is this project's own read:
`SkillbarStruct` is ``0xBC`` and `SkillbarSkillStruct` is ``0x14``
(`py4gw/context/world_context.py:1059-1093`, with ``assert ctypes.sizeof(...)`` for both), reached
through `WorldContextStruct.skillbars`. Every offset GwAu3 reads has a name there: ``+0x0`` `agent_id`,
``+0xA4`` `disabled`, the casting word ``+0xB0`` is the cast array's ``m_size``, ``+0x8``/``+0xC``/
``+0x10``/``+0x14`` of a slot are its two adrenaline words, its recharge timestamp and its skill id.

**The recharge timer is routed too, and it is the same number.** GwAu3's `Skill_GetSkillTimer` is
``GetTickCount() + $g_i_GWExeStart`` masked to 32 bits (``:11-14``); this project's
``client.memory_manager.GetSkillTimer()`` is the same sum (``py4gw/memory/memory_manager.py``, the
client global the catalog names ``memory.skill_timer_ptr``), which is why the two recharge keys answer
rather than refuse. The subtraction wraps as ``uint32`` in both.
"""

def _signed(value: int) -> int:
    """``Utils_MakeInt32``: the same 32-bit word read as a signed integer (`:276-277`).

    The source converts *both* timestamps before it subtracts, because the client stores them unsigned
    and the wrap is what makes a recharge that has already elapsed come out negative rather than huge.
    """

    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


def Skill_GetSkillTimer() -> int:
    """The client's own skill timer (``GwAu3_Data_Skill.au3:11-14``).

    ``BitAND(GetTickCount() + $g_i_GWExeStart, 0xFFFFFFFF)`` -- the tick count offset by the client's
    start, which is the value a skillbar slot's recharge timestamp is measured against. This project
    reads the same sum through the connection (`client.memory_manager.GetSkillTimer`), so the two
    recharge keys below are the source's own arithmetic over the source's own clock.
    """

    return int(require_client().memory_manager.GetSkillTimer())


def _skillbar(world: Any, hero_number: Any) -> Any:
    """The skillbar GwAu3's stride walk finds, or ``None``.

    The match is on the record's first word -- the skillbar's **agent id** -- against the player's own
    id (``$a_i_HeroNumber = 0``) or the numbered hero's, exactly as ``:220-231`` does it. ``None`` is
    GwAu3's own no-match answer (``:231`` returns ``0``), and so is a zero id (``:226``).
    """

    skillbars = world.skillbars
    if skillbars is None:
        return None

    if hero_number != 0:
        wanted = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
    else:
        wanted = Agent_GetMyID()

    if wanted == 0:
        return None

    for skillbar in skillbars:
        if int(skillbar.agent_id) == int(wanted):
            return skillbar
    return None


def Skill_GetSkillbarInfo(skill_slot: Any = 1, info: str = "", hero_number: Any = 0) -> Any:
    """One field of one skillbar slot, on the player's bar or a hero's
    (``GwAu3_Data_Skill.au3:210-304``).

    GwAu3's guards, in its order: a bar array the client does not hold, a hero number outside it, a
    slot number outside ``1..8``, and an agent id of ``0`` all answer ``0`` (``:214-226``); a walk that
    matches nothing answers ``0`` (``:231``); and an unrecognised key answers ``0`` -- its ``Case Else``.

    **Two key names are GwAu3's and answer a word the port names differently**, and both are recorded
    rather than glossed: ``h00A8[2]`` and ``h00B4[2]`` are the *first* and *fourth* words of the
    cast-array header at ``+0xA8`` -- the port's `cast_array` ``m_buffer`` and ``m_param`` -- and
    ``Casting`` is the third word, ``m_size``: "is a skill in flight" is "the cast array is not empty".
    A caller that wants the queued skill itself wants `cast_array`'s elements, which this key does not
    answer.

    ``SlotBySkillID`` and ``HasSkillID`` are the source's own reversals: both take a **skill id in the
    slot parameter**. **And both are unreachable with a real skill id, because the guard above the
    ``Switch`` rejects anything outside ``1..8`` (``:217``) before the ``Case`` is reached** -- so with
    a skill id they answer ``0``, in GwAu3 exactly as here. The port keeps the guard and the order, so
    its answer is the source's; the workaround a caller wants is `UAI_GetSkillbarInfo`'s sibling in the
    plugin, which looks a slot up by walking the eight ids itself.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    size = int(world.party_skillbar_array.m_size)
    if hero_number < 0 or hero_number >= size:
        return 0
    if skill_slot < 1 or skill_slot > 8:
        return 0

    skillbar = _skillbar(world, hero_number)
    if skillbar is None:
        return 0

    if info == "AgentID":
        return int(skillbar.agent_id)
    if info == "Disabled":
        return int(skillbar.disabled)
    if info == "Casting":
        return int(skillbar.cast_array.m_size)
    if info == "h00A8[2]":
        return int(skillbar.cast_array.m_buffer)
    if info == "h00B4[2]":
        return int(skillbar.cast_array.m_param)
    if info == "Queued":
        return int(skillbar.h00B8)

    slot = skillbar.skills[int(skill_slot) - 1]

    # Each slot key names its field literally. A table keyed by the GwAu3 name would reach the field
    # dynamically, which this project's porting rules forbid -- and the four names are GwAu3's own key
    # strings beside the port's field names, which is the mapping a reader wants to see anyway.
    if info == "SkillID":
        return int(slot.skill_id)
    if info == "Adrenaline":
        return int(slot.adrenaline_a)
    if info == "AdrenalineB":
        return int(slot.adrenaline_b)
    if info == "Event":
        return int(slot.event)

    if info == "IsRecharged":
        timestamp = int(slot.recharge)
        if timestamp == 0:
            return True
        return (timestamp - Skill_GetSkillTimer()) == 0

    if info == "RechargeTime":
        # `Utils_MakeInt32` on both sides (`:276-279`): the timestamps are unsigned words in the client
        # and the subtraction is signed in the source, then clamped at zero. `_signed` is that
        # conversion -- the same one the source's helper makes -- so the comparison is the source's.
        timestamp = int(slot.recharge)
        if timestamp == 0:
            return 0

        remaining = _signed(timestamp) - _signed(Skill_GetSkillTimer())
        if remaining <= 0:
            return 0
        return remaining

    if info == "HasSkill":
        return int(slot.skill_id) != 0

    if info == "SlotBySkillID":
        for index in range(8):
            if int(skillbar.skills[index].skill_id) == int(skill_slot):
                return index + 1
        return 0

    if info == "HasSkillID":
        for index in range(8):
            if int(skillbar.skills[index].skill_id) == int(skill_slot):
                return True
        return False

    return 0

__all__ = ['Skill_GetSkillInfo', 'Skill_GetSkillTimer', 'Skill_GetSkillbarInfo']
