"""GwAu3's ``UAI_*`` estimation helpers, over this project's own agent reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**The UtilityAI plugin is where GwAu3 keeps its combat AI, and this module is its arithmetic layer.**
``UtilityAI_Utils.au3`` is the part of it that touches the client only through agent reads and then
does sums -- armor ratings, hit-point estimates, damage multipliers -- so every formula here is
transcribed from the source with its constants intact. Nothing calls a member this project does not
have, and nothing forges a packet.

**The constants are GwAu3's own and they are not decoration.** ``20`` armour for a Warrior *or a
Paragon*, ``10`` for a Ranger, an Assassin *or a Dervish*; ``level Ãƒâ€” 20 + 80`` hit points with the hard
mode bonus of ``20`` per level above twenty; ``2 ^ ((60 - armour) / 40)`` for the damage curve. A
migration that changed any of them would change what a bot decides to attack, and none of them is
derivable from the others.

**One mechanism difference, recorded rather than hidden.** `UAI_GetAgentProfession` has two arms in
GwAu3: a player, hero or henchman answers the agent record's own ``Primary`` field, and **everything
else** is looked up in the world's NPC array at ``index Ãƒâ€” 0x30 + 0x14``. This project reads the
profession through `Agent.GetProfessions`, the ported member for the same field on the same agent --
including for a mob, where GwAu3 reaches the NPC record instead. Both answer the agent's primary
profession and both read it from the client; which one is right for an edge-case mob is what a live
comparison would settle, and the layer says so rather than pretending the two walks are the same.
"""

from __future__ import annotations

from typing import Any

from ..agent import Agent
from ..party import Party
from . import constants as _constants
from .data_agent import Agent_GetAgentInfo, Agent_GetMyID
from .data_party import (
    Party_GetHeroFlagInfo,
    Party_GetMyPartyHenchmanInfo,
    Party_GetMyPartyHeroInfo,
    Party_GetMyPartyInfo,
    Party_GetMyPartyPlayerMemberInfo,
)
from .data_skill import Skill_GetSkillbarInfo, Skill_GetSkillInfo
from .uai_agent import UAI_GetAgentInfo, UAI_GetAgentInfoByID, UAI_GetPlayerInfo

# **`uai_get_agent` and `uai_filter` are imported inside the party functions, not here.** The filter
# module reads this one for the profession predicates (`uai_filter` -> `uai_utils`), and the targeting
# module reads the filter (`uai_get_agent` -> `uai_filter`), so a module-level import in either
# direction is a cycle -- the same reason `py4gw/gwa3/uai_agent.py` resolves `AgentArray` inside its own
# function. Each of the three party queries imports exactly what it calls.

#: The columns the party functions measure with, named once.
_GC_UAI_AGENT_ID = _constants.GC_UAI_AGENT_ID
_GC_UAI_AGENT_X = _constants.GC_UAI_AGENT_X
_GC_UAI_AGENT_Y = _constants.GC_UAI_AGENT_Y
_GC_UAI_AGENT_HP = _constants.GC_UAI_AGENT_HP

__all__ = [
    "Party_GetAvailableRezz",
    "Party_GetAverageHealth",
    "Party_GetHeroAgentID",
    "Party_GetHeroCount",
    "Party_GetHeroID",
    "Party_GetMembersArray",
    "Party_GetSize",
    "Party_IsWiped",
    "Skill_CheckSlotByID",
    "Skill_GetSlotByID",
    "UAI_CountEnemyInPartyAggroRange",
    "UAI_EstimateDamage",
    "UAI_GetAgentProfession",
    "UAI_GetArmorBonus",
    "UAI_GetBaseArmor",
    "UAI_GetDamageMultiplier",
    "UAI_GetEffectiveArmor",
    "UAI_GetElementalArmor",
    "UAI_GetEstimatedCurrentHP",
    "UAI_GetEstimatedMaxHP",
    "UAI_GetNearestEnemyInPartyRange",
    "UAI_GetPartyCalledTarget",
    "UAI_GetPhysicalArmor",
    "UAI_IsCaster",
    "UAI_IsEnemyInPartyAggroRange",
    "UAI_IsMelee",
    "UAI_IsRanged",
]

#: GwAu3's profession constants, by the numbers its own comments name
#: (``UtilityAI_Utils.au3:317-322``): Warrior ``1``, Ranger ``2``, Monk ``3``, Necromancer ``4``,
#: Mesmer ``5``, Elementalist ``6``, Assassin ``7``, Ritualist ``8``, Paragon ``9``, Dervish ``10``.
_WARRIOR = 1
_RANGER = 2
_MONK = 3
_NECROMANCER = 4
_MESMER = 5
_ELEMENTALIST = 6
_ASSASSIN = 7
_RITUALIST = 8
_PARAGON = 9
_DERVISH = 10

#: The three armour bonuses, as GwAu3's own comment states them: "Warrior/Paragon: +20,
#: Ranger/Assassin/Dervish: +10, Others: +0" (``UtilityAI_Utils.au3:314``).
_ARMOR_BONUS_HEAVY = 20
_ARMOR_BONUS_MEDIUM = 10

#: GwAu3's hit-point formula (``:327-329``): "Normal Mode: Level Ãƒâ€” 20 + 80; Hard Mode: Level Ãƒâ€” 20 + 80
#: + (Level - 20) Ãƒâ€” 20 if Level > 20".
_HP_PER_LEVEL = 20
_HP_BASE = 80
_HARD_MODE_LEVEL = 20

#: GwAu3's own fallback for an agent whose level reads zero (``:332``, ``:356``).
_DEFAULT_LEVEL = 20

#: The reference armour for the damage curve (``:389-390``): "60 AL = 1.0x damage".
_DAMAGE_REFERENCE_ARMOR = 60
_DAMAGE_CURVE_DIVISOR = 40

#: The physical bonus a Warrior gets and the elemental bonus a Ranger gets (``:361``, ``:375``).
_WARRIOR_PHYSICAL_BONUS = 20
_RANGER_ELEMENTAL_BONUS = 30


def _D(msg: Any) -> None:
    """GwAu3's debug print (``UtilityAI_Utils.au3:3-5``).

    **This is the port of the source's body, and the source's body calls ``_D`` again**:

    .. code-block:: autoit

        Func _D($msg)
            If $g_b_UAI_Debug Then _D(" " & $msg)
        EndFunc

    Read literally -- and this layer reads the source literally -- the helper has no arm that prints
    anything: with ``$g_b_UAI_Debug`` true (``UtilityAI_Const.au3:2``) it calls itself with the message
    prefixed by a space, and with it false it does nothing at all. So **the switch is false and the
    call is a no-op**, which is the whole of what the 41 call sites in ``UtilityAI_WeaponSets.au3``
    observe in a default run. When the switch is turned on, the source recurses until its own stack
    ends; Python raises ``RecursionError`` at the same point, and that difference is the platform's
    rather than a behaviour this layer chose. The check the source makes is the check here -- a guard
    that returned early instead would be an arm the source does not have.

    ``$msg`` is used by the recursive call exactly as the source uses it: prefixed with a space, and
    otherwise ignored.
    """

    from . import uai_const

    if uai_const.g_b_UAI_Debug:
        _D(" " + str(msg))


def UAI_GetAgentProfession(agent_id: Any) -> int:
    """An agent's primary profession (``UtilityAI_Utils.au3:286-311``).

    GwAu3's two arms are described in this module's header: a player, hero or henchman (a non-zero
    ``LoginNumber``) answers the agent record's ``Primary``; a mob is looked up in the world's NPC
    array. This reads the ported member either way, and the difference is stated there rather than
    hidden here.
    """

    primary, _ = Agent.GetProfessions(int(agent_id))
    return int(primary)


def UAI_GetArmorBonus(profession: Any) -> int:
    """The armour bonus a profession's primary grants (``UtilityAI_Utils.au3:315-324``).

    GwAu3's own three cases, in its own order, with its own comment's numbers.
    """

    profession = int(profession)
    if profession in (_WARRIOR, _PARAGON):
        return _ARMOR_BONUS_HEAVY
    if profession in (_RANGER, _ASSASSIN, _DERVISH):
        return _ARMOR_BONUS_MEDIUM
    return 0


def UAI_GetEstimatedMaxHP(agent_id: Any) -> int:
    """An agent's estimated maximum health (``UtilityAI_Utils.au3:330-342``).

    The level falls back to ``20`` when it reads zero -- GwAu3's own "Default to level 20 if unknown"
    -- and the hard-mode bonus applies only above level twenty, which is what makes a level-20
    character's estimate the same in both modes.
    """

    level = int(Agent.GetLevel(int(agent_id)))
    if level == 0:
        level = _DEFAULT_LEVEL

    base = level * _HP_PER_LEVEL + _HP_BASE
    if Party.IsHardMode() and level > _HARD_MODE_LEVEL:
        base += (level - _HARD_MODE_LEVEL) * _HP_PER_LEVEL
    return base


def UAI_GetEstimatedCurrentHP(agent_id: Any) -> int:
    """An agent's estimated current health (``UtilityAI_Utils.au3:346-349``).

    The fraction the client reports times the estimate above -- **not** the client's own health field,
    which is the point: GwAu3 uses this for agents whose real maximum it does not know.
    """

    fraction = float(Agent.GetHealth(int(agent_id)))
    return int(round(fraction * UAI_GetEstimatedMaxHP(agent_id)))


def UAI_GetBaseArmor(agent_id: Any) -> int:
    """An agent's base armour rating (``UtilityAI_Utils.au3:353-358``): ``level Ãƒâ€” 3 + bonus``."""

    level = int(Agent.GetLevel(int(agent_id)))
    if level == 0:
        level = _DEFAULT_LEVEL
    return level * 3 + UAI_GetArmorBonus(UAI_GetAgentProfession(agent_id))


def UAI_GetPhysicalArmor(agent_id: Any) -> int:
    """Armour against physical damage (``UtilityAI_Utils.au3:362-372``): Warriors get ``+20``."""

    base = UAI_GetBaseArmor(agent_id)
    if UAI_GetAgentProfession(agent_id) == _WARRIOR:
        return base + _WARRIOR_PHYSICAL_BONUS
    return base


def UAI_GetElementalArmor(agent_id: Any) -> int:
    """Armour against elemental damage (``UtilityAI_Utils.au3:376-386``): Rangers get ``+30``."""

    base = UAI_GetBaseArmor(agent_id)
    if UAI_GetAgentProfession(agent_id) == _RANGER:
        return base + _RANGER_ELEMENTAL_BONUS
    return base


def UAI_GetDamageMultiplier(armor: Any) -> float:
    """The damage multiplier for an armour rating (``UtilityAI_Utils.au3:392-396``).

    ``2 ^ ((60 - armour) / 40)``, with the armour clamped at zero -- GwAu3's own clamp, which is why a
    negative rating and a zero rating answer the same multiplier.
    """

    armor = int(armor)
    if armor < 0:
        armor = 0
    return 2 ** ((_DAMAGE_REFERENCE_ARMOR - armor) / _DAMAGE_CURVE_DIVISOR)


def UAI_GetEffectiveArmor(base_armor: Any, penetration: Any = 0) -> int:
    """Armour after penetration (``UtilityAI_Utils.au3:401-405``).

    GwAu3's two short-circuits are kept: no penetration returns the armour **unchanged** (not rounded
    through the arithmetic), and a penetration above ``1`` is capped at ``1`` -- 100% -- rather than
    allowed to invert the armour.
    """

    penetration = float(penetration)
    if penetration <= 0:
        return int(base_armor)
    if penetration > 1:
        penetration = 1
    return int(round(int(base_armor) * (1 - penetration)))


def UAI_EstimateDamage(
    base_damage: Any,
    agent_id: Any,
    damage_type: Any = "physical",
    penetration: Any = 0,
) -> int:
    """Estimate damage against an agent (``UtilityAI_Utils.au3:412-433``).

    GwAu3's arms are kept in its own order: **armour-ignoring damage returns the base damage before
    anything is read** -- so it works for an agent that cannot be resolved -- then the armour is chosen
    by damage type (``physical``; five elemental spellings; anything else is the base rating), the
    penetration is applied, and the result is the base damage times the curve.
    """

    if str(damage_type) == "armor-ignoring":
        return int(base_damage)

    kind = str(damage_type)
    if kind == "physical":
        armor = UAI_GetPhysicalArmor(agent_id)
    elif kind in ("elemental", "fire", "cold", "lightning", "earth"):
        armor = UAI_GetElementalArmor(agent_id)
    else:
        armor = UAI_GetBaseArmor(agent_id)

    effective = UAI_GetEffectiveArmor(armor, penetration)
    return int(round(int(base_damage) * UAI_GetDamageMultiplier(effective)))


def UAI_IsCaster(agent_id: Any) -> bool:
    """Whether the agent's primary is a caster profession (``UtilityAI_Utils.au3:436-445``).

    GwAu3's own five -- Monk, Necromancer, Mesmer, Elementalist, Ritualist -- which are exactly the
    professions whose armour bonus is zero.
    """

    return UAI_GetAgentProfession(agent_id) in (
        _MONK,
        _NECROMANCER,
        _MESMER,
        _ELEMENTALIST,
        _RITUALIST,
    )


def UAI_IsMelee(agent_id: Any) -> bool:
    """Whether the agent's primary is a melee profession (``UtilityAI_Utils.au3:448-457``)."""

    return UAI_GetAgentProfession(agent_id) in (_WARRIOR, _ASSASSIN, _DERVISH)


def UAI_IsRanged(agent_id: Any) -> bool:
    """Whether the agent's primary is a ranged physical profession (``UtilityAI_Utils.au3:460-469``)."""

    return UAI_GetAgentProfession(agent_id) in (_RANGER, _PARAGON)


# ---------------------------------------------------------------------------------------------
# The party layer of the combat engine (``UtilityAI_Utils.au3:143-285``).
#
# These are what `UAI_UseSkills` and `UAI_Fight` are built on: the three aggro questions the slot loop
# asks before it casts, and the called-target a FOLLOW-mode fight copies. Every one of them reads the
# party's own member records and the hero-flag array -- both routed in `py4gw/gwa3/data_party.py` as of
# 2026-10-10, which is what unblocked this section -- and each keeps the source's guard order, including
# the skip of a *flagged* hero (a hero standing where it was told to stand is not the player's aggro to
# chase).
# ---------------------------------------------------------------------------------------------


def Skill_GetSlotByID(skill_id: Any, hero_number: Any = 0) -> Any:
    """The slot holding a skill id, or ``0`` (``UtilityAI_Utils.au3:10-16``).

    The eight slots walked in order, each asked for its ``SkillID`` through
    `py4gw/gwa3/data_skill.py`'s `Skill_GetSkillbarInfo` -- which is why this member was unbuildable
    before that accessor landed. It is also the *useful* spelling of GwAu3's own
    `Skill_GetSkillbarInfo(..., "SlotBySkillID")`, whose guard refuses any real skill id (recorded on
    that member).
    """

    from .data_skill import Skill_GetSkillbarInfo

    for slot in range(1, 9):
        if Skill_GetSkillbarInfo(slot, "SkillID", hero_number) == skill_id:
            return slot
    return 0


def Skill_CheckSlotByID(skill_id: Any, hero_number: Any = 0) -> bool:
    """Whether a skill id is on the bar at all (``UtilityAI_Utils.au3:18-24``).

    `Skill_GetSlotByID`'s loop asked for truth rather than for the slot -- the same reads, the same
    order, the same stopping point.
    """

    from .data_skill import Skill_GetSkillbarInfo

    for slot in range(1, 9):
        if Skill_GetSkillbarInfo(slot, "SkillID", hero_number) == skill_id:
            return True
    return False


def Party_GetSize() -> Any:
    """The current party size (``UtilityAI_Utils.au3:143-145``): the context's own ``TotalPartySize``."""

    from .data_party import Party_GetPartyContextInfo

    return Party_GetPartyContextInfo("TotalPartySize")


def Party_GetHeroCount() -> Any:
    """How many heroes the party holds (``UtilityAI_Utils.au3:148-150``)."""

    from .data_party import Party_GetPartyContextInfo

    return Party_GetPartyContextInfo("HeroCount")


def Party_GetHeroAgentID(hero_number: Any) -> Any:
    """A hero's agent id by hero number, ``0`` meaning the player (``UtilityAI_Utils.au3:153-156``).

    **``0`` is the player.** The source answers ``UAI_GetPlayerInfo($GC_UAI_AGENT_ID)`` for it rather
    than the party's first hero, which is the convention the whole plugin uses for "hero slot 0".
    """

    if hero_number == 0:
        return UAI_GetPlayerInfo(_GC_UAI_AGENT_ID)
    return Party_GetMyPartyHeroInfo(hero_number, "AgentID")


def Party_GetHeroID(hero_number: Any) -> Any:
    """A hero's hero id by hero number, ``0`` meaning the player (``UtilityAI_Utils.au3:159-165``).

    ```UAI_GetPlayerInfo($GC_UAI_AGENT_ID)`` again for slot ``0`` -- the source answers the *agent* id
    there, the same value `Party_GetHeroAgentID` gives, because a player has no hero id.
    """

    if hero_number == 0:
        return UAI_GetPlayerInfo(_GC_UAI_AGENT_ID)
    return Party_GetMyPartyHeroInfo(hero_number, "HeroID")


def Party_GetMembersArray() -> list[int]:
    """The party's agent ids, with **AutoIt's own array contract** (``UtilityAI_Utils.au3:165-198``).

    GwAu3 answers an array whose ``[0]`` is the number of valid entries and whose ``[1..n]`` are the ids:
    the player first (from the live read, falling back to the cache), then the heroes, then the henchmen,
    each skipped when its id is not positive. Python has no such convention, so the list **keeps** it --
    a caller here indexes exactly as GwAu3's callers do, and `Party_IsWiped` below does.
    """

    # Imported here, like the targeting queries above: `data_party` reads `data_agent`, and a module-level
    # import in that direction would close a cycle through this module's own callers.
    from .data_party import Party_GetPartyContextInfo
    from .uai_get_agent import _cached_ids

    hero_count = Party_GetHeroCount()
    hench_count = Party_GetPartyContextInfo("HenchmenCount")

    members: list[int] = [0]
    count = 0

    player_id = Agent_GetMyID()
    if player_id <= 0:
        player_id = UAI_GetPlayerInfo(_GC_UAI_AGENT_ID)
    if player_id > 0:
        count += 1
        members.append(int(player_id))

    for index in range(1, int(hero_count) + 1):
        hero_agent_id = Party_GetMyPartyHeroInfo(index, "AgentID")
        if hero_agent_id <= 0:
            continue
        count += 1
        members.append(int(hero_agent_id))

    for index in range(1, int(hench_count) + 1):
        hench_agent_id = Party_GetMyPartyHenchmanInfo(index, "AgentID")
        if hench_agent_id <= 0:
            continue
        count += 1
        members.append(int(hench_agent_id))

    members[0] = count
    return members


def _party_average_health() -> tuple[float, bool]:
    """``(average, valid)`` -- `Party_GetAverageHealth` with AutoIt's ``@error`` made explicit.

    ``:201-224`` answers the average hit-point **fraction** of the party's living, readable members and
    sets ``@error = 1`` when there are none -- and its only caller reads that flag
    (``Party_IsWiped``: ``Local $l_b_HasAvgHP = (@error = 0)``). Python has no out-of-band error, so the
    pair travels together here and `Party_GetAverageHealth` answers the number alone, as the source does.

    Two of the source's own skips are kept: a member the *cache* does not hold is passed over --
    ``UAI_GetIndexByID(...) = 0``, a row lookup this layer refuses as bookkeeping
    (`py4gw/gwa3/uai_agent.py`), so the live twin is "the client's array does not hold this agent" -- and
    a dead member is passed over. The fraction is clamped to ``0..1`` in the source and rounded to three
    places.
    """

    total_hp = 0.0
    alive_count = 0

    from .uai_get_agent import _cached_ids

    for agent_id in Party_GetMembersArray()[1:]:
        if agent_id <= 0:
            continue
        if agent_id not in _cached_ids():
            continue
        if UAI_GetAgentInfoByID(agent_id, _constants.GC_UAI_AGENT_IsDead):
            continue

        hp = UAI_GetAgentInfoByID(agent_id, _GC_UAI_AGENT_HP)
        if hp < 0:
            hp = 0
        if hp > 1:
            hp = 1
        total_hp += hp
        alive_count += 1

    if alive_count == 0:
        return 0.0, False
    return round(total_hp / alive_count, 3), True


def Party_GetAverageHealth() -> Any:
    """The party's average hit-point fraction, ``0`` when nothing is readable
    (``UtilityAI_Utils.au3:201-224``)."""

    return _party_average_health()[0]


def Party_GetAvailableRezz() -> int:
    """How many resurrection skills the party's **living heroes** hold (``UtilityAI_Utils.au3:257-274``).

    Per hero: its skillbar walked slot by slot through `Skill_GetSkillbarInfo`'s own ``hero_number``
    argument, each non-empty slot's skill tested for GwAu3's ``$GC_I_SKILL_SPECIAL_FLAG_RESURRECTION`` --
    the same ``Special`` word through the same skill table -- and a dead hero skipped entirely.
    """

    hero_rezz_skills = 0
    hero_count = Party_GetHeroCount()

    for hero_number in range(1, int(hero_count) + 1):
        hero_agent_id = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
        if hero_agent_id <= 0:
            continue
        if Agent_GetAgentInfo(hero_agent_id, "IsDead"):
            continue

        for skill_slot in range(1, 9):
            skill_id = Skill_GetSkillbarInfo(skill_slot, "SkillID", hero_number)
            if skill_id == 0:
                continue
            special = Skill_GetSkillInfo(skill_id, "Special")
            if int(special) & _constants.GC_I_SKILL_SPECIAL_FLAG_RESURRECTION:
                hero_rezz_skills += 1

    return hero_rezz_skills


def Party_IsWiped() -> bool:
    """Whether the party is wiped (``UtilityAI_Utils.au3:227-254``).

    The source's prerequisites and thresholds, in its order: **the player's death is required** (``:229``);
    then the living-hero count against "all non-player members" (``:242-243``, computed from the members
    array's own count so the threshold follows the party's size); then no available resurrection, the
    threshold, or an average health below ``0.15`` (``:249``).
    """

    if not Agent_GetAgentInfo(-2, "IsDead"):
        return False

    dead_heroes = 0
    for hero_number in range(1, int(Party_GetHeroCount()) + 1):
        hero_agent_id = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
        if hero_agent_id <= 0:
            continue
        if Agent_GetAgentInfo(hero_agent_id, "IsDead"):
            dead_heroes += 1

    available_rezz = Party_GetAvailableRezz()
    party_array = Party_GetMembersArray()
    dead_threshold = party_array[0] - 1
    if dead_threshold < 0:
        dead_threshold = 0

    average_hp, has_average_hp = _party_average_health()
    low_average_hp = has_average_hp and average_hp < 0.15

    if available_rezz == 0 or dead_heroes >= dead_threshold or low_average_hp:
        return True

    return False


def UAI_CountEnemyInPartyAggroRange(aggro_range: float = 1320) -> Any:
    """An enemy in the player's aggro range, or in an unflagged hero's (``UtilityAI_Utils.au3:29-49``).

    **The name says "count" and the answer is not always one**: the player branch returns
    `UAI_GetNearestAgent`'s **agent id**, while the hero branch returns `UAI_CountAgents`'s **count**.
    That is the source's own arithmetic and it is kept -- a caller uses the truthiness of the answer to
    decide whether a fight is on, which is why `UAI_Fight` compares it with ``= 0``.

    The hero loop keeps all three of GwAu3's skips, in its order: a hero with a non-zero flag is passed
    over (``:39``), a hero with no agent answers nothing (``:42``), and a match ends the loop.
    """

    from .uai_get_agent import UAI_CountAgents, UAI_GetNearestAgent

    enemy = UAI_GetNearestAgent(-2, aggro_range, "UAI_Filter_IsLivingEnemy")
    if enemy != 0:
        return enemy

    hero_count = Party_GetMyPartyInfo("ArrayHeroPartyMemberSize")

    for index in range(1, int(hero_count) + 1):
        flag_x = Party_GetHeroFlagInfo(index, "FlagX")
        flag_y = Party_GetHeroFlagInfo(index, "FlagY")

        if flag_x != 0 or flag_y != 0:
            continue

        hero_agent_id = Party_GetMyPartyHeroInfo(index, "AgentID")
        if hero_agent_id == 0:
            continue

        enemy = UAI_CountAgents(hero_agent_id, aggro_range, "UAI_Filter_IsLivingEnemy")
        if enemy != 0:
            return enemy

    return 0


def UAI_IsEnemyInPartyAggroRange(aggro_range: float = 1320) -> bool:
    """Whether any enemy is in the player's or an unflagged hero's aggro range
    (``UtilityAI_Utils.au3:51-71``).

    `UAI_CountEnemyInPartyAggroRange`'s own loop with the boolean question asked at each step -- the
    same three skips, and the player's answer short-circuits before the party is read at all.
    """

    from .uai_get_agent import UAI_IsAgentInRange

    in_range = UAI_IsAgentInRange(-2, aggro_range, "UAI_Filter_IsLivingEnemy")
    if in_range:
        return True

    hero_count = Party_GetMyPartyInfo("ArrayHeroPartyMemberSize")

    for index in range(1, int(hero_count) + 1):
        flag_x = Party_GetHeroFlagInfo(index, "FlagX")
        flag_y = Party_GetHeroFlagInfo(index, "FlagY")

        if flag_x != 0 or flag_y != 0:
            continue

        hero_agent_id = Party_GetMyPartyHeroInfo(index, "AgentID")
        if hero_agent_id == 0:
            continue

        in_range = UAI_IsAgentInRange(hero_agent_id, aggro_range, "UAI_Filter_IsLivingEnemy")
        if in_range:
            return True

    return False


def UAI_GetNearestEnemyInPartyRange(aggro_range: float = 1320) -> Any:
    """The enemy nearest the *player* that is inside the aggro range of the player or an unflagged hero
    (``UtilityAI_Utils.au3:76-128``).

    Two distances and they are not the same one: an enemy qualifies by its distance to a **hero**
    (``:110-115``, squared, from the hero's own ``X``/``Y``), and the winner is chosen by its distance to
    the **player** (``:118-122``, the ``Distance`` column). The cached column is computed here the way
    the source's cache fills it (`py4gw/gwa3/uai_get_agent.py`'s `_cached_distance`), because this layer
    reads live rather than from a frame's copy.

    ``999999`` is the source's own starting best, and the comparison is strict, so the first enemy at
    that distance wins -- which for a plugin looping per frame is a stable choice and for a caller here
    is simply the source's rule.
    """

    # Imported here, not at module scope: `uai_filter` reads this module for the profession predicates,
    # so a module-level import in this direction is a cycle. The same reason `uai_agent` resolves
    # `AgentArray` inside its own function.
    from .uai_filter import UAI_Filter_IsLivingEnemy

    from .uai_filter import UAI_Filter_IsLivingEnemy
    from .uai_get_agent import UAI_GetNearestAgent, _cached_distance, _cached_ids

    enemy = UAI_GetNearestAgent(-2, aggro_range, "UAI_Filter_IsLivingEnemy")
    if enemy != 0:
        return enemy

    hero_count = Party_GetMyPartyInfo("ArrayHeroPartyMemberSize")
    best_enemy = 0
    best_distance = 999999

    for index in range(1, int(hero_count) + 1):
        flag_x = Party_GetHeroFlagInfo(index, "FlagX")
        flag_y = Party_GetHeroFlagInfo(index, "FlagY")
        if flag_x != 0 or flag_y != 0:
            continue

        hero_agent_id = Party_GetMyPartyHeroInfo(index, "AgentID")
        if hero_agent_id == 0:
            continue

        hero_x = UAI_GetAgentInfoByID(hero_agent_id, _GC_UAI_AGENT_X)
        hero_y = UAI_GetAgentInfoByID(hero_agent_id, _GC_UAI_AGENT_Y)

        range_squared = aggro_range * aggro_range

        for agent_id in _cached_ids():
            if not UAI_Filter_IsLivingEnemy(agent_id):
                continue

            enemy_x = UAI_GetAgentInfo(agent_id, _GC_UAI_AGENT_X)
            enemy_y = UAI_GetAgentInfo(agent_id, _GC_UAI_AGENT_Y)
            dx = enemy_x - hero_x
            dy = enemy_y - hero_y

            if (dx * dx + dy * dy) > range_squared:
                continue

            distance_to_player = _cached_distance(agent_id)

            if distance_to_player < best_distance:
                best_distance = distance_to_player
                best_enemy = agent_id

    return best_enemy


def UAI_GetPartyCalledTarget() -> Any:
    """The called target of the first **other** player in the party, or ``0``
    (``UtilityAI_Utils.au3:131-140``).

    ``UAI_Fight``'s FOLLOW mode copies this onto its forced target, which is how a bot fights what the
    party's caller called. "Other" is decided by login number, and the loop's order is the party array's
    -- so the first non-self player who has called anything wins, not the nearest or the leader.
    """

    player_count = Party_GetMyPartyInfo("ArrayPlayerPartyMemberSize")
    my_login_number = Agent_GetAgentInfo(-2, "LoginNumber")

    for index in range(1, int(player_count) + 1):
        if Party_GetMyPartyPlayerMemberInfo(index, "LoginNumber") == my_login_number:
            continue

        called_target = Party_GetMyPartyPlayerMemberInfo(index, "CalledTargetID")
        if called_target != 0:
            return called_target

    return 0
