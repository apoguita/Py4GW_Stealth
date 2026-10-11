"""GwAu3's ``UtilityAI_WeaponSpell.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **50 of this file's 50 are transcribed and 0
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
from .uai_agent import (
    UAI_GetAgentInfo,
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_filter import UAI_Filter_IsLivingAlly
from .uai_get_agent import (
    UAI_CountAgents,
    _cached_distance,
    _cached_ids,
)


def CanUse_ResilientWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:29`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_ResilientWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:34`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsHexed) and not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsConditioned):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_SplinterWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:65`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_SplinterWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:70`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 2:
            return l_i_BestAlly
        return 0


def CanUse_WeaponOfWarding() -> Any:
    """``UtilityAI_WeaponSpell.au3:100`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfWarding(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:105`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount == 0:
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_WailingWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:136`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WailingWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:141`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_NightmreWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:171`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_NightmareWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:176`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_VengefulWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:205`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_VengefulWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:210`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount == 0:
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_WeaponOfShadow() -> Any:
    """``UtilityAI_WeaponSpell.au3:241`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfShadow(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:246`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_SpiritLightWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:275`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_SpiritLightWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:280`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_BrutalWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:308`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_BrutalWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:313`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        if UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsEnchanted):
            continue
        return l_i_AgentID

    return 0


def CanUse_GuidedWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:336`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_GuidedWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:341`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_VitalWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:363`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_VitalWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:368`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_WeaponOfQuickening() -> Any:
    """``UtilityAI_WeaponSpell.au3:396`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfQuickening(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:401`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsCasting):
            continue
        return l_i_AgentID

    return 0


def CanUse_WeaponOfFury() -> Any:
    """``UtilityAI_WeaponSpell.au3:423`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfFury(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:428`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_XinraesWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:450`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_XinraesWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:455`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount == 0:
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_WarmongersWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:486`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WarmongersWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:491`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestCasterCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_i_CasterCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemyCaster")
        if l_i_CasterCount > l_i_BestCasterCount:
            l_i_BestCasterCount = l_i_CasterCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestCasterCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_WeaponOfRemedy() -> Any:
    """``UtilityAI_WeaponSpell.au3:521`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfRemedy(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:526`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsConditioned):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount == 0:
            continue
        return l_i_AgentID

    return 0


def CanUse_WeaponOfMastery() -> Any:
    """``UtilityAI_WeaponSpell.au3:551`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfMastery(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:556`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_WeaponOfAggression() -> Any:
    """``UtilityAI_WeaponSpell.au3:578`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsWeaponSpelled):
        return False
    return True


def BestTarget_WeaponOfAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:584`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SunderingWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:593`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_SunderingWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:598`` -- transcribed from GwAu3's own body."""

    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_WeaponOfRenewal() -> Any:
    """``UtilityAI_WeaponSpell.au3:620`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:625`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestEnergy = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_f_Energy = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_CurrentEnergy)
        if l_f_Energy < l_f_LowestEnergy:
            l_f_LowestEnergy = l_f_Energy
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_GhostlyWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:654`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_GhostlyWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:659`` -- transcribed from GwAu3's own body."""

    l_i_PlayerID = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if l_i_AgentID == l_i_PlayerID:
            continue
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_GreatDwarfWeapon() -> Any:
    """``UtilityAI_WeaponSpell.au3:684`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_GreatDwarfWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:689`` -- transcribed from GwAu3's own body."""

    l_i_PlayerID = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if l_i_AgentID == l_i_PlayerID:
            continue
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        return l_i_AgentID

    return 0


def CanUse_SplinterWeaponPvP() -> Any:
    """``UtilityAI_WeaponSpell.au3:714`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_SplinterWeaponPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:719`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        if not UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_IsAttacking):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 2:
            return l_i_BestAlly
        return 0


def CanUse_WeaponOfWardingPvP() -> Any:
    """``UtilityAI_WeaponSpell.au3:749`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponOfWardingPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:754`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_f_LowestHP = 1.0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if UAI_GetAgentInfoByID(l_i_AgentID, _constants.GC_UAI_AGENT_IsWeaponSpelled):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount == 0:
            continue
        l_f_HP = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_HP)
        if l_f_HP < l_f_LowestHP:
            l_f_LowestHP = l_f_HP
            l_i_BestAlly = l_i_AgentID


        return l_i_BestAlly


def CanUse_WeaponsOfThreeForges() -> Any:
    """``UtilityAI_WeaponSpell.au3:785`` -- transcribed from GwAu3's own body."""

    if Anti_WeaponSpell():
        return False
    return True


def BestTarget_WeaponsOfThreeForges(a_f_AggroRange) -> Any:
    """``UtilityAI_WeaponSpell.au3:790`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_BrutalWeapon",
    "BestTarget_GhostlyWeapon",
    "BestTarget_GreatDwarfWeapon",
    "BestTarget_GuidedWeapon",
    "BestTarget_NightmareWeapon",
    "BestTarget_ResilientWeapon",
    "BestTarget_SpiritLightWeapon",
    "BestTarget_SplinterWeapon",
    "BestTarget_SplinterWeaponPvP",
    "BestTarget_SunderingWeapon",
    "BestTarget_VengefulWeapon",
    "BestTarget_VitalWeapon",
    "BestTarget_WailingWeapon",
    "BestTarget_WarmongersWeapon",
    "BestTarget_WeaponOfAggression",
    "BestTarget_WeaponOfFury",
    "BestTarget_WeaponOfMastery",
    "BestTarget_WeaponOfQuickening",
    "BestTarget_WeaponOfRemedy",
    "BestTarget_WeaponOfRenewal",
    "BestTarget_WeaponOfShadow",
    "BestTarget_WeaponOfWarding",
    "BestTarget_WeaponOfWardingPvP",
    "BestTarget_WeaponsOfThreeForges",
    "BestTarget_XinraesWeapon",
    "CanUse_BrutalWeapon",
    "CanUse_GhostlyWeapon",
    "CanUse_GreatDwarfWeapon",
    "CanUse_GuidedWeapon",
    "CanUse_NightmreWeapon",
    "CanUse_ResilientWeapon",
    "CanUse_SpiritLightWeapon",
    "CanUse_SplinterWeapon",
    "CanUse_SplinterWeaponPvP",
    "CanUse_SunderingWeapon",
    "CanUse_VengefulWeapon",
    "CanUse_VitalWeapon",
    "CanUse_WailingWeapon",
    "CanUse_WarmongersWeapon",
    "CanUse_WeaponOfAggression",
    "CanUse_WeaponOfFury",
    "CanUse_WeaponOfMastery",
    "CanUse_WeaponOfQuickening",
    "CanUse_WeaponOfRemedy",
    "CanUse_WeaponOfRenewal",
    "CanUse_WeaponOfShadow",
    "CanUse_WeaponOfWarding",
    "CanUse_WeaponOfWardingPvP",
    "CanUse_WeaponsOfThreeForges",
    "CanUse_XinraesWeapon",
]
