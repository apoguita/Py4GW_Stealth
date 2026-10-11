"""GwAu3's ``UtilityAI_GetAgent.au3``: the targeting and positioning queries.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the file does.** It answers three kinds of question about the agents around the player -- *which
one*, *where*, and *where should I stand* -- and it answers them by walking GwAu3's own per-frame agent
cache (``$g_amx2_AgentCache``, ``UtilityAI_AgentCache.au3``). Every function here is a loop over that
cache's rows, a set of comparisons, and an answer: an agent id, a coordinate triple, or a boolean. The
whole module is therefore ported as the *questions* it asks, over this project's live agent reads.

**The three translations this port makes, and they are the same three everywhere.**

* **A cache row is an agent id.** GwAu3 writes ``For $i = 1 To $g_i_AgentCacheCount`` and then
  ``UAI_GetAgentInfo($i, $GC_UAI_AGENT_ID)`` to get the row's agent. This port iterates the client's own
  agent array (`py4gw/agent_array.py`) and carries the id, so the row loop and the id loop are the same
  loop -- see `_cached_ids`. The row index itself is refused, by name, in
  `py4gw/gwa3/uai_agent.py`'s `UAI_GetIndexByID`.
* **``$GC_UAI_AGENT_Distance`` is computed, not read.** The cache fills that column at
  ``UtilityAI_AgentCache.au3:163-165,231`` as ``Sqrt((X - PlayerX)^2 + (Y - PlayerY)^2)`` -- the player,
  and no Z -- so `_cached_distance` performs the same arithmetic over the same two live reads. Asking
  this layer for the *column* refuses (`py4gw/gwa3/uai_agent.py`, *cache-only columns*), because a
  column is a copy and the arithmetic is not; six functions in this file need that value, and this is
  where it comes from.
* **The fight mode is read when it is used.** ``$g_i_FightMode`` is UtilityAI's mutable setting
  (`UtilityAI_Const.au3:20`, default ``1`` -- *Pressure*), and `py4gw/gwa3/uai_const.py` holds it. Every
  comparison against ``$g_i_FinisherMode``/``$g_i_PressureMode`` is made at call time, as the source
  makes it.

**Two members refuse, and both refuse for one missing member rather than for a missing rule.**
`UAI_GetBestTargetByConditionCount` counts seven status effects per agent with
``UAI_AgentHasVisibleEffect`` (``:645``), and `UAI_PlayerHasOtherMesmerHex` — which *is* ported, because
it only needs the player's effect list and the skill table — is the one that shows why: the condition
counter needs each *status* effect's skill id, not the effect count this layer already answers. The
member that would answer it is the next work item and is named where it is missing.

**The file's own quirks are kept rather than tidied**, and there are three worth naming because a
reader will meet them: `UAI_GetAgentLowest` computes the reference id and never consults it (``:177``);
`UAI_MoveTowardCorpse` returns ``True`` even when its bounded loop times out short of the corpse
(``:778``); and ``UAI_GetBestMartialEnemyPosition``'s closing comment names its sibling's function
(``:568``). They are the source's, and a port that fixed them would not be one.
"""

from __future__ import annotations

import time
from typing import Any

from .. import effect as _effect
from ..agent_array import AgentArray
from ..player import Player
from . import constants as _constants
from . import uai_const
from .cmd_map import Map_Move
from .data_agent import (
    _ApplyFilters,
    Agent_ConvertID,
    Agent_GetAgentInfo,
)
from .data_skill import Skill_GetSkillInfo
from .uai_agent import UAI_GetAgentCount, UAI_GetAgentInfo, UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import UAI_AgentHasVisibleEffect
from .uai_filter import (
    UAI_Filter_ExcludeMe,
    UAI_Filter_IsDeadEnemy,
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsLivingEnemy,
)
from .uai_utils import (
    UAI_GetBaseArmor,
    UAI_GetDamageMultiplier,
    UAI_GetElementalArmor,
    UAI_GetPhysicalArmor,
    UAI_IsCaster,
)

__all__ = [
    "UAI_ConvertAgentID",
    "UAI_CountAgents",
    "UAI_FindAgentByPlayerNumber",
    "UAI_GetAgentHighest",
    "UAI_GetAgentLowest",
    "UAI_GetBestAOETarget",
    "UAI_GetBestAOETargetByDamageType",
    "UAI_GetBestCorpseForAllySupport",
    "UAI_GetBestCorpseForEnemyPressure",
    "UAI_GetBestMartialEnemyPosition",
    "UAI_GetBestOffensiveWardPosition",
    "UAI_GetBestSingleTarget",
    "UAI_GetBestTargetByConditionCount",
    "UAI_GetBestTargetByDamageType",
    "UAI_GetBestWardPosition",
    "UAI_GetFarthestAgent",
    "UAI_GetNearestAgent",
    "UAI_IsAgentInRange",
    "UAI_IsCorpseNearest",
    "UAI_MoveToWardPosition",
    "UAI_MoveTowardCorpse",
    "UAI_PlayerHasOtherMesmerHex",
]

_GC_UAI_AGENT_ID = _constants.GC_UAI_AGENT_ID
_GC_UAI_AGENT_X = _constants.GC_UAI_AGENT_X
_GC_UAI_AGENT_Y = _constants.GC_UAI_AGENT_Y
_GC_UAI_AGENT_HP = _constants.GC_UAI_AGENT_HP
_GC_UAI_AGENT_PlayerNumber = _constants.GC_UAI_AGENT_PlayerNumber


def _cached_ids() -> list[int]:
    """The live twin of ``For $i = 1 To $g_i_AgentCacheCount``.

    GwAu3 walks its cache's rows and reads each row's ``$GC_UAI_AGENT_ID`` to learn which agent the row
    is about. This layer has no rows -- it reads the client's agent array at the point of use -- so the
    loop is over the ids themselves, and every place the source writes ``UAI_GetAgentInfo($i, $column)``
    this module writes ``UAI_GetAgentInfo($id, $column)``, which is the same call with the row already
    resolved (`py4gw/gwa3/uai_agent.py` states that equivalence on the member).
    """

    return list(AgentArray.GetAgentArray())


def _cached_distance(agent_id: Any) -> float:
    """``$GC_UAI_AGENT_Distance``, the way the cache fills it (``UtilityAI_AgentCache.au3:163-165,231``).

    ``Sqrt((X - PlayerX)^2 + (Y - PlayerY)^2)`` -- the distance to the **player**, with no Z, computed
    once per cache fill from that fill's own player position. Here the same sum is computed from the
    same two reads, which is the same number without the frame of staleness between them.
    """

    dx = UAI_GetAgentInfoByID(agent_id, _GC_UAI_AGENT_X) - UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
    dy = UAI_GetAgentInfoByID(agent_id, _GC_UAI_AGENT_Y) - UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)
    return (dx * dx + dy * dy) ** 0.5


def UAI_ConvertAgentID(agent_id: Any) -> int:
    """``Agent_ConvertID``, under the plugin's own name (``UtilityAI_GetAgent.au3:5-7``).

    ``-2`` is the player, ``-1`` the current target, anything else an agent id -- and every function in
    this file passes its own argument through it before comparing.
    """

    return Agent_ConvertID(agent_id)


def UAI_FindAgentByPlayerNumber(
    player_number: Any, agent_id: Any = -2, range: float = 5000, filter: str = ""
) -> int:
    """The first agent with a given player number inside a range (``UtilityAI_GetAgent.au3:11-43``).

    ``$a_v_PlayerNumber`` may be a single number or a list of them -- GwAu3 tests it with ``IsArray``
    and accepts either, so a Python list or tuple is the array case. The range test is on
    ``$GC_UAI_AGENT_Distance``, which is the distance to the **player** even when the reference agent is
    someone else (`_cached_distance`), and the reference agent itself is skipped. ``0`` when nothing
    matches.
    """

    ref_id = UAI_ConvertAgentID(agent_id)
    is_array = isinstance(player_number, (list, tuple))

    for this_id in _cached_ids():
        if this_id == ref_id:
            continue

        player_num = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_PlayerNumber)

        if is_array:
            match = False
            for wanted in player_number:
                if player_num == wanted:
                    match = True
                    break
            if not match:
                continue
        else:
            if player_num != player_number:
                continue

        if filter != "" and not _ApplyFilters(this_id, filter):
            continue

        if _cached_distance(this_id) <= range:
            return this_id

    return 0


def UAI_CountAgents(agent_id: Any = -2, range: float = 1320, filter: str = "") -> int:
    """How many agents matching a filter are within a range of a reference agent
    (``UtilityAI_GetAgent.au3:49-84``).

    **The distance here is not the cached column.** The source says so itself (``:47-48``): it takes the
    reference agent's own ``X``/``Y`` -- the player's when the reference *is* the player -- and compares
    squared distances to that point, because a caller measuring "within 1320 of the target" is not
    asking "within 1320 of me". The reference agent is excluded from the count, and the filter string is
    ``_ApplyFilters``'s (``py4gw/gwa3/data_agent.py``).
    """

    ref_id = UAI_ConvertAgentID(agent_id)

    if ref_id == UAI_GetPlayerInfo(_GC_UAI_AGENT_ID):
        ref_x = UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
        ref_y = UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)
    else:
        ref_x = UAI_GetAgentInfoByID(ref_id, _GC_UAI_AGENT_X)
        ref_y = UAI_GetAgentInfoByID(ref_id, _GC_UAI_AGENT_Y)

    range_squared = range * range
    count = 0

    for this_id in _cached_ids():
        if this_id == ref_id:
            continue

        dx = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X) - ref_x
        dy = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y) - ref_y
        if (dx * dx + dy * dy) > range_squared:
            continue

        if filter != "" and not _ApplyFilters(this_id, filter):
            continue

        count += 1

    return count


def UAI_IsAgentInRange(agent_id: Any = -2, range: float = 1320, filter: str = "") -> bool:
    """Whether *any* agent matching a filter is within a range of a reference agent
    (``UtilityAI_GetAgent.au3:88-121``).

    `UAI_CountAgents`' own loop stopped at the first match -- the same reference point, the same
    squared-distance test, the same exclusion of the reference agent.
    """

    ref_id = UAI_ConvertAgentID(agent_id)

    if ref_id == UAI_GetPlayerInfo(_GC_UAI_AGENT_ID):
        ref_x = UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
        ref_y = UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)
    else:
        ref_x = UAI_GetAgentInfoByID(ref_id, _GC_UAI_AGENT_X)
        ref_y = UAI_GetAgentInfoByID(ref_id, _GC_UAI_AGENT_Y)

    range_squared = range * range

    for this_id in _cached_ids():
        if this_id == ref_id:
            continue

        dx = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X) - ref_x
        dy = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y) - ref_y
        if (dx * dx + dy * dy) > range_squared:
            continue

        if filter != "" and not _ApplyFilters(this_id, filter):
            continue

        return True

    return False


def UAI_GetNearestAgent(agent_id: Any = -2, range: float = 1320, filter: str = "") -> int:
    """The nearest agent matching a filter within a range (``UtilityAI_GetAgent.au3:124-145``).

    Nearest **to the player**: the range test and the comparison both use ``$GC_UAI_AGENT_Distance``
    (``_cached_distance``), while the reference agent is used only to exclude itself from the answer --
    the source resolves the reference id at ``:127`` and consults it once, at ``:134``. ``0`` when
    nothing is in range.
    """

    nearest_id = 0
    nearest_dist = 0x7FFFFFFF
    ref_id = UAI_ConvertAgentID(agent_id)

    for this_id in _cached_ids():
        distance = _cached_distance(this_id)
        if distance > range:
            continue

        if this_id == ref_id:
            continue

        if filter != "" and not _ApplyFilters(this_id, filter):
            continue

        if distance < nearest_dist:
            nearest_dist = distance
            nearest_id = this_id

    return nearest_id


def UAI_GetFarthestAgent(agent_id: Any = -2, range: float = 1320, filter: str = "") -> int:
    """The farthest agent matching a filter within a range (``UtilityAI_GetAgent.au3:148-169``).

    `UAI_GetNearestAgent`'s mirror: the same player-relative distance, the same exclusion of the
    reference agent, and a comparison that starts from ``0`` rather than from a maximum.
    """

    farthest_id = 0
    farthest_dist = 0
    ref_id = UAI_ConvertAgentID(agent_id)

    for this_id in _cached_ids():
        distance = _cached_distance(this_id)
        if distance > range:
            continue

        if this_id == ref_id:
            continue

        if filter != "" and not _ApplyFilters(this_id, filter):
            continue

        if distance > farthest_dist:
            farthest_dist = distance
            farthest_id = this_id

    return farthest_id


def UAI_GetAgentLowest(
    agent_id: Any = -2,
    range: float = 1320,
    property: Any = _GC_UAI_AGENT_HP,
    custom_filter: str = "",
) -> int:
    """The agent with the lowest value of a column, within a range (``UtilityAI_GetAgent.au3:174-198``).

    ``$a_i_Property`` is any ``$GC_UAI_AGENT_*`` column, ``HP`` by default, and it is handed to
    ``UAI_GetAgentInfo`` as the source hands it -- so a column this layer refuses refuses here too,
    naming itself, rather than being answered from a lookalike.

    **The reference agent is computed and never used.** ``:177`` resolves ``$l_i_RefID`` and the loop
    never mentions it, so unlike its neighbours this function can return the reference agent itself.
    That is the source's behaviour and it is kept.
    """

    lowest_value = 0x7FFFFFFF
    lowest_agent = 0
    ref_id = UAI_ConvertAgentID(agent_id)  # computed at :177; the source never consults it

    if UAI_GetAgentCount() == 0:
        return 0

    for this_id in _cached_ids():
        distance = _cached_distance(this_id)
        if distance > range:
            continue

        if custom_filter != "" and not _ApplyFilters(this_id, custom_filter):
            continue

        value = UAI_GetAgentInfo(this_id, property)

        if value < lowest_value:
            lowest_value = value
            lowest_agent = this_id

    return lowest_agent


def UAI_GetAgentHighest(
    agent_id: Any = -2,
    range: float = 1320,
    property: Any = _GC_UAI_AGENT_HP,
    custom_filter: str = "",
) -> int:
    """The agent with the highest value of a column, within a range (``UtilityAI_GetAgent.au3:201-225``).

    `UAI_GetAgentLowest` from the other end, including the unused reference id (``:204``).
    """

    highest_value = -1
    highest_agent = 0
    ref_id = UAI_ConvertAgentID(agent_id)  # computed at :204; the source never consults it

    if UAI_GetAgentCount() == 0:
        return 0

    for this_id in _cached_ids():
        distance = _cached_distance(this_id)
        if distance > range:
            continue

        if custom_filter != "" and not _ApplyFilters(this_id, custom_filter):
            continue

        value = UAI_GetAgentInfo(this_id, property)

        if value > highest_value:
            highest_value = value
            highest_agent = this_id

    return highest_agent


def UAI_GetBestSingleTarget(
    agent_id: Any = -2,
    range: float = 1320,
    property: Any = _GC_UAI_AGENT_HP,
    custom_filter: str = "",
) -> int:
    """The mode's best single target: lowest HP in Finisher, highest in Pressure
    (``UtilityAI_GetAgent.au3:227-231``).

    The two modes are the whole function: ``$g_i_FightMode`` is read at call time out of
    `py4gw/gwa3/uai_const.py`, and a mode that is neither answers ``0`` -- the source's own fall-through
    (`:230`), which a caller reaches only by assigning a value the two constants do not name.
    """

    if uai_const.g_i_FightMode == _constants.g_i_FinisherMode:
        return UAI_GetAgentLowest(agent_id, range, property, custom_filter)
    if uai_const.g_i_FightMode == _constants.g_i_PressureMode:
        return UAI_GetAgentHighest(agent_id, range, property, custom_filter)
    return 0


def UAI_GetBestAOETarget(
    agent_id: Any = -2,
    range: float = 1320,
    ao_range: Any = _constants.GC_I_RANGE_ADJACENT,
    custom_filter: str = "",
) -> int:
    """The agent at the centre of the best group to hit with an area skill
    (``UtilityAI_GetAgent.au3:241-310``).

    GwAu3's strategy is two passes and both are kept: the filter runs **once per agent** into flat
    parallel arrays (``:253-265``), and then a symmetric pairwise pass over the filtered set counts, for
    every agent, how many others lie within ``$a_f_AOERange`` -- including itself, which is why each
    count starts at ``1`` (``:263``). Only agents within ``$a_f_Range`` of the player are *eligible* to
    win (``:258``), but an ineligible agent still contributes to its neighbours' counts, which is the
    source's arithmetic and not a slip.

    The winner is the largest group; ties go to the group with the lowest average HP in Finisher mode
    and the highest in Pressure (``:285-306``). ``0`` when the filter matched nothing.
    """

    if UAI_GetAgentCount() == 0:
        return 0

    coords_x: list[float] = []
    coords_y: list[float] = []
    agent_hp: list[float] = []
    agent_id_list: list[int] = []
    eligible: list[bool] = []
    count: list[int] = []
    sum_hp: list[float] = []

    for this_id in _cached_ids():
        if custom_filter != "" and not _ApplyFilters(this_id, custom_filter):
            continue

        coords_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
        coords_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))
        agent_hp.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_HP))
        agent_id_list.append(this_id)
        eligible.append(_cached_distance(this_id) <= range)
        count.append(1)  # counts itself
        sum_hp.append(agent_hp[-1])

    if not agent_id_list:
        return 0

    aoe_sq = ao_range * ao_range
    for a, (ax, ay, hp_a) in enumerate(zip(coords_x[:-1], coords_y[:-1], agent_hp[:-1])):
        for b, (bx, by, hp_b) in enumerate(
            zip(coords_x[a + 1 :], coords_y[a + 1 :], agent_hp[a + 1 :]), start=a + 1
        ):
            dx = bx - ax
            dy = by - ay
            if (dx * dx + dy * dy) > aoe_sq:
                continue

            count[a] += 1
            sum_hp[a] += hp_b
            count[b] += 1
            sum_hp[b] += hp_a

    is_finisher = uai_const.g_i_FightMode == _constants.g_i_FinisherMode
    best_agent = 0
    best_count = 0
    best_avg_hp = 0x7FFFFFFF if is_finisher else 0

    for m_index, this_id in enumerate(agent_id_list):
        if not eligible[m_index]:
            continue

        group_count = count[m_index]
        avg_hp = sum_hp[m_index] / group_count

        if group_count > best_count:
            best_count = group_count
            best_avg_hp = avg_hp
            best_agent = agent_id_list[m_index]
        elif group_count == best_count:
            better_hp = avg_hp < best_avg_hp if is_finisher else avg_hp > best_avg_hp
            if better_hp:
                best_avg_hp = avg_hp
                best_agent = agent_id_list[m_index]

    return best_agent


def UAI_GetBestTargetByDamageType(
    agent_id: Any = -2,
    range: float = 1320,
    damage_type: str = "Elemental",
    custom_filter: str = "",
) -> int:
    """The best single target once its armor against a damage type is priced in
    (``UtilityAI_GetAgent.au3:315-349``).

    The score is ``HP / DamageMultiplier(armor)`` -- the HP a hit of this type effectively has to chew
    through -- and Finisher mode takes the lowest score while Pressure takes the highest. The reference
    agent is excluded here (``:325``), unlike in `UAI_GetAgentLowest`.
    """

    best_agent = 0
    best_score = 0x7FFFFFFF if uai_const.g_i_FightMode == _constants.g_i_FinisherMode else 0
    ref_id = UAI_ConvertAgentID(agent_id)

    if UAI_GetAgentCount() == 0:
        return 0

    for this_id in _cached_ids():
        if this_id == ref_id:
            continue

        distance = _cached_distance(this_id)
        if distance > range:
            continue

        if custom_filter != "" and not _ApplyFilters(this_id, custom_filter):
            continue

        hp = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_HP)
        score = _GetArmorScore(this_id, hp, damage_type)

        if uai_const.g_i_FightMode == _constants.g_i_FinisherMode:
            if score < best_score:
                best_score = score
                best_agent = this_id
        else:  # Pressure mode
            if score > best_score:
                best_score = score
                best_agent = this_id

    return best_agent


def UAI_GetBestAOETargetByDamageType(
    agent_id: Any = -2,
    range: float = 1320,
    ao_range: Any = _constants.GC_I_RANGE_ADJACENT,
    damage_type: str = "Elemental",
    custom_filter: str = "",
) -> int:
    """`UAI_GetBestAOETarget` with armor-priced scores (``UtilityAI_GetAgent.au3:355-425``).

    The same two passes and the same tie-break, with each agent's `_GetArmorScore` computed once up
    front (``:376``) instead of an HP sum -- so the group's average is an average *score*, and the
    group is still chosen by size first.
    """

    if UAI_GetAgentCount() == 0:
        return 0

    coords_x: list[float] = []
    coords_y: list[float] = []
    score: list[float] = []
    agent_id_list: list[int] = []
    eligible: list[bool] = []
    count: list[int] = []
    sum_score: list[float] = []

    for this_id in _cached_ids():
        if custom_filter != "" and not _ApplyFilters(this_id, custom_filter):
            continue

        coords_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
        coords_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))
        hp = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_HP)
        score.append(_GetArmorScore(this_id, hp, damage_type))  # armor lookup ONCE per agent
        agent_id_list.append(this_id)
        eligible.append(_cached_distance(this_id) <= range)
        count.append(1)
        sum_score.append(score[-1])

    if not agent_id_list:
        return 0

    aoe_sq = ao_range * ao_range
    for a, (ax, ay, score_a) in enumerate(zip(coords_x[:-1], coords_y[:-1], score[:-1])):
        for b, (bx, by, score_b) in enumerate(
            zip(coords_x[a + 1 :], coords_y[a + 1 :], score[a + 1 :]), start=a + 1
        ):
            dx = bx - ax
            dy = by - ay
            if (dx * dx + dy * dy) > aoe_sq:
                continue

            count[a] += 1
            sum_score[a] += score_b
            count[b] += 1
            sum_score[b] += score_a

    is_finisher = uai_const.g_i_FightMode == _constants.g_i_FinisherMode
    best_agent = 0
    best_count = 0
    best_avg_score = 0x7FFFFFFF if is_finisher else 0

    for m_index, this_id in enumerate(agent_id_list):
        if not eligible[m_index]:
            continue

        group_count = count[m_index]
        avg_score = sum_score[m_index] / group_count

        if group_count > best_count:
            best_count = group_count
            best_avg_score = avg_score
            best_agent = agent_id_list[m_index]
        elif group_count == best_count:
            better = avg_score < best_avg_score if is_finisher else avg_score > best_avg_score
            if better:
                best_avg_score = avg_score
                best_agent = agent_id_list[m_index]

    return best_agent


def _GetArmorScore(agent_id: Any, hp: Any, damage_type: str) -> float:
    """``HP`` over the damage multiplier for the armor this damage type meets
    (``UtilityAI_GetAgent.au3:428-441``).

    The three cases are the source's own grouping -- the four elemental types and the three physical
    ones, everything else against base armor -- and the multiplier comes from
    `py4gw/gwa3/uai_utils.py`'s `UAI_GetDamageMultiplier`, the same member the plugin's own damage
    estimates use.

    **The comparison is case-insensitive, as AutoIt's ``=`` on strings is.** ``Switch``/``Case`` in
    AutoIt matches with ``=``, which ignores case, so ``"elemental"`` and ``"Elemental"`` take the same
    branch in GwAu3 -- and they do here.
    """

    damage = damage_type.lower()
    if damage in ("elemental", "fire", "cold", "lightning", "earth"):
        armor = UAI_GetElementalArmor(agent_id)
    elif damage in ("physical", "blunt", "piercing", "slashing"):
        armor = UAI_GetPhysicalArmor(agent_id)
    else:
        armor = UAI_GetBaseArmor(agent_id)

    damage_mult = UAI_GetDamageMultiplier(armor)
    return hp / damage_mult


def _UAI_CountAlliesInRange(
    coords_x: list[float],
    coords_y: list[float],
    count: int,
    center_x: float,
    center_y: float,
    range_sq: float,
) -> int:
    """How many of the first ``count`` points lie within a squared range of one point
    (``UtilityAI_GetAgent.au3:445-453``).

    The source's ``ByRef`` arrays are Python lists here, and ``$a_i_Count`` stays an explicit argument
    for the same reason it is one there: the same array is reused with a smaller live count.
    """

    in_range = 0
    for i in range(count):
        dx = coords_x[i] - center_x
        dy = coords_y[i] - center_y
        if (dx * dx + dy * dy) <= range_sq:
            in_range += 1
    return in_range


def _UAI_BestCoveragePosition(
    coords_x: list[float],
    coords_y: list[float],
    count: int,
    range: float,
    from_x: float,
    from_y: float,
) -> list[float]:
    """The position whose range-disk covers the most points (``UtilityAI_GetAgent.au3:458-503``).

    The candidate set is the source's: **every point, then every pairwise midpoint** (``:467-478``) --
    which is what makes the answer good enough for a ward without a search. Coverage ties resolve toward
    ``from_x``/``from_y``, so among equally good spots the nearest one wins (``:490``), and the result is
    ``[X, Y, Count]`` with ``[0, 0, 0]`` when nothing covers anything (``:460``, ``:498``).
    """

    result: list[float] = [0, 0, 0]
    if count == 0:
        return result

    range_sq = range * range

    cand_x: list[float] = []
    cand_y: list[float] = []
    for point_x, point_y in zip(coords_x[:count], coords_y[:count]):
        cand_x.append(point_x)
        cand_y.append(point_y)
    for a, (point_x, point_y) in enumerate(zip(coords_x[:count], coords_y[:count])):
        for other_x, other_y in zip(coords_x[a + 1 : count], coords_y[a + 1 : count]):
            cand_x.append((point_x + other_x) * 0.5)
            cand_y.append((point_y + other_y) * 0.5)

    best_x = 0.0
    best_y = 0.0
    best_cover = 0
    best_dist_sq = 0.0

    for cx, cy in zip(cand_x, cand_y):
        cover = _UAI_CountAlliesInRange(coords_x, coords_y, count, cx, cy, range_sq)
        if cover < 1:
            continue

        ddx = cx - from_x
        ddy = cy - from_y
        dist_sq = ddx * ddx + ddy * ddy

        if cover > best_cover or (cover == best_cover and dist_sq < best_dist_sq):
            best_cover = cover
            best_dist_sq = dist_sq
            best_x = cx
            best_y = cy

    if best_cover < 1:
        return result
    result[0] = best_x
    result[1] = best_y
    result[2] = best_cover
    return result


def UAI_GetBestWardPosition(ward_range: Any = _constants.GC_I_RANGE_AREA) -> list[float]:
    """Where to stand for a ward that should cover the party (``UtilityAI_GetAgent.au3:507-525``).

    Living allies other than the player -- ``UAI_Filter_IsLivingAlly`` **and** ``UAI_Filter_ExcludeMe``,
    the source's own pair at ``:514-515`` -- are the points to cover, and the anchor the tie-break leans
    to is the player's own position. ``[X, Y, Count]``; ``Count`` is ``0`` when no ally was found,
    which is how the source's callers tell "no answer" from "stand here".
    """

    coords_x: list[float] = []
    coords_y: list[float] = []

    for this_id in _cached_ids():
        if not UAI_Filter_IsLivingAlly(this_id):
            continue
        if not UAI_Filter_ExcludeMe(this_id):
            continue
        coords_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
        coords_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))

    me_x = UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
    me_y = UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)

    return _UAI_BestCoveragePosition(coords_x, coords_y, len(coords_x), ward_range, me_x, me_y)


def UAI_GetBestOffensiveWardPosition(ward_range: Any = _constants.GC_I_RANGE_AREA) -> list[float]:
    """Where to stand for a ward that should cover the enemy group (``UtilityAI_GetAgent.au3:529-546``).

    `UAI_GetBestWardPosition` over ``UAI_Filter_IsLivingEnemy`` instead of allies, with no exclusion of
    the player -- the player is not an enemy, so the source needs none.
    """

    coords_x: list[float] = []
    coords_y: list[float] = []

    for this_id in _cached_ids():
        if not UAI_Filter_IsLivingEnemy(this_id):
            continue
        coords_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
        coords_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))

    me_x = UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
    me_y = UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)

    return _UAI_BestCoveragePosition(coords_x, coords_y, len(coords_x), ward_range, me_x, me_y)


def UAI_GetBestMartialEnemyPosition(ward_range: Any = _constants.GC_I_RANGE_AREA) -> list[float]:
    """Where to stand for a ward that should cover the enemy *front line*
    (``UtilityAI_GetAgent.au3:550-568``).

    Living enemies that are not casters (`UAI_IsCaster`, ``py4gw/gwa3/uai_utils.py``) -- the martial
    ones, which is what a ward against melee wants under it. The source's trailing comment names
    `UAI_GetBestOffensiveWardPosition` instead of this function (``:568``); it is a copy-paste in the
    comment and the code above it is this function's own.
    """

    coords_x: list[float] = []
    coords_y: list[float] = []

    for this_id in _cached_ids():
        if not UAI_Filter_IsLivingEnemy(this_id):
            continue
        if UAI_IsCaster(this_id):
            continue
        coords_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
        coords_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))

    me_x = UAI_GetPlayerInfo(_GC_UAI_AGENT_X)
    me_y = UAI_GetPlayerInfo(_GC_UAI_AGENT_Y)

    return _UAI_BestCoveragePosition(coords_x, coords_y, len(coords_x), ward_range, me_x, me_y)


def UAI_MoveToWardPosition(
    ward_range: Any = _constants.GC_I_RANGE_AREA,
    ward_type: Any = _constants.GC_I_UAI_WARDTYPE_DEFENSIVE,
) -> bool:
    """Move to the best ward position and report whether it is in reach to cast
    (``UtilityAI_GetAgent.au3:572-597``).

    The move is issued **once** and the loop only watches for arrival (``:588-594``): a ``Map_Move`` per
    iteration would restart the path. Arrival is within 25 units, bounded at five seconds, and a ward
    type that is neither of the two constants finds no position and answers ``False`` (``:573-579``).

    ``Map_Move`` is called with the source's own ``0`` for its randomisation argument, which is what
    keeps the destination exact.
    """

    best_pos: list[float] = [0, 0, 0]
    if ward_type == _constants.GC_I_UAI_WARDTYPE_DEFENSIVE:
        best_pos = UAI_GetBestWardPosition(ward_range)
    elif ward_type == _constants.GC_I_UAI_WARDTYPE_OFFENSIVE:
        best_pos = UAI_GetBestOffensiveWardPosition(ward_range)
    if best_pos[2] == 0:
        return False

    target_x = best_pos[0]
    target_y = best_pos[1]

    arrival_dist_sq = 25 * 25
    max_timeout_ms = 5000
    start = time.monotonic()

    Map_Move(target_x, target_y, 0)  # issue once; loop only watches for arrival
    while True:
        time.sleep(32 / 1000.0)
        dx = target_x - Agent_GetAgentInfo(-2, "X")
        dy = target_y - Agent_GetAgentInfo(-2, "Y")
        if (dx * dx + dy * dy) < arrival_dist_sq:
            return True
        if (time.monotonic() - start) * 1000.0 >= max_timeout_ms:
            break

    return False


def UAI_PlayerHasOtherMesmerHex(exclude_skill_id: Any) -> bool:
    """Whether the controlled character carries a Mesmer hex other than one skill
    (``UtilityAI_GetAgent.au3:602-617``).

    A build that applies a hex wants to know whether one is already up before spending another; the
    question is per *effect*, and it needs the skill table twice -- ``Profession`` then ``SkillType``
    (``:610-612``), the second read only inside the first's match, in the source's order.

    **The source's first line is a cache-row guard and has no twin here.** ``If $g_i_PlayerCacheIndex <
    1 Then Return False`` (``:603``) asks whether the player has a row in GwAu3's own effects cache; a
    row index is bookkeeping this layer refuses by name (`py4gw/gwa3/uai_agent.py`'s
    `UAI_GetPlayerIndex`), and the live twin of the guard is the answer it protects: with no effects
    there is nothing to walk and the answer is ``False`` either way.
    """

    for effect in _effect.get_effects(int(Player.GetAgentID())):
        skill_id = effect.skill_id
        if skill_id == exclude_skill_id:
            continue

        if Skill_GetSkillInfo(skill_id, "Profession") == _constants.GC_I_PROFESSION_MESMER:
            skill_type = Skill_GetSkillInfo(skill_id, "SkillType")
            if skill_type == _constants.GC_I_SKILL_TYPE_HEX:
                return True

    return False


def UAI_GetBestTargetByConditionCount(
    agent_id: Any = -2, range: float = 1320, custom_filter: str = ""
) -> int:
    """The conditioned agent worth attacking most, scored by how many conditions it carries
    (``:619-672``).

    The source's own walk and its own score, both kept:

    * every cached agent, skipped when it is further than ``$a_f_Range``, when it is **not**
      ``IsConditioned``, and when a custom filter rejects it (``:634-639``);
    * then the seven status effects it asks about by name -- bleeding, blinded, burning, diseased,
      poisoned, dazed and weakness (``:623-627``, where the source notes weakness shares its value with
      cracked armor) -- counted one `UAI_AgentHasVisibleEffect` call at a time (``:643-646``), and an
      agent with **none** of them is skipped as well (``:648``);
    * and the score: in **Finisher** mode ``HP / count`` preferring the lowest, in **Pressure** mode
      ``HP * count`` preferring the highest (``:652-668``), with the initial best score being the
      source's own ``0x7FFFFFFF`` in one mode and ``0`` in the other (``:621``).

    ``$g_i_FightMode`` is read at call time from `py4gw/gwa3/uai_const.py`, as every other reader of it
    does, and ``$a_i_AgentID`` is the source's own unused parameter -- kept so that a migrating call
    keeps its shape.

    **The walk is over the live agents, not over cache rows.** The source's ``For $i = 1 To
    $g_i_AgentCacheCount`` walks its own cache by **row index** and asks
    ``UAI_GetAgentInfo($i, ...)``; this file's convention for that loop is the live id list
    (`_cached_ids`), and the row index itself is refused by name (`py4gw/gwa3/uai_agent.py`).

    **This was the last targeting query that refused**, and it refused for exactly the reason its
    docstring gave: the per-effect read it needs (`UAI_AgentHasVisibleEffect`) did not exist. It does
    now (``py4gw/gwa3/uai_effects.py``), so the count is the source's count rather than a substitute
    number derived from the condition bits.
    """

    best_agent = 0
    best_score = (
        0x7FFFFFFF
        if uai_const.g_i_FightMode == _constants.g_i_FinisherMode
        else 0
    )

    conditions = (
        _constants.GC_I_EFFECT_ID_BLEEDING,
        _constants.GC_I_EFFECT_ID_BLINDED,
        _constants.GC_I_EFFECT_ID_BURNING,
        _constants.GC_I_EFFECT_ID_DISEASED,
        _constants.GC_I_EFFECT_ID_POISONED,
        _constants.GC_I_EFFECT_ID_DAZED,
        _constants.GC_I_EFFECT_ID_WEAKNESS,
    )

    for current_id in _cached_ids():
        distance = _cached_distance(current_id)
        if distance > range:
            continue

        if not UAI_GetAgentInfo(current_id, _constants.GC_UAI_AGENT_IsConditioned):
            continue

        if custom_filter != "" and not _ApplyFilters(current_id, custom_filter):
            continue

        hp = UAI_GetAgentInfo(current_id, _constants.GC_UAI_AGENT_HP)

        count = 0
        for condition in conditions:
            if UAI_AgentHasVisibleEffect(
                current_id, _constants.GC_I_EFFECT_TYPE_STATUS, condition
            ):
                count += 1

        if count == 0:
            continue

        if uai_const.g_i_FightMode == _constants.g_i_FinisherMode:
            score = hp / count
            if score < best_score:
                best_score = score
                best_agent = current_id
        else:
            score = hp * count
            if score > best_score:
                best_score = score
                best_agent = current_id

    return best_agent


def _UAI_GetBestCorpse(range: float, member_filter: str) -> int:
    """The corpse whose neighbourhood holds the most members, and getting there
    (``UtilityAI_GetAgent.au3:681-741``).

    Both lists are built in **one** cache pass (``:693-713``) -- dead enemies within ``$a_f_Range`` as
    candidates, everything matching ``$a_s_MemberFilter`` as the people to count -- and then each corpse
    is scored by how many members sit inside ``$GC_I_RANGE_AREA`` of it (``:717-734``). The source is
    explicit that the pass was rewritten to avoid re-filtering per corpse (``:678-680``), so the flat
    lists are the design and not an optimization of this port's.

    The answer is the **player's own id** when the best corpse is already the nearest one, or once
    `UAI_MoveTowardCorpse` has closed the distance -- otherwise ``0``, which is how the callers tell
    "not positioned yet" from "cast now". ``0`` as well when there is no corpse or no member near any of
    them (``:715``, ``:736``).
    """

    corpse_x: list[float] = []
    corpse_y: list[float] = []
    corpse_id: list[int] = []
    nearest_corpse = 0
    nearest_dist = 0x7FFFFFFF

    member_x: list[float] = []
    member_y: list[float] = []

    for this_id in _cached_ids():
        if UAI_Filter_IsDeadEnemy(this_id):
            distance = _cached_distance(this_id)
            if distance <= range:
                corpse_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
                corpse_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))
                corpse_id.append(this_id)
                if distance < nearest_dist:
                    nearest_dist = distance
                    nearest_corpse = this_id
        elif _ApplyFilters(this_id, member_filter):
            member_x.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X))
            member_y.append(UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y))

    if len(corpse_id) == 0:
        return 0

    area_sq = _constants.GC_I_RANGE_AREA * _constants.GC_I_RANGE_AREA
    best_corpse = 0
    best_count = 0

    for c, (this_corpse, cx, cy) in enumerate(zip(corpse_id, corpse_x, corpse_y)):
        count = 0
        for mx, my in zip(member_x, member_y):
            dx = mx - cx
            dy = my - cy
            if (dx * dx + dy * dy) <= area_sq:
                count += 1
        if count > best_count:
            best_count = count
            best_corpse = this_corpse

    if best_count == 0:
        return 0

    if best_corpse == nearest_corpse:
        return UAI_GetPlayerInfo(_GC_UAI_AGENT_ID)
    if UAI_MoveTowardCorpse(best_corpse):
        return UAI_GetPlayerInfo(_GC_UAI_AGENT_ID)
    return 0


def UAI_GetBestCorpseForAllySupport(range: Any) -> int:
    """The corpse to raise an ally-support well on: the one with the most living allies near it
    (``UtilityAI_GetAgent.au3:744-746``)."""

    return _UAI_GetBestCorpse(range, "UAI_Filter_IsLivingAlly")


def UAI_GetBestCorpseForEnemyPressure(range: Any) -> int:
    """The corpse to raise an enemy-pressure well on: the one with the most living enemies near it
    (``UtilityAI_GetAgent.au3:749-751``)."""

    return _UAI_GetBestCorpse(range, "UAI_Filter_IsLivingEnemy")


def UAI_MoveTowardCorpse(corpse_id: Any) -> bool:
    """Walk toward a corpse until it is the nearest one, so the well lands there
    (``UtilityAI_GetAgent.au3:754-779``).

    ``Map_Move`` is re-issued every iteration here -- unlike `UAI_MoveToWardPosition`, which issues once
    -- because the destination is fixed but the *question* is not: each pass re-asks `UAI_IsCorpseNearest`
    and stops the moment that corpse is the closest, at which point the well would raise there.

    **The ``Return True`` at the end is the source's, and it is reached on a timeout too** (``:778``): a
    call that ran the full five seconds without the corpse becoming nearest still answers ``True``. It is
    kept as written rather than corrected; the loop's exit condition mentions the arrival distance, which
    is a distance to a *coordinate*, while the success test inside the loop is about *ranking*.
    """

    target_x = UAI_GetAgentInfoByID(corpse_id, _GC_UAI_AGENT_X)
    target_y = UAI_GetAgentInfoByID(corpse_id, _GC_UAI_AGENT_Y)

    timeout = 0
    arrival_dist = 80
    max_timeout = 5000

    while True:
        Map_Move(target_x, target_y, 0)
        time.sleep(32 / 1000.0)
        timeout += 32

        cur_x = Agent_GetAgentInfo(-2, "X")
        cur_y = Agent_GetAgentInfo(-2, "Y")

        diff_x = target_x - cur_x
        diff_y = target_y - cur_y
        dist_to_target = (diff_x * diff_x + diff_y * diff_y) ** 0.5

        if UAI_IsCorpseNearest(corpse_id, cur_x, cur_y):
            return True

        if dist_to_target < arrival_dist or timeout >= max_timeout:
            break

    return True


def UAI_IsCorpseNearest(corpse_id: Any, x: Any, y: Any) -> bool:
    """Whether one corpse is the nearest corpse from a position (``UtilityAI_GetAgent.au3:782-803``).

    Squared distances throughout, and the comparison is **strict** (``:799``): another corpse at exactly
    the same distance does not displace the target, which is what stops
    `UAI_MoveTowardCorpse` from oscillating between two equidistant corpses.
    """

    target_x = UAI_GetAgentInfoByID(corpse_id, _GC_UAI_AGENT_X)
    target_y = UAI_GetAgentInfoByID(corpse_id, _GC_UAI_AGENT_Y)
    tdx = target_x - x
    tdy = target_y - y
    target_dist_sq = tdx * tdx + tdy * tdy

    for this_id in _cached_ids():
        if not UAI_Filter_IsDeadEnemy(this_id):
            continue
        if this_id == corpse_id:
            continue

        odx = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_X) - x
        ody = UAI_GetAgentInfo(this_id, _GC_UAI_AGENT_Y) - y

        if (odx * odx + ody * ody) < target_dist_sq:
            return False

    return True
