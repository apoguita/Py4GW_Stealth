"""GwAu3's ``UAI_*`` effect and bond questions, over this project's own effect reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**The questions are portable and the timings are not, and the split is the whole module.** GwAu3's
``UtilityAI_EffectsCache`` fills a per-frame cache of every agent's effects and bonds
(``$g_amx3_EffectsCache``, with a row count in ``$g_ai_EffectsCount``) and answers two kinds of thing
from it:

* **presence** -- "does this agent have this skill active", "how many effects", "is this bond one I
  upkeep" -- which is a fact about the client *now*, and which this project reads directly
  (`py4gw.effect`, over ``PyEffects``' own bindings);
* **timing** -- ``TimeElapsed``, ``TimeRemaining``, ``Scale`` and ``BonusScale`` -- which are computed
  from ``$GC_UAI_EFFECT_Timestamp``, a field **GwAu3 writes when it fills the cache**, not a client
  field (``UtilityAI_EffectsCache.au3:345-350``). A time elapsed since *GwAu3's own snapshot* has no
  live equivalent: this project has no frame loop, so there is no fill moment to measure from, and
  answering from "now" would answer a different question.

So presence is routed and timing refuses, with the reason on each function rather than in a comment
somewhere. The distinction matters to a caller: a bot asking "is my enchantment still up" wants
presence and gets it; a bot asking "how long has it been up" wants GwAu3's cache and is told so.
"""

from __future__ import annotations

from typing import Any

from .. import effect as _effect
from ..player import Player
from . import constants as _constants

__all__ = [
    "UAI_AgentHasEffect",
    "UAI_AgentHasVisibleEffect",
    "UAI_AgentUpkeepsBond",
    "UAI_GetAgentBondInfo",
    "UAI_GetAgentEffectCount",
    "UAI_GetAgentEffectInfo",
    "UAI_GetAgentVisibleEffectCount",
    "UAI_GetAgentVisibleEffectInfo",
    "UAI_GetFeederEnchOnTop",
    "UAI_GetPlayerEffectCount",
    "UAI_GetPlayerEffectInfo",
    "UAI_GetPlayerVisibleEffectCount",
    "UAI_GetPlayerVisibleEffectInfo",
    "UAI_PlayerHasEffect",
    "UAI_PlayerHasEffectType",
    "UAI_PlayerHasVisibleEffect",
    "UAI_PlayerUpkeepsBond",
]

#: The four properties that are **computed** rather than read, and the two things each needs.
#:
#: **These used to refuse here, and the reason they no longer do is a correction this module owes the
#: record.** The refusal said the timing columns rest on a timestamp "GwAu3 writes when it fills its own
#: per-frame cache, not a client field". That is wrong: the cache is filled from a **client read** --
#: ``Memory_ReadArrayStruct($l_p_EffectArray, $l_i_EffectCount, UAI_GetEffectStruct())``
#: (``UtilityAI_EffectsCache.au3:181-183``) -- and `UAI_GetEffectStruct` is a structure whose
#: ``Timestamp`` is a dword at ``+0x14`` and ``Duration`` a float at ``+0x10`` (``:59-62``). GwAu3 copies
#: the client's own values; this project reads the same two fields from the same record through
#: `py4gw.effect.get_effects`, whose `EffectType` carries both. So the source's formulas are the port's
#: formulas, over the same quantity:
#:
#: ``TimeElapsed`` is ``BitAND(Skill_GetSkillTimer() - Timestamp, 0xFFFFFFFF)``; ``TimeRemaining`` is
#: ``Duration * 1000`` minus that; and ``Scale``/``BonusScale`` interpolate the skill's own
#: ``Scale0``/``Scale15`` (``BonusScale0``/``BonusScale15``) by the effect's ``AttributeLevel``, floored.
_TIMING_PROPERTIES: frozenset[str] = frozenset(
    {"TimeElapsed", "TimeRemaining", "Scale", "BonusScale"}
)


def UAI_AgentHasEffect(agent_id: Any, skill_id: Any) -> bool:
    """Whether an agent has an effect from a skill (``UtilityAI_EffectsCache.au3:312-322``).

    GwAu3 walks its cached rows for the agent and compares ``SkillID``; this asks the client's own
    effects directly. The question is the same one, and here it is answered from the client rather than
    from a copy of it -- which is the semantic difference the module header states.

    Two of GwAu3's shapes are kept: a skill that is not found answers ``False``, and an agent with no
    effects answers ``False`` rather than raising.
    """

    return bool(_effect.effect_exists(int(agent_id), int(skill_id)))


def UAI_PlayerHasEffect(skill_id: Any) -> bool:
    """Whether the controlled character has an effect from a skill (``:325-330``)."""

    return bool(_effect.effect_exists(int(Player.GetAgentID()), int(skill_id)))


def UAI_GetAgentEffectCount(agent_id: Any) -> int:
    """How many effects an agent has (``:405-410``).

    GwAu3's count is ``$g_ai_EffectsCount[$index]`` -- how many rows it filled for that agent; this is
    ``PyEffects.effect_count``, the client's own count for the same agent.
    """

    return int(_effect.effect_count(int(agent_id)))


def UAI_GetPlayerEffectCount() -> int:
    """How many effects the controlled character has (``:412-415``)."""

    return int(_effect.effect_count(int(Player.GetAgentID())))


def UAI_GetAgentEffectInfo(agent_id: Any, skill_id: Any, prop: Any) -> Any:
    """One property of an agent's effect (``UtilityAI_EffectsCache.au3:333-370``).

    **The four timing properties refuse** and the rest are a question this module does not answer from
    GwAu3's shape: GwAu3's ``Switch`` returns the cached **column value** for a recognised property and
    ``0`` for anything else, and the columns that are not timing (``SkillID``, ``AttributeLevel``,
    ``EffectID``, ``CasterID``, ``Duration``) are fields of the client's own effect record. This
    project reads those through `py4gw.effect.get_effects`, whose record type carries them -- and the
    exact field names are the port's, so the work is a property table over that record rather than a
    guess made here.

    The guard order is GwAu3's: a property outside the enum answers ``0`` before anything is read, and
    an effect that is not present answers ``0``.
    """

    count = getattr(_constants, "GC_UAI_EFFECT_COUNT")
    if int(prop) < 0 or int(prop) >= count:
        return 0

    name = _EFFECT_PROPERTIES.get(int(prop), "")
    if not name:
        return 0

    reader = _EFFECT_PROPERTY_READERS.get(name)
    if reader is None:
        # A property GwAu3 recognises and this layer has no reader for. Answering `0` would be a wrong
        # value of the right type -- GwAu3 answers the cached column -- so it refuses and names the work
        # rather than pretending the column is empty.
        raise NotImplementedError(
            f"`$GC_UAI_EFFECT_{name}` is a column GwAu3 recognises and this layer has no reader for. "
            "GwAu3 answers it from `$g_amx3_EffectsCache[row][col]` "
            "(`UtilityAI_EffectsCache.au3:361-370`); this project reads the client's own effect records "
            "(`py4gw.effect.get_effects`), whose field names are the port's, and the work is the "
            "column-to-field table between them. Answering `0` here would be a wrong value that looks "
            "like an empty column."
        )

    # Presence first, so an effect the agent does not have answers 0 -- GwAu3's own loop simply never
    # matches and its `Return 0` at the end does the same.
    if not _effect.effect_exists(int(agent_id), int(skill_id)):
        return 0
    return reader(_find_effect(agent_id, skill_id))


def UAI_GetPlayerEffectInfo(skill_id: Any, prop: Any) -> Any:
    """One property of the controlled character's effect (``:371-403``). As the agent form."""

    return UAI_GetAgentEffectInfo(int(Player.GetAgentID()), skill_id, prop)


def UAI_AgentUpkeepsBond(agent_id: Any, skill_id: Any) -> bool:
    """Whether a bond on an agent is one the character upkeeps (``:417-428``).

    GwAu3 walks its bond rows for the agent and compares ``SkillID``; this asks the client's own bond
    list. **``buff_exists`` is the ported member for it**: the client's buff list is the upkeep list --
    an upkeep is a maintained enchantment, and ``PyEffects.buff_exists`` is its own exact-skill-id
    match (``effects_bindings.cpp:69-77``).
    """

    return bool(_effect.buff_exists(int(agent_id), int(skill_id)))


def UAI_PlayerUpkeepsBond(skill_id: Any) -> bool:
    """Whether the character upkeeps a bond (``:430-436``)."""

    return bool(_effect.buff_exists(int(Player.GetAgentID()), int(skill_id)))


def UAI_GetAgentBondInfo(agent_id: Any, skill_id: Any, prop: Any) -> Any:
    """One property of a bond on an agent (``:438-...``).

    **REFUSED**, and for the same reason the effect properties are: GwAu3's bond rows carry
    ``$GC_UAI_BOND_Timestamp`` and its siblings, written when *it* filled the cache, and the row set is
    ``$g_amx3_BondsCache``. This project reads the client's own buff records (`py4gw.effect.get_buffs`),
    whose fields are the port's names -- so the work is a property table over that record, and
    ``UAI_AgentUpkeepsBond`` is the routed question in the meantime.
    """

    raise NotImplementedError(
        "UtilityAI_EffectsCache.au3:438-... reads GwAu3's own bond cache "
        "(`$g_amx3_BondsCache[row][$GC_UAI_BOND_*]`), whose columns include a `Timestamp` GwAu3 writes "
        "when it fills the cache rather than a client field. This project has no such cache "
        "(`py4gw/gwa3/uai_agent.py` records the same divergence for the agent cache) and no "
        "column-to-field table for the port's buff records yet: `py4gw.effect.get_buffs(agent_id)` "
        "answers them, and building that table is the work. **Presence is routed**: "
        "`UAI_AgentUpkeepsBond` answers whether a bond is one the character upkeeps."
    )


def UAI_PlayerHasEffectType(a_s_EffectType: Any = "") -> bool:
    """Whether the controlled character is under an effect of one of three types
    (``UtilityAI_EffectsCache.au3:587-610``).

    The source's steps, in its order: the player's effect-count guard (``:589``); the **string**
    argument mapped to a skill type by three ``Case``s -- ``"HasStance"``, ``"HasGlyph"``,
    ``"HasPreparation"`` -- with anything else answering ``False`` under ``SetError(1, 0, False)``
    (``:592-601``); then the effect list walked **backwards** (``:603``), each effect's skill id looked
    up in the skill table for its type, and the first match answering ``True`` with that skill id
    through ``@extended`` (``:606``). Nothing matched answers ``False``.

    **The two channels are split here, and the second is named.** ``@extended`` has no twin in Python,
    so the skill id the source hands back is `_player_effect_of_type`'s answer -- the same scan, the
    same backwards order, the same two facts -- and this member answers the boolean alone. That is the
    documented pattern this layer uses wherever AutoIt carries a second fact out of band
    (`UAI_PrioritySkills`'s used slot, `Party_GetAverageHealth`'s validity). ``@error`` has no twin
    either: the source sets ``1`` for an unrecognised name, and an unknown name answers ``False`` here
    with that fact carried in this docstring. **``UAI_IsCastSensible`` is the caller**
    (``Core/UtilityAI_CanCast.au3:390``, ``:394``, ``:398``), and it reads the skill id through the
    twin.

    **The count guard is the empty scan.** ``If $l_i_EffectCount = 0 Then Return False``
    short-circuits a list with nothing in it, which is what the twin's own loop answers anyway -- and
    the list is read once, by the twin, rather than twice.

    **The name comparison is AutoIt's ``Switch``, which is case-insensitive for strings** unless
    ``Opt("StringCaseSense", 1)`` is set, and GwAu3 never sets it -- so ``"hasstance"`` matches, as it
    does in the source.
    """

    if str(a_s_EffectType).lower() == "hasstance":
        effect_type = _constants.GC_I_SKILL_TYPE_STANCE
    elif str(a_s_EffectType).lower() == "hasglyph":
        effect_type = _constants.GC_I_SKILL_TYPE_GLYPH
    elif str(a_s_EffectType).lower() == "haspreparation":
        effect_type = _constants.GC_I_SKILL_TYPE_PREPARATION
    else:
        return False

    return _player_effect_of_type(effect_type) != 0


def _player_effect_of_type(skill_type: int) -> int:
    """The skill id of the player's effect whose skill is of a type, or ``0``.

    **This is GwAu3's ``@extended``, spelled out.** ``UAI_PlayerHasEffectType("HasStance")`` answers
    ``True`` and hands the matching effect's **skill id** back through AutoIt's out-of-band return,
    which is the value `UAI_IsCastSensible` compares with the slot's own skill
    (``Core/UtilityAI_CanCast.au3:391``, ``:395``, ``:399``). Python has no out-of-band return, so the
    same scan is made here: the player's own effect list (`py4gw.effect.get_effects`), each effect's
    skill id, and the skill table's own ``SkillType`` -- the two facts the source reads, from the two
    places it reads them.

    **The scan runs backwards, because the source's does**: ``For $i = ($l_i_EffectCount - 1) To 0 Step
    -1`` (``UtilityAI_EffectsCache.au3:603``), so with two stances up the *last* one in the effect array
    is the id the source hands back -- and that is the id `UAI_IsCastSensible` compares with the slot.
    A forward scan would answer the first one, which is a different skill for the same client state.
    """

    from .data_skill import Skill_GetSkillInfo

    for record in reversed(list(_effect.get_effects(int(Player.GetAgentID())))):
        skill_id = int(record.skill_id)
        if skill_id == 0:
            continue
        if int(Skill_GetSkillInfo(skill_id, "SkillType")) == skill_type:
            return skill_id
    return 0


#: ``UtilityAI_EffectsCache.au3:51`` -- the timestamp of the last feeder enchantment this helper
#: reported. **A global the source declares in *this* file**, not in ``UtilityAI_Const.au3``, so it
#: lives here with the member that reads and writes it -- the same rule that puts the plugin's other
#: mutable settings in the module named for the file that declares them.
#:
#: It is what makes `UAI_GetFeederEnchOnTop` answer ``True`` **once per new enchantment** rather than
#: once per call, and `UAI_ResetRuntime` returns it to this value (``UtilityAI_Cache.au3:72``).
g_i_LastFeederEnchTimestamp: int = 0

#: ``UtilityAI_EffectsCache.au3:556-565`` -- the eight Dervish enchantments the source's
#: ``$l_ai_FeederEnchantments`` array holds, in the source's own order.
#:
#: **The source tests membership with ``_ArrayBinarySearch(...) < 0``, which is only a membership test
#: on a sorted array -- and this list is sorted** (1493, 1495, 1496, 1497, 1498, 1499, 1524, 1763), so
#: the binary search and this set answer the same thing. The order is kept as a tuple as well, because
#: the sortedness is a fact about the source that a later reader should be able to see rather than take
#: on trust.
_FEEDER_ENCHANTMENTS: tuple[int, ...] = (
    _constants.GC_I_SKILL_ID_GRENTHS_FINGERS,
    _constants.GC_I_SKILL_ID_AURA_OF_THORNS,
    _constants.GC_I_SKILL_ID_BALTHAZARS_RAGE,
    _constants.GC_I_SKILL_ID_DUST_CLOAK,
    _constants.GC_I_SKILL_ID_STAGGERING_FORCE,
    _constants.GC_I_SKILL_ID_PIOUS_RENEWAL,
    _constants.GC_I_SKILL_ID_EREMITES_ZEAL,
    _constants.GC_I_SKILL_ID_ZEALOUS_RENEWAL,
)


def UAI_GetFeederEnchOnTop() -> bool:
    """Whether a **new** feeder enchantment is the newest Dervish enchantment on the player
    (``UtilityAI_EffectsCache.au3:549-585``).

    The source's steps, in its order: the player's effect-count guard (``:551``); a scan over the
    player's effects keeping the **newest** skill that is a Dervish (``$GC_I_PROFESSION_DERVISH``)
    enchantment (``:568-577``); ``False`` when nothing matched (``:579``); ``False`` unless that skill
    is one of the eight feeder enchantments (``:580``); and ``False`` again when its timestamp is the
    one already reported -- otherwise the timestamp is **remembered** and the answer is ``True``
    (``:581-584``).

    **The answer is therefore "once per new enchantment", not "is there one"**, and the memory that
    makes it so is `g_i_LastFeederEnchTimestamp`, declared in this module because the source declares
    it in this file.

    **The count guard is the empty list.** ``If $l_i_EffectCount = 0 Then Return False`` reads the
    count GwAu3 cached; this reads the client's own list **once** and the guard is whether it is empty,
    which is the same question asked of the same facts -- and it keeps the scan from reading the list a
    second time, which a live read (unlike a cached count) would have to.

    **The scan order does not matter here** and that is worth stating, because the neighbouring scan in
    `_player_effect_of_type` has the opposite property: this one keeps a *maximum* timestamp rather
    than the first or last match, so every order over the same list answers the same skill. The two
    facts per effect are the client's own record (`skill_id`, `timestamp`) and the skill table's
    ``Profession`` and ``SkillType`` -- the same four reads the source makes, from the same two places.
    """

    global g_i_LastFeederEnchTimestamp

    from .data_skill import Skill_GetSkillInfo

    records = list(_effect.get_effects(int(Player.GetAgentID())))
    if not records:
        return False

    timestamp = 0
    skill_id = 0

    for record in records:
        current_skill_id = int(record.skill_id)
        if (
            int(Skill_GetSkillInfo(current_skill_id, "Profession"))
            != _constants.GC_I_PROFESSION_DERVISH
        ):
            continue
        if (
            int(Skill_GetSkillInfo(current_skill_id, "SkillType"))
            != _constants.GC_I_SKILL_TYPE_ENCHANTMENT
        ):
            continue
        current_timestamp = int(record.timestamp)
        if current_timestamp > timestamp:
            timestamp = current_timestamp
            skill_id = current_skill_id

    if skill_id == 0:
        return False
    if skill_id not in _FEEDER_ENCHANTMENTS:
        return False
    if g_i_LastFeederEnchTimestamp == timestamp:
        return False

    g_i_LastFeederEnchTimestamp = timestamp
    return True


def _visible_effects(agent_id: Any) -> list[Any]:
    """The agent's own visible-effect list, walked from its record -- GwAu3's cache, read live.

    ``UAI_FillVisEffectRows`` (``UtilityAI_EffectsCache.au3:116-137``) walks the TList at
    **``$l_p_AgentPtr + 0x174``** with ``Utils_TList_CreateIterator`` and reads each node with
    ``UAI_GetVisibleEffectStruct`` -- ``dword EffectType[0x0]; dword EffectID[0x4]; dword
    HasEnded[0x8]`` (``:76-82``) -- stopping at 31 rows. This project has the same walk already, in
    the ported agent context: `AgentLivingStruct.visible_effects_list` sits at that same ``+0x174``
    (``py4gw/context/agent_array.py:885``, and `py4gw/gwa3/data_agent.py` reads its pointers by that
    offset), and `AgentLivingStruct.visible_effects` walks it into `VisibleEffectStruct` records whose
    fields land exactly where GwAu3's struct puts them -- the port calls the first one ``unk`` where the
    source calls it ``EffectType``, and that is the one field-name difference in the mapping.

    **Two bounds differ, and the difference is the cache.** GwAu3's fill stops at 31 rows because its
    row arrays are ``[32]`` wide; the port's walk is bounded by the port's own reader
    (``_MAX_VISIBLE_EFFECTS``, 128). So an agent carrying more than 31 visible effects is answered from
    all of them here and from the first 31 there. **The first check is GwAu3's own row lookup**: the
    source answers ``False`` when ``UAI_GetIndexByID`` finds no cache row, and here that is a record the
    client does not hold or one that is not a living agent -- the same two cases its fill skips
    (``:229`` passes over every non-living agent, so its row count for one is zero).

    **Measured live, read-only** (`tests/probe_gwa3_visible_effects_live.py`, pid 19696, 2026-10-10;
    ``tests/live_reports/gwa3_visible_effects.log``): of the client's 39 agents, twelve carried nodes and
    the walk answered for all of them -- most with one ``[2, 0, 0]`` row, one with two
    (``[2, 0, 0], [1, 42, 0]``), and one with ``[3, 5, 0]``. **That second agent is the measurement the
    mapping needed**: a node whose first dword is ``1`` (``$GC_I_EFFECT_TYPE_STATUS``) and whose second
    is ``42``, a status id outside the seven condition ids GwAu3 filters on (23..29) -- so the first
    dword is the effect *type* and the second the effect *id*, which is what GwAu3's own struct names
    and what this port reads through the fields the port calls ``unk`` and ``id``.
    """

    from .data_agent import Agent_GetAgentPtr

    record = Agent_GetAgentPtr(agent_id)
    if record is None or not record.is_living_type:
        return []
    return list(record.visible_effects)


def UAI_AgentHasVisibleEffect(a_i_AgentID: Any, a_i_EffectType: Any, a_i_EffectID: Any) -> bool:
    """Whether an agent carries a visible effect of a type and id (``:480-491``).

    The source's loop, kept: each row's ``EffectType`` compared first, then its ``EffectID``, and the
    first row that matches both answers ``True``. Rows are read from the agent's own record here rather
    than from the cache GwAu3 fills (see `_visible_effects`), which is the substitution this module's
    header describes for every effect question.

    **This is the member ten `UAI_Filter_*` predicates and one targeting query were waiting on**, and
    the answer is exact rather than inferred: GwAu3's own comment on those filters is that the agent
    record's *condition bit* is a different test, which is why they refused rather than approximate.
    """

    for record in _visible_effects(a_i_AgentID):
        if int(record.unk) != a_i_EffectType:
            continue
        if int(record.id) == a_i_EffectID:
            return True
    return False


def UAI_PlayerHasVisibleEffect(a_i_EffectType: Any, a_i_EffectID: Any) -> bool:
    """Whether the controlled character carries a visible effect of a type and id (``:494-500``).

    The same loop as the agent form, over the player's own record -- GwAu3 reads its mirrored player
    cache, which its fill copies out of the very rows the agent walk produced (``:235-243``).
    """

    return UAI_AgentHasVisibleEffect(
        int(Player.GetAgentID()), a_i_EffectType, a_i_EffectID
    )


def UAI_GetAgentVisibleEffectInfo(a_i_AgentID: Any) -> list[list[int]]:
    """An agent's visible-effect rows, row ``0`` carrying the count (``:503-519``).

    GwAu3 answers an AutoIt 2-D array ``[1 + count][3]`` whose ``[0][0]`` is the count and whose rows
    are ``(EffectType, EffectID, HasEnded)``; **the shape is kept**, as a list of rows, because that is
    the contract a migrating caller reads -- the same substitution `Party_GetMembersArray` makes for its
    one-dimensional twin. An agent with no rows answers ``[[0]]``, which is the source's own
    ``Local $l_ai2_VisEffects[1][1] = [[0]]`` returned unchanged when its row lookup fails (``:504-506``).
    """

    effects = _visible_effects(a_i_AgentID)
    if not effects:
        return [[0]]
    rows: list[list[int]] = [[len(effects), 0, 0]]
    for effect in effects:
        rows.append([int(effect.unk), int(effect.id), int(effect.has_ended)])
    return rows


def UAI_GetPlayerVisibleEffectInfo() -> list[list[int]]:
    """The controlled character's visible-effect rows, as the agent form (``:522-535``)."""

    return UAI_GetAgentVisibleEffectInfo(int(Player.GetAgentID()))


def UAI_GetAgentVisibleEffectCount(a_i_AgentID: Any) -> int:
    """How many visible-effect rows an agent has (``:538-542``). ``0`` for an agent with no row."""

    return len(_visible_effects(a_i_AgentID))


def UAI_GetPlayerVisibleEffectCount() -> int:
    """How many visible-effect rows the controlled character has (``:545-547``)."""

    return len(_visible_effects(int(Player.GetAgentID())))


def _find_effect(agent_id: Any, skill_id: Any) -> Any:
    """The client's own effect record for a skill, or ``None``."""

    for record in _effect.get_effects(int(agent_id)):
        if int(getattr(record, "skill_id", 0)) == int(skill_id):
            return record
    return None


#: ``{column value: column name}`` for the effect enum, read from the generated constants so the numbers
#: come from GwAu3's own ``Global Enum`` rather than from a transcription of it.
_EFFECT_PROPERTIES: dict[int, str] = {
    getattr(_constants, name): name[len("GC_UAI_EFFECT_") :]
    for name in _constants.__all__
    if name.startswith("GC_UAI_EFFECT_") and name != "GC_UAI_EFFECT_COUNT"
}

#: ``{property name: reader over the port's effect record}``. **Every field is named literally** -- this
#: layer never reaches a record's field through a dynamic name, and the record is the port's own
#: `EffectType` (`py4gw/effect.py:74-88`), which declares all of them.
_EFFECT_PROPERTY_READERS: dict[str, Any] = {
    "SkillID": lambda record: int(record.skill_id),
    "AttributeLevel": lambda record: int(record.attribute_level),
    "EffectID": lambda record: int(record.effect_id),
    "CasterID": lambda record: int(record.agent_id),
    "Duration": lambda record: float(record.duration),
    "Timestamp": lambda record: int(record.timestamp),
    # The four computed columns, each the source's own expression over the same client fields.
    "TimeElapsed": lambda record: _elapsed(record),
    "TimeRemaining": lambda record: float(record.duration) * 1000 - _elapsed(record),
    "Scale": lambda record: _scaled(record, "Scale0", "Scale15"),
    "BonusScale": lambda record: _scaled(record, "BonusScale0", "BonusScale15"),
}


def _elapsed(record: Any) -> int:
    """``BitAND(Skill_GetSkillTimer() - Timestamp, 0xFFFFFFFF)`` (``:380``, ``:384``).

    The client's own timer (routed: `py4gw/gwa3/data_skill.py`'s `Skill_GetSkillTimer` is the same
    ``GetTickCount() + client start`` GwAu3 computes) minus the effect's start timestamp, masked to
    32 bits exactly as the source masks it.
    """

    from .data_skill import Skill_GetSkillTimer

    return (int(Skill_GetSkillTimer()) - int(record.timestamp)) & 0xFFFFFFFF


def _scaled(record: Any, key0: str, key15: str) -> int:
    """``Floor(scale0 + ((scale15 - scale0) / 15) * AttributeLevel)`` (``:355``, ``:360``).

    The two ends come from the **skill table** (routed, `Skill_GetSkillInfo`) and the interpolation from
    the effect's own attribute level -- the source reads exactly these three numbers, and floors.
    """

    import math

    from .data_skill import Skill_GetSkillInfo

    scale0 = int(Skill_GetSkillInfo(int(record.skill_id), key0))
    scale15 = int(Skill_GetSkillInfo(int(record.skill_id), key15))
    return math.floor(scale0 + ((scale15 - scale0) / 15) * int(record.attribute_level))
