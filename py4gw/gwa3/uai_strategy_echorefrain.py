"""GwAu3's ``UtilityAI_EchoRefrain.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **32 of this file's 32 are transcribed and 0
refuse** -- a body the translator cannot read, or one calling a name this layer does not implement,
refuses by name rather than answering a plausible target.

Their callees are this layer's own: ``UAI_GetNearestAgent``, ``UAI_GetAgentLowest``,
``UAI_GetPlayerInfo``, ``UAI_GetBestSingleTarget``, ``UAI_PlayerHasEffect``,
``UAI_GetPlayerEffectInfo``, ``Party_GetPetInfo`` and the ``Anti_*`` predicates in
`py4gw/gwa3/uai_anti.py`.
"""

from __future__ import annotations

import math
from typing import Any

from . import constants as _constants
from . import uai_const
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import UAI_AgentHasEffect, UAI_GetPlayerEffectInfo, UAI_PlayerHasEffect
from .uai_filter import (
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsLivingEnemy,
    UAI_Filter_IsMoving,
    UAI_Filter_IsSpirit,
)
from .uai_get_agent import (
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestSingleTarget,
    UAI_GetFarthestAgent,
    UAI_GetNearestAgent,
)
from .uai_anti import (
    Anti_Attack,
    Anti_Chant,
    Anti_EchoRefrain,
    Anti_Enchantment,
    Anti_Form,
    Anti_Glyph,
    Anti_Hex,
    Anti_ItemSpell,
    Anti_PetAttack,
    Anti_Preparation,
    Anti_Ritual,
    Anti_Shout,
    Anti_Signet,
    Anti_Skill10,
    Anti_Skill16,
    Anti_Spell,
    Anti_Stance,
    Anti_Trap,
    Anti_Ward,
    Anti_WeaponSpell,
    Anti_Well,
)
from .data_attribute import Attribute_GetPartyAttributeInfo
from .uai_agent import (
    UAI_GetAgentInfo,
    UAI_GetPlayerInfo,
)
from .uai_effects import (
    UAI_AgentHasEffect,
    UAI_GetPlayerEffectInfo,
)
from .uai_filter import (
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsSpirit,
)
from .uai_get_agent import (
    UAI_CountAgents,
    _cached_distance,
    _cached_ids,
)
from .uai_utils import Party_GetMembersArray


def CanUse_EnduringHarmony() -> Any:
    """``UtilityAI_EchoRefrain.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_EnduringHarmony(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:13`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_BlazingFinale() -> Any:
    """``UtilityAI_EchoRefrain.au3:22`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_BlazingFinale(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:27`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_BLAZING_FINALE):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_BurningRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:69`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_BurningRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:74`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 999999
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_BURNING_REFRAIN):
            continue
        l_f_CurrentHP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_CurrentHP)
        if l_f_CurrentHP < l_f_LowestHP:
            l_f_LowestHP = l_f_CurrentHP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_FinaleOfRestoration() -> Any:
    """``UtilityAI_EchoRefrain.au3:113`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_FinaleOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:118`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_FINALE_OF_RESTORATION):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_MendingRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:157`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_MendingRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:162`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_MENDING_REFRAIN):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_PurifyingFinale() -> Any:
    """``UtilityAI_EchoRefrain.au3:201`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_PurifyingFinale(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:206`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_PURIFYING_FINALE):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsConditioned):
            continue
        return l_i_AgentID

    return 0


def CanUse_BladeturnRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:239`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_BladeturnRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:244`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_BLADETURN_REFRAIN):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_SoldiersFury() -> Any:
    """``UtilityAI_EchoRefrain.au3:286`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOLDIERS_FURY, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_SoldiersFury(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:292`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AggressiveRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:301`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AGGRESSIVE_REFRAIN, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AggressiveRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:307`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergizingFinale() -> Any:
    """``UtilityAI_EchoRefrain.au3:316`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_EnergizingFinale(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:321`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestEnergy = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_ENERGIZING_FINALE):
            continue
        l_f_Energy = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_EnergyPercent)
        if l_f_Energy < l_f_LowestEnergy:
            l_f_LowestEnergy = l_f_Energy
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_HastyRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:360`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_HastyRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:365`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_FarthestDist = 0
    l_i_FallbackAlly = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_AgentHasEffect(l_i_AgentID, _constants.GC_I_SKILL_ID_HASTY_REFRAIN):
            continue
        if l_i_FallbackAlly == 0:
            l_i_FallbackAlly = l_i_AgentID
        if l_f_Distance > l_f_FarthestDist:
            l_f_FarthestDist = l_f_Distance
            l_i_BestAlly = l_i_AgentID


        if l_i_BestAlly != 0:
            return l_i_BestAlly
        return l_i_FallbackAlly


def CanUse_BlazingFinalePvP() -> Any:
    """``UtilityAI_EchoRefrain.au3:408`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_BlazingFinalePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:413`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_BladeturnRefrainPvP() -> Any:
    """``UtilityAI_EchoRefrain.au3:422`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_BladeturnRefrainPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:427`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_FinaleOfRestorationPvP() -> Any:
    """``UtilityAI_EchoRefrain.au3:436`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_FinaleOfRestorationPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:441`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_MendingRefrainPvP() -> Any:
    """``UtilityAI_EchoRefrain.au3:450`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_MendingRefrainPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:455`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeroicRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:464`` -- transcribed from GwAu3's own body."""

    if Anti_EchoRefrain():
        return False
    return True


def BestTarget_HeroicRefrain(a_f_AggroRange) -> Any:
    """``UtilityAI_EchoRefrain.au3:469`` -- transcribed from GwAu3's own body."""

    if Attribute_GetPartyAttributeInfo(_constants.GC_I_ATTRIBUTE_LEADERSHIP, 0, "CurrentLevel") < 20:
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    l_ai_PartyArray = Party_GetMembersArray()
    for i in range(1,  + 1):
        if UAI_AgentHasEffect(l_ai_PartyArray[i], _constants.GC_I_SKILL_ID_HEROIC_REFRAIN):
            continue
        return l_ai_PartyArray[i]

    return 0


__all__ = [
    "BestTarget_AggressiveRefrain",
    "BestTarget_BladeturnRefrain",
    "BestTarget_BladeturnRefrainPvP",
    "BestTarget_BlazingFinale",
    "BestTarget_BlazingFinalePvP",
    "BestTarget_BurningRefrain",
    "BestTarget_EnduringHarmony",
    "BestTarget_EnergizingFinale",
    "BestTarget_FinaleOfRestoration",
    "BestTarget_FinaleOfRestorationPvP",
    "BestTarget_HastyRefrain",
    "BestTarget_HeroicRefrain",
    "BestTarget_MendingRefrain",
    "BestTarget_MendingRefrainPvP",
    "BestTarget_PurifyingFinale",
    "BestTarget_SoldiersFury",
    "CanUse_AggressiveRefrain",
    "CanUse_BladeturnRefrain",
    "CanUse_BladeturnRefrainPvP",
    "CanUse_BlazingFinale",
    "CanUse_BlazingFinalePvP",
    "CanUse_BurningRefrain",
    "CanUse_EnduringHarmony",
    "CanUse_EnergizingFinale",
    "CanUse_FinaleOfRestoration",
    "CanUse_FinaleOfRestorationPvP",
    "CanUse_HastyRefrain",
    "CanUse_HeroicRefrain",
    "CanUse_MendingRefrain",
    "CanUse_MendingRefrainPvP",
    "CanUse_PurifyingFinale",
    "CanUse_SoldiersFury",
]
