"""GwAu3's ``UAI_Filter_*`` predicates, over this project's own agent reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Sixty-four predicates, and the module is worth reading as a map of what an agent question costs.**
Each is a small conjunction over the `UAI_GetAgentInfoByID` columns -- allegiance, health fraction, the
effect word, the type word -- so most of them route for free through `py4gw/gwa3/uai_agent.py`, which
answers those columns from the client. The refusals are the interesting half and they fall into two
groups, each of which says something:

* **the NPC profession predicates** -- Warrior through Dervish -- which GwAu3 answers by walking the
  world's **NPC array**; `UAI_GetAgentProfession` in `py4gw/gwa3/uai_utils.py` records that mechanism
  difference, and these are routed through it with GwAu3's own "only an NPC" guard kept;
* **the ones that read state this layer does not have** -- the two NPC-flag predicates that need the
  world's `NpcArray` columns, `IsNotAvoided` (GwAu3's own avoid list), `IsExploitableCorpse` (a
  cache-only column) and the two that read GwAu3's `$g_i_BestTarget`.

**Two groups used to refuse here and do not any more**, both because a missing member landed rather than
because a test was relaxed: the seven visible-effect predicates now walk the agent's own list, and the
three model-state predicates (`IsMoving`, `IsAttacking`, `IsIdle`) now answer, because this project's
porting authority settles the disagreement between GwAu3's two files about what those model states mean
(`py4gw/gwa3/uai_agent.py`).
"""

from __future__ import annotations

from typing import Any

from .uai_agent import UAI_GetAgentInfo, UAI_GetPlayerInfo
from .uai_effects import UAI_AgentHasVisibleEffect
from .uai_utils import UAI_IsCaster, UAI_IsMelee, UAI_IsRanged
from . import constants as _constants
from .uai_utils import UAI_GetAgentProfession

__all__ = [
    "UAI_Filter_AgentHasMoreHpThanMe",
    "UAI_Filter_ExcludeMe",
    "UAI_Filter_IdConditionedOrEnchanted",
    "UAI_Filter_IsAbove50HP",
    "UAI_Filter_IsAssassin",
    "UAI_Filter_IsAttacking",
    "UAI_Filter_IsBelow25HP",
    "UAI_Filter_IsBelow50HP",
    "UAI_Filter_IsBleeding",
    "UAI_Filter_IsBlind",
    "UAI_Filter_IsBoss",
    "UAI_Filter_IsBurning",
    "UAI_Filter_IsCaster",
    "UAI_Filter_IsCasting",
    "UAI_Filter_IsConditioned",
    "UAI_Filter_IsControlledMinion",
    "UAI_Filter_IsControlledSpirit",
    "UAI_Filter_IsCrippled",
    "UAI_Filter_IsDazed",
    "UAI_Filter_IsDeadAlly",
    "UAI_Filter_IsDeadEnemy",
    "UAI_Filter_IsDeadNPC",
    "UAI_Filter_IsDeepWounded",
    "UAI_Filter_IsDegenHexed",
    "UAI_Filter_IsDervish",
    "UAI_Filter_IsDiseased",
    "UAI_Filter_IsElementalist",
    "UAI_Filter_IsEnchanted",
    "UAI_Filter_IsExploitableCorpse",
    "UAI_Filter_IsGadget",
    "UAI_Filter_IsGadgetOrLiving",
    "UAI_Filter_IsHarbingers",
    "UAI_Filter_IsHexed",
    "UAI_Filter_IsHexedOrConditioned",
    "UAI_Filter_IsHexedOrEnchanted",
    "UAI_Filter_IsIdle",
    "UAI_Filter_IsKnocked",
    "UAI_Filter_IsLastStrikeIsDual",
    "UAI_Filter_IsLastStrikeIsLead",
    "UAI_Filter_IsLastStrikeIsOffHand",
    "UAI_Filter_IsLastStrikeLeadOrOffHand",
    "UAI_Filter_IsLivingAlly",
    "UAI_Filter_IsLivingEnemy",
    "UAI_Filter_IsLivingNPC",
    "UAI_Filter_IsMelee",
    "UAI_Filter_IsMesmer",
    "UAI_Filter_IsMinion",
    "UAI_Filter_IsMonk",
    "UAI_Filter_IsMoving",
    "UAI_Filter_IsNecromancer",
    "UAI_Filter_IsNotAvoided",
    "UAI_Filter_IsNotCaster",
    "UAI_Filter_IsNotDeepWounded",
    "UAI_Filter_IsNotPoisoned",
    "UAI_Filter_IsParagon",
    "UAI_Filter_IsPoisoned",
    "UAI_Filter_IsRanger",
    "UAI_Filter_IsRanged",
    "UAI_Filter_IsRitualist",
    "UAI_Filter_IsSpirit",
    "UAI_Filter_IsWarrior",
    "UAI_Filter_IsWeakness",
    "UAI_Filter_IsWeaponSpelled",
    "UAI_Filter_NotIsDeepWounded",
]

# GwAu3's own allegiance numbers, as its predicates spell them (``UtilityAI_AgentFilter.au3:37``,
# ``:51``, ``:65``, ``:425``, ``:468``): Ally ``1``, Enemy ``3``, Spirit ``4``, Minion ``5``,
# NPC ``6``.
_ALLY = 1
_ENEMY = 3
_SPIRIT = 4
_MINION = 5
_NPC = 6

#: GwAu3's three ``LastStrike`` values (``:11``, ``:16``, ``:21``): lead hand, off hand, dual.
_LAST_STRIKE_LEAD = 1
_LAST_STRIKE_OFFHAND = 2
_LAST_STRIKE_DUAL = 3

#: The three Harbinger player numbers (``:553``).
_HARBINGER_NUMBERS = (5458, 5459, 5460)


def _info(agent_id: Any, column: str) -> Any:
    """One column, by the name the generated constants give it."""

    return UAI_GetAgentInfo(agent_id, getattr(_constants, f"GC_UAI_AGENT_{column}"))


def _living(agent_id: Any, allegiance: int) -> bool:
    """The shape four predicates share: right allegiance, health left, not dead (``:36-75``)."""

    if int(_info(agent_id, "Allegiance")) != allegiance:
        return False
    if float(_info(agent_id, "HP")) <= 0:
        return False
    if _info(agent_id, "IsDead"):
        return False
    return True


def _dead(agent_id: Any, allegiance: int) -> bool:
    """Its inverse: right allegiance, no health left, dead (``:43-75``)."""

    if int(_info(agent_id, "Allegiance")) != allegiance:
        return False
    if float(_info(agent_id, "HP")) > 0:
        return False
    if not _info(agent_id, "IsDead"):
        return False
    return True


def _profession_of_npc(agent_id: Any, profession: int) -> bool:
    """GwAu3's NPC-profession predicate shape (``:184-421``).

    Its guard is kept: a **player, hero or henchman answers ``False``** -- ``LoginNumber <> 0`` -- so
    these predicates mean "an NPC of this profession", not "any agent of it". The profession itself
    comes from `UAI_GetAgentProfession`, whose own docstring records the one mechanism difference.
    """

    if int(_info(agent_id, "LoginNumber")) != 0:
        return False
    return UAI_GetAgentProfession(agent_id) == profession


# -- the gadget, last-strike and allegiance predicates -------------------------------------------


def UAI_Filter_IsGadget(agent_id: Any) -> bool:
    """``:4-8``. Not an item type and not a living type."""

    if _info(agent_id, "IsItemType"):
        return False
    if _info(agent_id, "IsLivingType"):
        return False
    return True


def UAI_Filter_IsGadgetOrLiving(agent_id: Any) -> bool:
    """``:31-34``. Not an item type -- note it is *not* the same test as `IsGadget`."""

    if _info(agent_id, "IsItemType"):
        return False
    return True


def UAI_Filter_IsLastStrikeIsLead(agent_id: Any) -> bool:
    """``:10-13``. ``LastStrike`` is ``1``."""

    return int(_info(agent_id, "LastStrike")) == _LAST_STRIKE_LEAD


def UAI_Filter_IsLastStrikeIsOffHand(agent_id: Any) -> bool:
    """``:15-18``. ``LastStrike`` is ``2``."""

    return int(_info(agent_id, "LastStrike")) == _LAST_STRIKE_OFFHAND


def UAI_Filter_IsLastStrikeIsDual(agent_id: Any) -> bool:
    """``:20-23``. ``LastStrike`` is ``3``."""

    return int(_info(agent_id, "LastStrike")) == _LAST_STRIKE_DUAL


def UAI_Filter_IsLastStrikeLeadOrOffHand(agent_id: Any) -> bool:
    """``:25-29``. ``LastStrike`` is ``1`` or ``2`` -- one read, two comparisons."""

    last_strike = int(_info(agent_id, "LastStrike"))
    return last_strike in (_LAST_STRIKE_LEAD, _LAST_STRIKE_OFFHAND)


def UAI_Filter_IsLivingEnemy(agent_id: Any) -> bool:
    """``:36-41``. Enemy allegiance, health left, not dead."""

    return _living(agent_id, _ENEMY)


def UAI_Filter_IsDeadEnemy(agent_id: Any) -> bool:
    """``:43-48``. Enemy allegiance, no health, dead."""

    return _dead(agent_id, _ENEMY)


def UAI_Filter_IsLivingAlly(agent_id: Any) -> bool:
    """``:50-55``."""

    return _living(agent_id, _ALLY)


def UAI_Filter_IsDeadAlly(agent_id: Any) -> bool:
    """``:57-62``."""

    return _dead(agent_id, _ALLY)


def UAI_Filter_IsLivingNPC(agent_id: Any) -> bool:
    """``:64-69``."""

    return _living(agent_id, _NPC)


def UAI_Filter_IsDeadNPC(agent_id: Any) -> bool:
    """``:71-76``."""

    return _dead(agent_id, _NPC)


def UAI_Filter_IsBoss(agent_id: Any) -> bool:
    """``:78-81``. The boss-glow bit of the type map."""

    return bool(_info(agent_id, "HasBossGlow"))


def UAI_Filter_ExcludeMe(agent_id: Any) -> bool:
    """``:83-86``. False for the controlled character, true for everyone else."""

    return int(agent_id) != int(UAI_GetPlayerInfo(getattr(_constants, "GC_UAI_AGENT_ID")))


# -- the effect-word predicates -----------------------------------------------------------------


def UAI_Filter_IsEnchanted(agent_id: Any) -> bool:
    """``:120-122``, and the next nine are the same one-line shape over other columns."""

    return bool(_info(agent_id, "IsEnchanted"))


def UAI_Filter_IsConditioned(agent_id: Any) -> bool:
    """``:124-126``."""

    return bool(_info(agent_id, "IsConditioned"))


def UAI_Filter_IsCrippled(agent_id: Any) -> bool:
    """``:128-130``."""

    return bool(_info(agent_id, "IsCrippled"))


def UAI_Filter_IsDeepWounded(agent_id: Any) -> bool:
    """``:132-134``."""

    return bool(_info(agent_id, "IsDeepWounded"))


def UAI_Filter_NotIsDeepWounded(agent_id: Any) -> bool:
    """``:136-138``. GwAu3 spells this one one way here and another below -- see `IsNotDeepWounded`."""

    return not _info(agent_id, "IsDeepWounded")


def UAI_Filter_IsDegenHexed(agent_id: Any) -> bool:
    """``:140-142``."""

    return bool(_info(agent_id, "IsDegenHexed"))


def UAI_Filter_IsHexed(agent_id: Any) -> bool:
    """``:144-146``."""

    return bool(_info(agent_id, "IsHexed"))


def UAI_Filter_IsWeaponSpelled(agent_id: Any) -> bool:
    """``:160-162``."""

    return bool(_info(agent_id, "IsWeaponSpelled"))


def UAI_Filter_IsKnocked(agent_id: Any) -> bool:
    """``:164-166``, over the **``IsKnockedDown``** column."""

    return bool(_info(agent_id, "IsKnockedDown"))


def UAI_Filter_IsCasting(agent_id: Any) -> bool:
    """``:176-178``. Routed, and the only one of the four activity predicates that is.

    `IsMoving`, `IsAttacking` and `IsIdle` refuse because GwAu3's two files disagree about their model
    state sets; `IsCasting`'s sets match, so it answers.
    """

    return bool(_info(agent_id, "IsCasting"))


def UAI_Filter_IsHexedOrEnchanted(agent_id: Any) -> bool:
    """``:148-150``. Two reads, an ``Or``."""

    return bool(_info(agent_id, "IsHexed")) or bool(_info(agent_id, "IsEnchanted"))


def UAI_Filter_IdConditionedOrEnchanted(agent_id: Any) -> bool:
    """``:152-154``. GwAu3's own typo in the name is kept -- a script calls this spelling."""

    return bool(_info(agent_id, "IsConditioned")) or bool(_info(agent_id, "IsEnchanted"))


def UAI_Filter_IsHexedOrConditioned(agent_id: Any) -> bool:
    """``:156-158``."""

    return bool(_info(agent_id, "IsHexed")) or bool(_info(agent_id, "IsConditioned"))


def UAI_Filter_IsNotPoisoned(agent_id: Any) -> bool:
    """``:543-545``."""

    return not _info(agent_id, "IsPoisoned")


def UAI_Filter_IsNotDeepWounded(agent_id: Any) -> bool:
    """``:547-549``. The second spelling of the same test as `NotIsDeepWounded`."""

    return not _info(agent_id, "IsDeepWounded")


# -- the health-fraction predicates ---------------------------------------------------------------


def UAI_Filter_IsBelow50HP(agent_id: Any) -> bool:
    """``:510-512``. The **health fraction**, not the health."""

    return float(_info(agent_id, "HP")) < 0.5


def UAI_Filter_IsBelow25HP(agent_id: Any) -> bool:
    """``:514-516``."""

    return float(_info(agent_id, "HP")) < 0.25


def UAI_Filter_IsAbove50HP(agent_id: Any) -> bool:
    """``:518-520``. Note it is strictly above, so exactly half satisfies neither it nor ``Below50``."""

    return float(_info(agent_id, "HP")) > 0.5


def UAI_Filter_IsHarbingers(agent_id: Any) -> bool:
    """``:551-555``. Three player numbers, which are the Harbingers' own."""

    return int(_info(agent_id, "PlayerNumber")) in _HARBINGER_NUMBERS


# -- the profession predicates --------------------------------------------------------------------


def UAI_Filter_IsWarrior(agent_id: Any) -> bool:
    """``:184-206``. An **NPC** whose primary is Warrior."""

    return _profession_of_npc(agent_id, 1)


def UAI_Filter_IsRanger(agent_id: Any) -> bool:
    """``:208-230``."""

    return _profession_of_npc(agent_id, 2)


def UAI_Filter_IsMonk(agent_id: Any) -> bool:
    """``:232-254``."""

    return _profession_of_npc(agent_id, 3)


def UAI_Filter_IsNecromancer(agent_id: Any) -> bool:
    """``:256-278``."""

    return _profession_of_npc(agent_id, 4)


def UAI_Filter_IsMesmer(agent_id: Any) -> bool:
    """``:280-302``."""

    return _profession_of_npc(agent_id, 5)


def UAI_Filter_IsElementalist(agent_id: Any) -> bool:
    """``:304-326``."""

    return _profession_of_npc(agent_id, 6)


def UAI_Filter_IsAssassin(agent_id: Any) -> bool:
    """``:328-350``."""

    return _profession_of_npc(agent_id, 7)


def UAI_Filter_IsRitualist(agent_id: Any) -> bool:
    """``:352-374``."""

    return _profession_of_npc(agent_id, 8)


def UAI_Filter_IsParagon(agent_id: Any) -> bool:
    """``:376-398``."""

    return _profession_of_npc(agent_id, 9)


def UAI_Filter_IsDervish(agent_id: Any) -> bool:
    """``:400-422``."""

    return _profession_of_npc(agent_id, 10)


def UAI_Filter_IsMelee(agent_id: Any) -> bool:
    """``:526-528``. GwAu3 delegates to `UAI_IsMelee`, and so does this."""

    return UAI_IsMelee(agent_id)


def UAI_Filter_IsCaster(agent_id: Any) -> bool:
    """``:530-532``."""

    return UAI_IsCaster(agent_id)


def UAI_Filter_IsRanged(agent_id: Any) -> bool:
    """``:534-536``."""

    return UAI_IsRanged(agent_id)


def UAI_Filter_IsNotCaster(agent_id: Any) -> bool:
    """``:538-541``."""

    return not UAI_IsCaster(agent_id)


def UAI_Filter_IsSpirit(agent_id: Any) -> bool:
    """``:424-447``. Spirit allegiance, not a logged-in player, and the spirit flag in the NPC record.

    **The last test is the one that refuses.** GwAu3 reads the NPC record's flags word at ``+0x?`` and
    tests ``0x4000``; this project's world family refuses the ``NpcArray`` columns (see
    ``docs/GWA3_ROUTE_MAP.md``), so that flag has no route -- and the first three conditions are not
    the predicate, they are what it narrows to.
    """

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:424-447 answers True for spirit allegiance (`4`), a zero login "
        "number, and **`BitAND($l_i_NpcFlags, 0x4000) <> 0`** -- a flag in the world's NPC record. "
        "This project's `World_GetWorldInfo` refuses the `NpcArray` columns "
        "(`py4gw/gwa3/data_world.py` records why, and the route map carries the rows), so the flag has "
        "no route. The first three conditions are readable here (`UAI_GetAgentInfo` answers "
        "`Allegiance` and `LoginNumber`), but they are not the predicate: answering True on them alone "
        "would call every non-player spirit-ally a spirit."
    )


def UAI_Filter_IsControlledSpirit(agent_id: Any) -> bool:
    """``:449-465``. **Refused with `IsSpirit`**, which is its first guard."""

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:449-465 first asks `UAI_Filter_IsSpirit` and then walks the world's "
        "`Others` array for the agent id. `IsSpirit` refuses for want of the NPC flags word "
        "(`docs/GWA3_ROUTE_MAP.md` records the `NpcArray` refusal), and the `Others` walk is the "
        "party's own array, which `py4gw/party.py` reads as `GetOthers`. Both halves are needed; "
        "neither alone is the predicate."
    )


def UAI_Filter_IsMinion(agent_id: Any) -> bool:
    """``:467-490``. **Refused with `IsSpirit`**, for the same NPC flags word (``0x100`` there)."""

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:467-490 answers True for minion allegiance (`5`), a zero login "
        "number and **`BitAND($l_i_NpcFlags, 0x100) <> 0`** from the world's NPC record -- the same "
        "refused `NpcArray` column `IsSpirit` needs, with a different bit "
        "(`py4gw/gwa3/data_world.py` refuses those keys). The first two conditions are readable; the "
        "flag is the predicate."
    )


def UAI_Filter_IsControlledMinion(agent_id: Any) -> bool:
    """``:492-508``. **Refused with `IsMinion`**, which is its first guard."""

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:492-508 asks `UAI_Filter_IsMinion` and then walks the world's "
        "`Others` array. Refused for the same reasons as `UAI_Filter_IsControlledSpirit`: "
        "`IsMinion`'s NPC flags word has no route, and the `Others` walk is `py4gw/party.py`'s "
        "`GetOthers`."
    )


# -- the predicates built on the three disagreeing columns ----------------------------------------


def UAI_Filter_IsMoving(agent_id: Any) -> bool:
    """``:557`` -- moving: the velocity words or one of the three moving model states.

    **This one answered ``REFUSED`` until the model-state disagreement was settled with evidence.** The
    column is one of the three GwAu3's own files read differently, and this layer answers the definition
    Reforged Native agrees with (`py4gw/gwa3/uai_agent.py` carries the comparison, the live measurement of
    model state ``0x40``, and the divergence that remains for a caller comparing against GwAu3's plugin).
    """

    return bool(_info(agent_id, "IsMoving"))


def UAI_Filter_IsAttacking(agent_id: Any) -> bool:
    """``:561`` -- attacking: model states ``0x60``, ``0x440``, ``0x460`` (see `UAI_Filter_IsMoving`)."""

    return bool(_info(agent_id, "IsAttacking"))


def UAI_Filter_IsIdle(agent_id: Any) -> bool:
    """``:565`` -- idle: model states ``0x44``, ``0x40``, ``0x64`` (see `UAI_Filter_IsMoving`)."""

    return bool(_info(agent_id, "IsIdle"))


def UAI_Filter_IsExploitableCorpse(agent_id: Any) -> bool:
    """**REFUSED: the `IsExploitableCorpse` column is cache-only in GwAu3.**"""

    return bool(_info(agent_id, "IsExploitableCorpse"))


# -- the visible-effect predicates ----------------------------------------------------------------
#
# Each is one line in the source -- `UAI_AgentHasVisibleEffect($a_i_AgentID,
# $GC_I_EFFECT_TYPE_STATUS, $GC_I_EFFECT_ID_<NAME>)` -- so each is one line here, with the id named
# literally rather than reached through its spelling. The member they call is ported
# (`py4gw/gwa3/uai_effects.py`), and the alternative those predicates refused against is still the
# wrong answer: GwAu3's own comment records that the agent record's condition bit is a *different*
# test from its visible-effect rows.


def UAI_Filter_IsDiseased(agent_id: Any) -> bool:
    """``:93`` -- disease, from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_DISEASED
    )


def UAI_Filter_IsDazed(agent_id: Any) -> bool:
    """``:97`` -- dazed, from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_DAZED
    )


def UAI_Filter_IsWeakness(agent_id: Any) -> bool:
    """``:101`` -- weakness (and cracked armor), from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_WEAKNESS
    )


def UAI_Filter_IsPoisoned(agent_id: Any) -> bool:
    """``:105`` -- poison, from the visible-effect rows.

    Note the contrast with `IsNotPoisoned`, which answers the *negative* from the agent record's own
    ``IsPoisoned`` column: two spellings of one question, two different mechanisms in the source, and
    both routed here.
    """

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_POISONED
    )


def UAI_Filter_IsBlind(agent_id: Any) -> bool:
    """``:109`` -- blindness, from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_BLINDED
    )


def UAI_Filter_IsBurning(agent_id: Any) -> bool:
    """``:113`` -- burning, from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_BURNING
    )


def UAI_Filter_IsBleeding(agent_id: Any) -> bool:
    """``:117`` -- bleeding, from the visible-effect rows."""

    return UAI_AgentHasVisibleEffect(
        agent_id, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_BLEEDING
    )


# -- the two that read GwAu3's own globals --------------------------------------------------------


def UAI_Filter_AgentHasMoreHpThanMe(agent_id: Any) -> bool:
    """**REFUSED: it reads GwAu3's own ``$g_i_BestTarget``, not the agent it is given.**

    ``:522-524`` is ``Return UAI_GetEstimatedCurrentHP($g_i_BestTarget) >
    UAI_GetPlayerInfo($GC_UAI_AGENT_CurrentHP)`` -- note it **ignores its own argument** and uses the
    global the planner last set. That global is GwAu3's own state; the comparison itself is portable
    and needs the agent passed in rather than the global, which is a change to the function's
    behaviour and not this layer's to make.
    """

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:522-524 compares **`$g_i_BestTarget`** -- GwAu3's own global, set by "
        "its planner -- against the player's current health, ignoring the `$a_i_AgentID` it is passed. "
        "This project keeps no such global (`py4gw/gwa3/uai_agent.py` records the same divergence for "
        "the agent cache), and the comparison the function's *name* describes would need the argument "
        "used instead, which is a behaviour change rather than a port."
    )


def UAI_Filter_IsNotAvoided(agent_id: Any) -> bool:
    """**REFUSED: it reads GwAu3's own ``$g_v_AvoidPlayerNumbers``.**

    ``:557-570`` answers ``True`` when that variable is ``-1``, then checks whether the agent's player
    number is in it -- as an array or as a single value. It is a caller-set option list in GwAu3's own
    process, not a client fact, and this layer holds no equivalent.
    """

    raise NotImplementedError(
        "UtilityAI_AgentFilter.au3:557-570 tests the agent's player number against GwAu3's own "
        "`$g_v_AvoidPlayerNumbers` -- a caller-set option in GwAu3's process, answered `True` outright "
        "when it is `-1`. This project keeps no such option list; the *question* is a caller's, so the "
        "list belongs with the caller (a filter over `UAI_GetAgentInfo(agent, "
        "GC_UAI_AGENT_PlayerNumber)`), not in this layer."
    )
