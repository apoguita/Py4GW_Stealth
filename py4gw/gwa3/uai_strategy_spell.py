"""GwAu3's ``UtilityAI_Spell.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **1118 of this file's 1118 are transcribed and 0
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
from .data_skill import Skill_GetSkillInfo
from .uai_agent import (
    UAI_GetAgentInfo,
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_effects import UAI_PlayerHasEffect
from .uai_filter import UAI_Filter_IsLivingEnemy
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_FindAgentByPlayerNumber,
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestAOETarget,
    UAI_GetBestCorpseForEnemyPressure,
    UAI_GetBestSingleTarget,
    UAI_GetNearestAgent,
    _cached_distance,
    _cached_ids,
)


def CanUse_PowerBlock() -> Any:
    """``UtilityAI_Spell.au3:32`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GUILT):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return False
    if not UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_IsCasting):
        return False
    return True


def BestTarget_PowerBlock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:40`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_InspiredEnchantment() -> Any:
    """``UtilityAI_Spell.au3:52`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_InspiredEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:57`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_InspiredHex() -> Any:
    """``UtilityAI_Spell.au3:66`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_InspiredHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:71`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_PowerSpike() -> Any:
    """``UtilityAI_Spell.au3:81`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PowerSpike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:86`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_PowerLeak() -> Any:
    """``UtilityAI_Spell.au3:96`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PowerLeak(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:101`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_PowerDrain() -> Any:
    """``UtilityAI_Spell.au3:111`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    lSkillID = UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_Skill)
    lRuptable = [_constants.GC_I_SKILL_TYPE_HEX, _constants.GC_I_SKILL_TYPE_SPELL, _constants.GC_I_SKILL_TYPE_ENCHANTMENT, _constants.GC_I_SKILL_TYPE_WELL, _constants.GC_I_SKILL_TYPE_WARD, _constants.GC_I_SKILL_TYPE_ITEM_SPELL, _constants.GC_I_SKILL_TYPE_WEAPON_SPELL, _constants.GC_I_SKILL_TYPE_CHANT]
    for i in range(0,  + 1):
        if Skill_GetSkillInfo(lSkillID, "SkillType") == i:
            return True

    return False


def BestTarget_PowerDrain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:125`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster|UAI_Filter_IsCasting")


def CanUse_ShatterDelusions() -> Any:
    """``UtilityAI_Spell.au3:134`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShatterDelusions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:139`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")


def CanUse_EnergySurge() -> Any:
    """``UtilityAI_Spell.au3:149`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergySurge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:154`` -- transcribed from GwAu3's own body."""

    l_i_BestAgent = 0
    l_i_BestCount = 0
    l_i_BestCasterCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if not UAI_Filter_IsLivingEnemy(l_i_AgentID):
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")
        l_i_CasterCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
        if l_i_EnemyCount > l_i_BestCount:
            l_i_BestCount = l_i_EnemyCount
            l_i_BestCasterCount = l_i_CasterCount
            l_i_BestAgent = l_i_AgentID
        elif l_i_EnemyCount == l_i_BestCount and l_i_CasterCount > l_i_BestCasterCount:
            l_i_BestCasterCount = l_i_CasterCount
            l_i_BestAgent = l_i_AgentID


        return l_i_BestAgent


def CanUse_EtherFeast() -> Any:
    """``UtilityAI_Spell.au3:197`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.7:
        return False
    return True


def BestTarget_EtherFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:204`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyBurn() -> Any:
    """``UtilityAI_Spell.au3:215`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergyBurn(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:220`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_CryOfFrustration() -> Any:
    """``UtilityAI_Spell.au3:232`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CryOfFrustration(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:237`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Mimic() -> Any:
    """``UtilityAI_Spell.au3:247`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Mimic(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:252`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArcaneMimicry() -> Any:
    """``UtilityAI_Spell.au3:262`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArcaneMimicry(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:267`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShatterHex() -> Any:
    """``UtilityAI_Spell.au3:277`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShatterHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:282`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_DrainEnchantment() -> Any:
    """``UtilityAI_Spell.au3:292`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    return True


def BestTarget_DrainEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:298`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_ShatterEnchantment() -> Any:
    """``UtilityAI_Spell.au3:307`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShatterEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:312`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_ChaosStorm() -> Any:
    """``UtilityAI_Spell.au3:322`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ChaosStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:327`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Epidemic() -> Any:
    """``UtilityAI_Spell.au3:336`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Epidemic(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:341`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyDrain() -> Any:
    """``UtilityAI_Spell.au3:353`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    return True


def BestTarget_EnergyDrain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:359`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMonk")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyTap() -> Any:
    """``UtilityAI_Spell.au3:378`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    return True


def BestTarget_EnergyTap(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:384`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMonk")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ArcaneThievery() -> Any:
    """``UtilityAI_Spell.au3:403`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArcaneThievery(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:408`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnimateBoneHorror() -> Any:
    """``UtilityAI_Spell.au3:420`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateBoneHorror(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:425`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnimateBoneFiend() -> Any:
    """``UtilityAI_Spell.au3:434`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateBoneFiend(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:439`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnimateBoneMinions() -> Any:
    """``UtilityAI_Spell.au3:448`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateBoneMinions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:453`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GrenthsBalance() -> Any:
    """``UtilityAI_Spell.au3:462`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GrenthsBalance(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:467`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VeratasGaze() -> Any:
    """``UtilityAI_Spell.au3:473`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VeratasGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:478`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DeathlyChill() -> Any:
    """``UtilityAI_Spell.au3:484`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DeathlyChill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:489`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_VeratasSacrifice() -> Any:
    """``UtilityAI_Spell.au3:499`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VeratasSacrifice(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:504`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PutridExplosion() -> Any:
    """``UtilityAI_Spell.au3:509`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PutridExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:514`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_SoulFeast() -> Any:
    """``UtilityAI_Spell.au3:523`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SoulFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:528`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NecroticTraversal() -> Any:
    """``UtilityAI_Spell.au3:537`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NecroticTraversal(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:542`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConsumeCorpse() -> Any:
    """``UtilityAI_Spell.au3:551`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ConsumeCorpse(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:556`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowStrike() -> Any:
    """``UtilityAI_Spell.au3:565`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShadowStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:570`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DeathlySwarm() -> Any:
    """``UtilityAI_Spell.au3:580`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DeathlySwarm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:585`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_RottingFlesh() -> Any:
    """``UtilityAI_Spell.au3:594`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RottingFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:599`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Virulence() -> Any:
    """``UtilityAI_Spell.au3:609`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Virulence(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:614`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")


def CanUse_UnholyFeast() -> Any:
    """``UtilityAI_Spell.au3:624`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UnholyFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:629`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DesecrateEnchantments() -> Any:
    """``UtilityAI_Spell.au3:638`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DesecrateEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:643`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Enfeeble1() -> Any:
    """``UtilityAI_Spell.au3:655`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Enfeeble1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:660`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnfeeblingBlood() -> Any:
    """``UtilityAI_Spell.au3:666`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnfeeblingBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:671`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_BloodOfTheMaster() -> Any:
    """``UtilityAI_Spell.au3:681`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BloodOfTheMaster(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:686`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkPact() -> Any:
    """``UtilityAI_Spell.au3:695`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DarkPact(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:700`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RendEnchantments() -> Any:
    """``UtilityAI_Spell.au3:706`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RendEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:711`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_StripEnchantment() -> Any:
    """``UtilityAI_Spell.au3:721`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StripEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:726`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_Chilblains() -> Any:
    """``UtilityAI_Spell.au3:735`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Chilblains(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:740`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_OfferingOfBlood() -> Any:
    """``UtilityAI_Spell.au3:752`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OfferingOfBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:757`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PlagueSending() -> Any:
    """``UtilityAI_Spell.au3:766`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PlagueSending(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:771`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FeastOfCorruption() -> Any:
    """``UtilityAI_Spell.au3:781`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FeastOfCorruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:786`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_TasteOfDeath() -> Any:
    """``UtilityAI_Spell.au3:798`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TasteOfDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:803`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VampiricGaze() -> Any:
    """``UtilityAI_Spell.au3:813`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VampiricGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:818`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WeakenArmor() -> Any:
    """``UtilityAI_Spell.au3:827`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WeakenArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:832`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningStorm() -> Any:
    """``UtilityAI_Spell.au3:842`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:847`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Gale() -> Any:
    """``UtilityAI_Spell.au3:857`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Gale(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:862`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Whirlwind() -> Any:
    """``UtilityAI_Spell.au3:872`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Whirlwind(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:877`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Eruption() -> Any:
    """``UtilityAI_Spell.au3:886`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Eruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:891`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Earthquake() -> Any:
    """``UtilityAI_Spell.au3:901`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Earthquake(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:906`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Stoning() -> Any:
    """``UtilityAI_Spell.au3:916`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Stoning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:921`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StoneDaggers() -> Any:
    """``UtilityAI_Spell.au3:933`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StoneDaggers(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:938`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Aftershock() -> Any:
    """``UtilityAI_Spell.au3:948`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Aftershock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:953`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Inferno() -> Any:
    """``UtilityAI_Spell.au3:962`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Inferno(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:967`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MindBurn() -> Any:
    """``UtilityAI_Spell.au3:976`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MindBurn(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:981`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Fireball() -> Any:
    """``UtilityAI_Spell.au3:991`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Fireball(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:996`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Meteor() -> Any:
    """``UtilityAI_Spell.au3:1006`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Meteor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1011`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FlameBurst() -> Any:
    """``UtilityAI_Spell.au3:1021`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FlameBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1026`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RodgortsInvocation() -> Any:
    """``UtilityAI_Spell.au3:1035`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RodgortsInvocation(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1040`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Immolate() -> Any:
    """``UtilityAI_Spell.au3:1046`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Immolate(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1051`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MeteorShower() -> Any:
    """``UtilityAI_Spell.au3:1061`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MeteorShower(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1066`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_Phoenix() -> Any:
    """``UtilityAI_Spell.au3:1075`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Phoenix(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1080`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Flare() -> Any:
    """``UtilityAI_Spell.au3:1090`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Flare(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1095`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_LavaFont() -> Any:
    """``UtilityAI_Spell.au3:1104`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LavaFont(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1109`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SearingHeat() -> Any:
    """``UtilityAI_Spell.au3:1118`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SearingHeat(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1123`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_FireStorm() -> Any:
    """``UtilityAI_Spell.au3:1132`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1137`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_Maelstrom() -> Any:
    """``UtilityAI_Spell.au3:1146`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Maelstrom(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1151`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_CrystalWave() -> Any:
    """``UtilityAI_Spell.au3:1162`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CrystalWave(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1167`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ObsidianFlame() -> Any:
    """``UtilityAI_Spell.au3:1176`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ObsidianFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1181`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_BlindingFlash() -> Any:
    """``UtilityAI_Spell.au3:1191`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlindingFlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1196`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ChainLightning() -> Any:
    """``UtilityAI_Spell.au3:1208`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ChainLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1213`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_EnervatingCharge() -> Any:
    """``UtilityAI_Spell.au3:1223`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnervatingCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1228`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MindShock() -> Any:
    """``UtilityAI_Spell.au3:1238`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MindShock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1243`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Thunderclap() -> Any:
    """``UtilityAI_Spell.au3:1253`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Thunderclap(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1258`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningOrb1() -> Any:
    """``UtilityAI_Spell.au3:1268`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningOrb1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1273`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningJavelin() -> Any:
    """``UtilityAI_Spell.au3:1279`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningJavelin(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1284`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WaterTrident() -> Any:
    """``UtilityAI_Spell.au3:1296`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WaterTrident(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1301`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Smite() -> Any:
    """``UtilityAI_Spell.au3:1311`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Smite(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1316`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_SymbolOfWrath() -> Any:
    """``UtilityAI_Spell.au3:1325`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SymbolOfWrath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1330`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Banish() -> Any:
    """``UtilityAI_Spell.au3:1339`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Banish(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1344`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMinion")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsSpirit")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MendCondition() -> Any:
    """``UtilityAI_Spell.au3:1358`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendCondition(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1363`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_RestoreCondition() -> Any:
    """``UtilityAI_Spell.au3:1375`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RestoreCondition(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1380`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_MendAilment() -> Any:
    """``UtilityAI_Spell.au3:1392`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendAilment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1397`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")


def CanUse_PurgeConditions() -> Any:
    """``UtilityAI_Spell.au3:1407`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PurgeConditions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1412`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")


def CanUse_DivineHealing() -> Any:
    """``UtilityAI_Spell.au3:1422`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DivineHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1427`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealArea() -> Any:
    """``UtilityAI_Spell.au3:1436`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealArea(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1441`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrisonOfHealing() -> Any:
    """``UtilityAI_Spell.au3:1450`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) > 0.8:
        return False
    return True


def BestTarget_OrisonOfHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1456`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_WordOfHealing() -> Any:
    """``UtilityAI_Spell.au3:1465`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WordOfHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1470`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_DwaynasKiss() -> Any:
    """``UtilityAI_Spell.au3:1487`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) > 0.8:
        return False
    return True


def BestTarget_DwaynasKiss(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1493`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsEnchanted|UAI_Filter_IsHexed")
    if UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.8 and l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsHexed")
    if UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.8 and l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsEnchanted")
    if UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.8 and l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.5 and l_i_Target != 0:
        return l_i_Target
    return l_i_Target


def CanUse_HealOther() -> Any:
    """``UtilityAI_Spell.au3:1510`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealOther(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1515`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_HealParty() -> Any:
    """``UtilityAI_Spell.au3:1525`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealParty(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1530`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InfuseHealth() -> Any:
    """``UtilityAI_Spell.au3:1539`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_InfuseHealth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1544`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.1:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_Martyr() -> Any:
    """``UtilityAI_Spell.au3:1558`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Martyr(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1563`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveHex() -> Any:
    """``UtilityAI_Spell.au3:1572`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RemoveHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1577`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")


def CanUse_SmiteHex() -> Any:
    """``UtilityAI_Spell.au3:1586`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_CountAgents(uai_const.g_i_BestTarget, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy") < 1:
        return False
    return True


def BestTarget_SmiteHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1592`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")


def CanUse_ConvertHexes() -> Any:
    """``UtilityAI_Spell.au3:1601`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ConvertHexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1606`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_LightOfDwayna() -> Any:
    """``UtilityAI_Spell.au3:1618`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_LightOfDwayna(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1624`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Resurrect() -> Any:
    """``UtilityAI_Spell.au3:1633`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_Resurrect(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1639`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_Rebirth() -> Any:
    """``UtilityAI_Spell.au3:1649`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_Rebirth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1655`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_DrawConditions() -> Any:
    """``UtilityAI_Spell.au3:1665`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DrawConditions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1670`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe|UAI_Filter_IsConditioned")


def CanUse_HealingTouch() -> Any:
    """``UtilityAI_Spell.au3:1680`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1685`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_RestoreLife() -> Any:
    """``UtilityAI_Spell.au3:1695`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_RestoreLife(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1701`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_EruptionEnvironment() -> Any:
    """``UtilityAI_Spell.au3:1711`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EruptionEnvironment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1716`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireStormEnvironment() -> Any:
    """``UtilityAI_Spell.au3:1721`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireStormEnvironment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1726`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FountOfMaguuma() -> Any:
    """``UtilityAI_Spell.au3:1731`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FountOfMaguuma(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1736`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingFountain() -> Any:
    """``UtilityAI_Spell.au3:1745`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingFountain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1750`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IcyGround() -> Any:
    """``UtilityAI_Spell.au3:1759`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_IcyGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1764`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MaelstromEnvironment() -> Any:
    """``UtilityAI_Spell.au3:1773`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MaelstromEnvironment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1778`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MursaatTowerSkill() -> Any:
    """``UtilityAI_Spell.au3:1783`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MursaatTowerSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1788`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_QuicksandEnvironmentEffect() -> Any:
    """``UtilityAI_Spell.au3:1794`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_QuicksandEnvironmentEffect(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1799`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CurseOfTheBloodstone() -> Any:
    """``UtilityAI_Spell.au3:1804`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CurseOfTheBloodstone(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1809`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChainLightningEnvironment() -> Any:
    """``UtilityAI_Spell.au3:1818`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ChainLightningEnvironment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1823`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ObeliskLightning() -> Any:
    """``UtilityAI_Spell.au3:1828`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ObeliskLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1833`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Tar() -> Any:
    """``UtilityAI_Spell.au3:1842`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Tar(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1847`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Nibble() -> Any:
    """``UtilityAI_Spell.au3:1856`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Nibble(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1861`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GuardianPacify() -> Any:
    """``UtilityAI_Spell.au3:1870`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GuardianPacify(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1875`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoulVortex() -> Any:
    """``UtilityAI_Spell.au3:1884`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SoulVortex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1889`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ResurrectGargoyle() -> Any:
    """``UtilityAI_Spell.au3:1899`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ResurrectGargoyle(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1904`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LightningOrb2() -> Any:
    """``UtilityAI_Spell.au3:1910`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningOrb2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1915`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WurmSiegeDunesOfDespair() -> Any:
    """``UtilityAI_Spell.au3:1921`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WurmSiegeDunesOfDespair(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1926`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_WurmSiege() -> Any:
    """``UtilityAI_Spell.au3:1932`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WurmSiege(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1937`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ShiverTouch() -> Any:
    """``UtilityAI_Spell.au3:1943`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShiverTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1948`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Vanish() -> Any:
    """``UtilityAI_Spell.au3:1958`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Vanish(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1963`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisruptingDagger() -> Any:
    """``UtilityAI_Spell.au3:1972`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DisruptingDagger(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1977`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StatuesBlessing() -> Any:
    """``UtilityAI_Spell.au3:1989`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StatuesBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:1994`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DomainOfSkillDamage() -> Any:
    """``UtilityAI_Spell.au3:2000`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DomainOfSkillDamage(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2005`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DomainOfEnergyDraining() -> Any:
    """``UtilityAI_Spell.au3:2014`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DomainOfEnergyDraining(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2019`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DomainOfElements() -> Any:
    """``UtilityAI_Spell.au3:2028`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DomainOfElements(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2033`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DomainOfHealthDraining() -> Any:
    """``UtilityAI_Spell.au3:2042`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DomainOfHealthDraining(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2047`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DomainOfSlow() -> Any:
    """``UtilityAI_Spell.au3:2056`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DomainOfSlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2061`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SwampWater() -> Any:
    """``UtilityAI_Spell.au3:2070`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SwampWater(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2075`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JanthirsGaze() -> Any:
    """``UtilityAI_Spell.au3:2084`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_JanthirsGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2089`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FakeSpell() -> Any:
    """``UtilityAI_Spell.au3:2094`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FakeSpell(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2099`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StormcallerSkill() -> Any:
    """``UtilityAI_Spell.au3:2108`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StormcallerSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2113`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QuestSkill() -> Any:
    """``UtilityAI_Spell.au3:2118`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_QuestSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2123`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RurikMustLive() -> Any:
    """``UtilityAI_Spell.au3:2132`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RurikMustLive(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2137`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GazeOfContempt() -> Any:
    """``UtilityAI_Spell.au3:2146`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GazeOfContempt(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2151`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_VipersDefense() -> Any:
    """``UtilityAI_Spell.au3:2160`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VipersDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2165`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Return() -> Any:
    """``UtilityAI_Spell.au3:2171`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Return(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2176`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_ExcludeMe")


def CanUse_EntanglingAsp() -> Any:
    """``UtilityAI_Spell.au3:2185`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EntanglingAsp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2190`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_FleshOfMyFlesh() -> Any:
    """``UtilityAI_Spell.au3:2199`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_FleshOfMyFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2205`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_SorrowsFlame() -> Any:
    """``UtilityAI_Spell.au3:2214`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SorrowsFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2219`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SorrowsFist() -> Any:
    """``UtilityAI_Spell.au3:2224`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SorrowsFist(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2229`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlastFurnace() -> Any:
    """``UtilityAI_Spell.au3:2234`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlastFurnace(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BeguilingHaze() -> Any:
    """``UtilityAI_Spell.au3:2248`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BeguilingHaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2253`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnimateVampiricHorror() -> Any:
    """``UtilityAI_Spell.au3:2262`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateVampiricHorror(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2267`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Discord() -> Any:
    """``UtilityAI_Spell.au3:2276`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Discord(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2281`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexedOrEnchanted|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LavaArrows() -> Any:
    """``UtilityAI_Spell.au3:2292`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LavaArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2297`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_BedOfCoals() -> Any:
    """``UtilityAI_Spell.au3:2306`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BedOfCoals(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2311`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_RayOfJudgment() -> Any:
    """``UtilityAI_Spell.au3:2320`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RayOfJudgment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2325`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_AnimateFleshGolem() -> Any:
    """``UtilityAI_Spell.au3:2334`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateFleshGolem(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2339`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RideTheLightning() -> Any:
    """``UtilityAI_Spell.au3:2348`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RideTheLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2353`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PoisonedHeart() -> Any:
    """``UtilityAI_Spell.au3:2362`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonedHeart(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2367`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FetidGround() -> Any:
    """``UtilityAI_Spell.au3:2376`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FetidGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2381`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ArcLightning() -> Any:
    """``UtilityAI_Spell.au3:2390`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArcLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2395`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ChurningEarth() -> Any:
    """``UtilityAI_Spell.au3:2404`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ChurningEarth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2409`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LiquidFlame() -> Any:
    """``UtilityAI_Spell.au3:2418`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LiquidFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2423`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Steam1() -> Any:
    """``UtilityAI_Spell.au3:2432`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Steam1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2437`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Chomper() -> Any:
    """``UtilityAI_Spell.au3:2443`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Chomper(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2448`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DancingDaggers() -> Any:
    """``UtilityAI_Spell.au3:2457`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DancingDaggers(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2462`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RavenousGaze() -> Any:
    """``UtilityAI_Spell.au3:2471`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RavenousGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2476`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_OppressiveGaze() -> Any:
    """``UtilityAI_Spell.au3:2485`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OppressiveGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2490`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningHammer() -> Any:
    """``UtilityAI_Spell.au3:2499`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningHammer(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2504`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VaporBlade() -> Any:
    """``UtilityAI_Spell.au3:2513`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VaporBlade(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2518`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HealingLight() -> Any:
    """``UtilityAI_Spell.au3:2527`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2532`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsEnchanted")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.9:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.8:
        return l_i_Target
    return l_i_Target


def CanUse_LyssasBalance() -> Any:
    """``UtilityAI_Spell.au3:2547`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LyssasBalance(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2552`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SearingFlames1() -> Any:
    """``UtilityAI_Spell.au3:2558`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SearingFlames1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2563`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_OathOfHealing() -> Any:
    """``UtilityAI_Spell.au3:2569`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OathOfHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2574`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodOfTheAggressor() -> Any:
    """``UtilityAI_Spell.au3:2583`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BloodOfTheAggressor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2588`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IcyPrism() -> Any:
    """``UtilityAI_Spell.au3:2597`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_IcyPrism(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2602`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritRift() -> Any:
    """``UtilityAI_Spell.au3:2611`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritRift(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2616`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ConsumeSoul() -> Any:
    """``UtilityAI_Spell.au3:2625`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ConsumeSoul(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2630`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritLight() -> Any:
    """``UtilityAI_Spell.au3:2639`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    l_i_SpiritCount = UAI_CountAgents(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsSpirit")
    l_i_HP = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP)
    if l_i_SpiritCount <= 0 and l_i_HP < 0.85:
        return False
    return True


def BestTarget_SpiritLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2647`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.85:
        return l_i_Target


def CanUse_RuptureSoul() -> Any:
    """``UtilityAI_Spell.au3:2657`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RuptureSoul(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2662`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsSpirit")


def CanUse_SpiritToFlesh() -> Any:
    """``UtilityAI_Spell.au3:2671`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritToFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2676`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_SpiritBurn() -> Any:
    """``UtilityAI_Spell.au3:2682`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritBurn(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2687`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PowerReturn() -> Any:
    """``UtilityAI_Spell.au3:2696`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PowerReturn(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2701`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_Complicate() -> Any:
    """``UtilityAI_Spell.au3:2710`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Complicate(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2715`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ShatterStorm() -> Any:
    """``UtilityAI_Spell.au3:2724`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShatterStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2729`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_EnvenomEnchantments() -> Any:
    """``UtilityAI_Spell.au3:2738`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnvenomEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2743`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_Shockwave() -> Any:
    """``UtilityAI_Spell.au3:2752`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Shockwave(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2757`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CryOfLament() -> Any:
    """``UtilityAI_Spell.au3:2766`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CryOfLament(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2771`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlessedLight() -> Any:
    """``UtilityAI_Spell.au3:2780`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlessedLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2785`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.9:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.9:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.7:
        return l_i_Target
    return l_i_Target


def CanUse_WithdrawHexes() -> Any:
    """``UtilityAI_Spell.au3:2806`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WithdrawHexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2811`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_Extinguish() -> Any:
    """``UtilityAI_Spell.au3:2820`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Extinguish(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2825`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathsCharge() -> Any:
    """``UtilityAI_Spell.au3:2834`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DeathsCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2839`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_AgentHasMoreHpThanMe")


def CanUse_ExpelHexes() -> Any:
    """``UtilityAI_Spell.au3:2848`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ExpelHexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2853`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_RipEnchantment() -> Any:
    """``UtilityAI_Spell.au3:2862`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RipEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2867`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_HealingWhisper() -> Any:
    """``UtilityAI_Spell.au3:2876`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingWhisper(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2881`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_EtherealLight() -> Any:
    """``UtilityAI_Spell.au3:2890`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EtherealLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2895`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_ReleaseEnchantments() -> Any:
    """``UtilityAI_Spell.au3:2904`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReleaseEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2909`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritTransfer() -> Any:
    """``UtilityAI_Spell.au3:2918`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    l_i_SpiritCount = UAI_CountAgents(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsSpirit")
    if l_i_SpiritCount <= 0:
        return False
    return True


def BestTarget_SpiritTransfer(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2926`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.5:
        return l_i_Target
    return l_i_Target


def CanUse_ArchemorusStrike() -> Any:
    """``UtilityAI_Spell.au3:2938`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArchemorusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2943`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpearOfArchemorusLevel1() -> Any:
    """``UtilityAI_Spell.au3:2948`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfArchemorusLevel1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2953`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpearOfArchemorusLevel2() -> Any:
    """``UtilityAI_Spell.au3:2958`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfArchemorusLevel2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2963`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpearOfArchemorusLevel3() -> Any:
    """``UtilityAI_Spell.au3:2968`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfArchemorusLevel3(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2973`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpearOfArchemorusLevel4() -> Any:
    """``UtilityAI_Spell.au3:2978`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfArchemorusLevel4(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2983`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpearOfArchemorusLevel5() -> Any:
    """``UtilityAI_Spell.au3:2988`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfArchemorusLevel5(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:2993`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArgosCry() -> Any:
    """``UtilityAI_Spell.au3:2998`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArgosCry(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3003`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JadeFury() -> Any:
    """``UtilityAI_Spell.au3:3009`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_JadeFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3014`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlindingPowder() -> Any:
    """``UtilityAI_Spell.au3:3023`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlindingPowder(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3028`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_MantisTouch() -> Any:
    """``UtilityAI_Spell.au3:3037`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MantisTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3042`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FeastOfSouls() -> Any:
    """``UtilityAI_Spell.au3:3051`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FeastOfSouls(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3056`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Caltrops() -> Any:
    """``UtilityAI_Spell.au3:3065`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Caltrops(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3070`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_DenyHexes() -> Any:
    """``UtilityAI_Spell.au3:3079`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DenyHexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3084`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_BlindingSnow() -> Any:
    """``UtilityAI_Spell.au3:3093`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlindingSnow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3098`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AvalancheSkill() -> Any:
    """``UtilityAI_Spell.au3:3107`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AvalancheSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3112`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Snowball() -> Any:
    """``UtilityAI_Spell.au3:3118`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Snowball(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3123`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MegaSnowball() -> Any:
    """``UtilityAI_Spell.au3:3132`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MegaSnowball(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3137`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HolidayBlues() -> Any:
    """``UtilityAI_Spell.au3:3146`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HolidayBlues(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3151`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlurryOfIce() -> Any:
    """``UtilityAI_Spell.au3:3160`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FlurryOfIce(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3165`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SnowballNpc() -> Any:
    """``UtilityAI_Spell.au3:3174`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SnowballNpc(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3179`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HeartOfShadow() -> Any:
    """``UtilityAI_Spell.au3:3185`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.9:
        return False
    return True


def BestTarget_HeartOfShadow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3191`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CripplingDagger() -> Any:
    """``UtilityAI_Spell.au3:3200`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CripplingDagger(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3205`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritWalk() -> Any:
    """``UtilityAI_Spell.au3:3214`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritWalk(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3219`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsSpirit")


def CanUse_RevealedEnchantment() -> Any:
    """``UtilityAI_Spell.au3:3228`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RevealedEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3233`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_RevealedHex() -> Any:
    """``UtilityAI_Spell.au3:3242`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RevealedHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3247`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_AccumulatedPain() -> Any:
    """``UtilityAI_Spell.au3:3256`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AccumulatedPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3261`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        l_i_HexCount = UAI_CountAgents(l_i_Target, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsHex")
        if l_i_HexCount >= 2:
            return l_i_Target

        return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PsychicDistraction() -> Any:
    """``UtilityAI_Spell.au3:3276`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PsychicDistraction(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3281`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_PsychicInstability() -> Any:
    """``UtilityAI_Spell.au3:3291`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PsychicInstability(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3296`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_CelestialHaste() -> Any:
    """``UtilityAI_Spell.au3:3306`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CelestialHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3311`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Feedback() -> Any:
    """``UtilityAI_Spell.au3:3320`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Feedback(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3325`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_ArcaneLarceny() -> Any:
    """``UtilityAI_Spell.au3:3335`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArcaneLarceny(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3340`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LifebaneStrike() -> Any:
    """``UtilityAI_Spell.au3:3352`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LifebaneStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3357`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_BitterChill() -> Any:
    """``UtilityAI_Spell.au3:3367`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BitterChill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3372`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_TasteOfPain() -> Any:
    """``UtilityAI_Spell.au3:3382`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TasteOfPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3387`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DefileEnchantments() -> Any:
    """``UtilityAI_Spell.au3:3397`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DefileEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3402`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_VampiricSwarm() -> Any:
    """``UtilityAI_Spell.au3:3414`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_VampiricSwarm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3419`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_BloodDrinker() -> Any:
    """``UtilityAI_Spell.au3:3429`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BloodDrinker(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3434`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_TeinaisWind() -> Any:
    """``UtilityAI_Spell.au3:3444`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TeinaisWind(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3449`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ShockArrow() -> Any:
    """``UtilityAI_Spell.au3:3455`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShockArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3460`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UnsteadyGround() -> Any:
    """``UtilityAI_Spell.au3:3472`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UnsteadyGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3477`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_DragonsStomp() -> Any:
    """``UtilityAI_Spell.au3:3487`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DragonsStomp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3492`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SecondWind() -> Any:
    """``UtilityAI_Spell.au3:3498`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SecondWind(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3503`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BreathOfFire() -> Any:
    """``UtilityAI_Spell.au3:3512`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BreathOfFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3517`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_StarBurst() -> Any:
    """``UtilityAI_Spell.au3:3526`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StarBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3531`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_TeinaisCrystals() -> Any:
    """``UtilityAI_Spell.au3:3541`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TeinaisCrystals(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3546`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ShieldOfSaintViktor() -> Any:
    """``UtilityAI_Spell.au3:3552`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShieldOfSaintViktor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3557`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrnOfSaintViktorLevel1() -> Any:
    """``UtilityAI_Spell.au3:3566`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UrnOfSaintViktorLevel1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3571`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrnOfSaintViktorLevel2() -> Any:
    """``UtilityAI_Spell.au3:3576`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UrnOfSaintViktorLevel2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3581`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrnOfSaintViktorLevel3() -> Any:
    """``UtilityAI_Spell.au3:3586`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UrnOfSaintViktorLevel3(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3591`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrnOfSaintViktorLevel4() -> Any:
    """``UtilityAI_Spell.au3:3596`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UrnOfSaintViktorLevel4(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3601`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrnOfSaintViktorLevel5() -> Any:
    """``UtilityAI_Spell.au3:3606`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UrnOfSaintViktorLevel5(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3611`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KirinsWrath() -> Any:
    """``UtilityAI_Spell.au3:3616`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_KirinsWrath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3621`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeavensDelight() -> Any:
    """``UtilityAI_Spell.au3:3626`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HeavensDelight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3631`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingBurst() -> Any:
    """``UtilityAI_Spell.au3:3640`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3645`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_KareisHealingCircle() -> Any:
    """``UtilityAI_Spell.au3:3655`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_KareisHealingCircle(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3660`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JameisGaze() -> Any:
    """``UtilityAI_Spell.au3:3665`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_JameisGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3670`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GiftOfHealth() -> Any:
    """``UtilityAI_Spell.au3:3676`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GiftOfHealth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3681`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_EmpathicRemoval() -> Any:
    """``UtilityAI_Spell.au3:3691`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EmpathicRemoval(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3696`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_ResurrectionChant() -> Any:
    """``UtilityAI_Spell.au3:3709`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_ResurrectionChant(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3715`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_WordOfCensure() -> Any:
    """``UtilityAI_Spell.au3:3726`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WordOfCensure(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3731`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearOfLight() -> Any:
    """``UtilityAI_Spell.au3:3741`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpearOfLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3746`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CathedralCollapse2() -> Any:
    """``UtilityAI_Spell.au3:3758`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CathedralCollapse2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3763`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodOfZuHeltzer() -> Any:
    """``UtilityAI_Spell.au3:3768`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BloodOfZuHeltzer(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3773`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CorruptedDragonSpores() -> Any:
    """``UtilityAI_Spell.au3:3782`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CorruptedDragonSpores(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3787`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_CorruptedDragonScales() -> Any:
    """``UtilityAI_Spell.au3:3799`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CorruptedDragonScales(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3804`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_OfRoyalBlood() -> Any:
    """``UtilityAI_Spell.au3:3814`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OfRoyalBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3819`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PassageToTahnnakai() -> Any:
    """``UtilityAI_Spell.au3:3828`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PassageToTahnnakai(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3833`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClamorOfSouls() -> Any:
    """``UtilityAI_Spell.au3:3838`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ClamorOfSouls(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3843`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_DrawSpirit() -> Any:
    """``UtilityAI_Spell.au3:3854`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DrawSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3859`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChanneledStrike() -> Any:
    """``UtilityAI_Spell.au3:3869`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ChanneledStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3874`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritBoonStrike() -> Any:
    """``UtilityAI_Spell.au3:3884`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritBoonStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3889`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EssenceStrike() -> Any:
    """``UtilityAI_Spell.au3:3899`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    return True


def BestTarget_EssenceStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3905`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritSiphon() -> Any:
    """``UtilityAI_Spell.au3:3914`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritSiphon(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3919`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoothingMemories() -> Any:
    """``UtilityAI_Spell.au3:3928`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SoothingMemories(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3933`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_MendBodyAndSoul() -> Any:
    """``UtilityAI_Spell.au3:3943`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendBodyAndSoul(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3948`` -- transcribed from GwAu3's own body."""

    l_i_SpiritCount = UAI_CountAgents(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsSpirit")
    l_i_TargetConditioned = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    l_i_TargetLowest = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_TargetLowest != 0:
        l_f_LowestHP = UAI_GetAgentInfoByID(l_i_TargetLowest, _constants.GC_UAI_AGENT_HP)
        if l_f_LowestHP >= 0.85:
            if l_i_SpiritCount >= 1 and l_i_TargetConditioned != 0:
                return l_i_TargetConditioned
            return 0

            if l_i_SpiritCount >= 1 and l_i_TargetConditioned != 0 and l_i_TargetConditioned != l_i_TargetLowest:
                l_f_ConditionedHP = UAI_GetAgentInfoByID(l_i_TargetConditioned, _constants.GC_UAI_AGENT_HP)
                l_f_HPDelta = 0.10
                if l_f_ConditionedHP <= l_f_LowestHP + l_f_HPDelta:
                    return l_i_TargetConditioned

                return l_i_TargetLowest



def CanUse_ArchemorusStrikeCelestialSummoning() -> Any:
    """``UtilityAI_Spell.au3:3976`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ArchemorusStrikeCelestialSummoning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3981`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldOfSaintViktorCelestialSummoning() -> Any:
    """``UtilityAI_Spell.au3:3986`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShieldOfSaintViktorCelestialSummoning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:3991`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GazeFromBeyond() -> Any:
    """``UtilityAI_Spell.au3:3996`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GazeFromBeyond(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4001`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HealingRing() -> Any:
    """``UtilityAI_Spell.au3:4007`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingRing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4012`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RenewLife() -> Any:
    """``UtilityAI_Spell.au3:4021`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_RenewLife(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4027`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_Doom() -> Any:
    """``UtilityAI_Spell.au3:4037`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Doom(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4042`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WieldersBoon() -> Any:
    """``UtilityAI_Spell.au3:4052`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WieldersBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4057`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BattleCry2() -> Any:
    """``UtilityAI_Spell.au3:4063`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BattleCry2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4068`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalDefenseZone() -> Any:
    """``UtilityAI_Spell.au3:4073`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ElementalDefenseZone(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4078`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MeleeDefenseZone() -> Any:
    """``UtilityAI_Spell.au3:4087`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MeleeDefenseZone(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4092`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TurretArrow() -> Any:
    """``UtilityAI_Spell.au3:4101`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TurretArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4106`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodFlowerSkill() -> Any:
    """``UtilityAI_Spell.au3:4115`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BloodFlowerSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4120`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireFlowerSkill() -> Any:
    """``UtilityAI_Spell.au3:4125`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireFlowerSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4130`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PoisonArrowFlower() -> Any:
    """``UtilityAI_Spell.au3:4135`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonArrowFlower(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4140`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldingUrnSkill() -> Any:
    """``UtilityAI_Spell.au3:4145`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShieldingUrnSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4150`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireballObelisk() -> Any:
    """``UtilityAI_Spell.au3:4155`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireballObelisk(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4160`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExtendConditions() -> Any:
    """``UtilityAI_Spell.au3:4165`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ExtendConditions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4170`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Hypochondria() -> Any:
    """``UtilityAI_Spell.au3:4182`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Hypochondria(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4187`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritualPain() -> Any:
    """``UtilityAI_Spell.au3:4197`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritualPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4202`` -- transcribed from GwAu3's own body."""

    l_i_BestAgent = 0
    l_i_BestSummonCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        if not UAI_Filter_IsLivingEnemy(l_i_AgentID):
            continue
        l_i_SpiritCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsSpirit")
        l_i_MinionCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMinion")
        l_i_SummonCount = l_i_SpiritCount + l_i_MinionCount
        if l_i_SummonCount > l_i_BestSummonCount:
            l_i_BestSummonCount = l_i_SummonCount
            l_i_BestAgent = l_i_AgentID


        if l_i_BestAgent != 0:
            return l_i_BestAgent
        return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DrainDelusions() -> Any:
    """``UtilityAI_Spell.au3:4241`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DrainDelusions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4246`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Tease() -> Any:
    """``UtilityAI_Spell.au3:4258`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Tease(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4263`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_DischargeEnchantment() -> Any:
    """``UtilityAI_Spell.au3:4273`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DischargeEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4278`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_HexEaterVortex() -> Any:
    """``UtilityAI_Spell.au3:4290`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HexEaterVortex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4295`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")


def CanUse_MirrorOfDisenchantment() -> Any:
    """``UtilityAI_Spell.au3:4305`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MirrorOfDisenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4310`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SimpleThievery() -> Any:
    """``UtilityAI_Spell.au3:4322`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SimpleThievery(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4327`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_AnimateShamblingHorror() -> Any:
    """``UtilityAI_Spell.au3:4337`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateShamblingHorror(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4342`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfUndeath() -> Any:
    """``UtilityAI_Spell.au3:4351`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OrderOfUndeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4356`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PutridFlesh() -> Any:
    """``UtilityAI_Spell.au3:4365`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PutridFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4370`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FeastForTheDead() -> Any:
    """``UtilityAI_Spell.au3:4380`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FeastForTheDead(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4385`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PainOfDisenchantment() -> Any:
    """``UtilityAI_Spell.au3:4391`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PainOfDisenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4396`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_BlindingSurge() -> Any:
    """``UtilityAI_Spell.au3:4408`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlindingSurge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4413`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningBolt() -> Any:
    """``UtilityAI_Spell.au3:4423`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningBolt(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4428`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Sandstorm() -> Any:
    """``UtilityAI_Spell.au3:4438`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Sandstorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4443`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_EbonHawk() -> Any:
    """``UtilityAI_Spell.au3:4453`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EbonHawk(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4458`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GlowingGaze1() -> Any:
    """``UtilityAI_Spell.au3:4468`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GlowingGaze1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4473`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SavannahHeat() -> Any:
    """``UtilityAI_Spell.au3:4479`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SavannahHeat(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4484`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_WordsOfComfort() -> Any:
    """``UtilityAI_Spell.au3:4493`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WordsOfComfort(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4498`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_LightOfDeliverance() -> Any:
    """``UtilityAI_Spell.au3:4511`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightOfDeliverance(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4516`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MendingTouch() -> Any:
    """``UtilityAI_Spell.au3:4525`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendingTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4530`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly")


def CanUse_StopPump() -> Any:
    """``UtilityAI_Spell.au3:4542`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StopPump(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4547`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WaveOfTorment() -> Any:
    """``UtilityAI_Spell.au3:4556`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WaveOfTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4561`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CorruptedHealing() -> Any:
    """``UtilityAI_Spell.au3:4570`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CorruptedHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4575`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonTorment() -> Any:
    """``UtilityAI_Spell.au3:4585`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SummonTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4590`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OfferingOfSpirit() -> Any:
    """``UtilityAI_Spell.au3:4599`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OfferingOfSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4604`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReclaimEssence() -> Any:
    """``UtilityAI_Spell.au3:4613`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReclaimEssence(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4618`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticTwister() -> Any:
    """``UtilityAI_Spell.au3:4627`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MysticTwister(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4632`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturalHealing() -> Any:
    """``UtilityAI_Spell.au3:4641`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NaturalHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4646`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ImbueHealth() -> Any:
    """``UtilityAI_Spell.au3:4655`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    l_i_HP = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP)
    if l_i_HP < 0.6:
        return False
    return True


def BestTarget_ImbueHealth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4662`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.7:
        return l_i_Target


def CanUse_MysticHealing() -> Any:
    """``UtilityAI_Spell.au3:4673`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MysticHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4678`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DwaynasTouch() -> Any:
    """``UtilityAI_Spell.au3:4687`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DwaynasTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4692`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_PiousRestoration() -> Any:
    """``UtilityAI_Spell.au3:4698`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PiousRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4703`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticSandstorm() -> Any:
    """``UtilityAI_Spell.au3:4712`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MysticSandstorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4717`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WindsOfDisenchantment() -> Any:
    """``UtilityAI_Spell.au3:4726`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WindsOfDisenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4731`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RendingTouch() -> Any:
    """``UtilityAI_Spell.au3:4740`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RendingTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4745`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TestOfFaith() -> Any:
    """``UtilityAI_Spell.au3:4755`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TestOfFaith(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4760`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SummoningOfTheScepter() -> Any:
    """``UtilityAI_Spell.au3:4772`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SummoningOfTheScepter(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4777`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RiseFromYourGrave() -> Any:
    """``UtilityAI_Spell.au3:4786`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RiseFromYourGrave(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4791`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathsRetreat() -> Any:
    """``UtilityAI_Spell.au3:4796`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DeathsRetreat(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4801`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Swap() -> Any:
    """``UtilityAI_Spell.au3:4807`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Swap(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4812`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ToxicChill() -> Any:
    """``UtilityAI_Spell.au3:4822`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ToxicChill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4827`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Glowstone() -> Any:
    """``UtilityAI_Spell.au3:4841`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Glowstone(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4846`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MindBlast() -> Any:
    """``UtilityAI_Spell.au3:4858`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MindBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4863`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_InvokeLightning() -> Any:
    """``UtilityAI_Spell.au3:4873`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_InvokeLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4878`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_BattleCry1() -> Any:
    """``UtilityAI_Spell.au3:4888`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BattleCry1(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4893`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MendingShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:4898`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendingShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4903`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergyShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:4912`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergyShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4917`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NorthernHealthShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:4926`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NorthernHealthShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4931`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SouthernHealthShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:4940`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SouthernHealthShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4945`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ToThePainHeroBattles() -> Any:
    """``UtilityAI_Spell.au3:4954`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ToThePainHeroBattles(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4959`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlimmerOfLight() -> Any:
    """``UtilityAI_Spell.au3:4964`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GlimmerOfLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4969`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_ZealousBenediction() -> Any:
    """``UtilityAI_Spell.au3:4979`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ZealousBenediction(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4984`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_DismissCondition() -> Any:
    """``UtilityAI_Spell.au3:4993`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DismissCondition(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:4998`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_DivertHexes() -> Any:
    """``UtilityAI_Spell.au3:5011`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DivertHexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5016`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly")


def CanUse_SunspearSiege() -> Any:
    """``UtilityAI_Spell.au3:5028`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SunspearSiege(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5033`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WieldersStrike() -> Any:
    """``UtilityAI_Spell.au3:5042`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WieldersStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5047`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GhostmirrorLight() -> Any:
    """``UtilityAI_Spell.au3:5053`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    l_i_SpiritCount = UAI_CountAgents(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsSpirit")
    if l_i_SpiritCount <= 0:
        return False
    return True


def BestTarget_GhostmirrorLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5061`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_CaretakersCharge() -> Any:
    """``UtilityAI_Spell.au3:5071`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CaretakersCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5076`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AltarBuff() -> Any:
    """``UtilityAI_Spell.au3:5082`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AltarBuff(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5087`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CapturePoint() -> Any:
    """``UtilityAI_Spell.au3:5096`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CapturePoint(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5101`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BanishEnchantment() -> Any:
    """``UtilityAI_Spell.au3:5110`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BanishEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5115`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_UnyieldingAnguish() -> Any:
    """``UtilityAI_Spell.au3:5127`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UnyieldingAnguish(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5132`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PutridFlames() -> Any:
    """``UtilityAI_Spell.au3:5141`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PutridFlames(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5146`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireDart() -> Any:
    """``UtilityAI_Spell.au3:5155`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireDart(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5160`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IceDart() -> Any:
    """``UtilityAI_Spell.au3:5169`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_IceDart(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5174`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PoisonDart() -> Any:
    """``UtilityAI_Spell.au3:5183`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonDart(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5188`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PowerLock() -> Any:
    """``UtilityAI_Spell.au3:5197`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PowerLock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5202`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_WasteNotWantNot() -> Any:
    """``UtilityAI_Spell.au3:5212`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WasteNotWantNot(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5217`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CureHex() -> Any:
    """``UtilityAI_Spell.au3:5223`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CureHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5228`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")


def CanUse_SmiteCondition() -> Any:
    """``UtilityAI_Spell.au3:5237`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SmiteCondition(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5242`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned")


def CanUse_BurningGround() -> Any:
    """``UtilityAI_Spell.au3:5252`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BurningGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5257`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FreezingGround() -> Any:
    """``UtilityAI_Spell.au3:5266`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FreezingGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5271`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PoisonGround() -> Any:
    """``UtilityAI_Spell.au3:5280`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5285`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireJet() -> Any:
    """``UtilityAI_Spell.au3:5294`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireJet(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5299`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PoisonJet() -> Any:
    """``UtilityAI_Spell.au3:5308`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonJet(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5313`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireSpout() -> Any:
    """``UtilityAI_Spell.au3:5322`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireSpout(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5327`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PoisonSpout() -> Any:
    """``UtilityAI_Spell.au3:5336`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PoisonSpout(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5341`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SarcophagusSpores() -> Any:
    """``UtilityAI_Spell.au3:5350`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SarcophagusSpores(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5355`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExplodingBarrel() -> Any:
    """``UtilityAI_Spell.au3:5360`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ExplodingBarrel(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5365`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonSpiritsLuxon() -> Any:
    """``UtilityAI_Spell.au3:5370`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpiritsAt5000 = UAI_CountAgents(-2, 5000, "UAI_Filter_IsControlledSpirit")
    if lSpiritsAt5000 == 0:
        return False
    lSpiritsAt1000 = UAI_CountAgents(-2, 1000, "UAI_Filter_IsControlledSpirit")
    if lSpiritsAt5000 > 0 and lSpiritsAt1000 == lSpiritsAt5000:
        lLowestSpirit = UAI_GetAgentLowest(-2, 1320, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsControlledSpirit")
        if UAI_GetAgentInfoByID(lLowestSpirit, _constants.GC_UAI_AGENT_HP) < 0.85:
            return True
        return False

        return True


def BestTarget_SummonSpiritsLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5386`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Aneurysm() -> Any:
    """``UtilityAI_Spell.au3:5391`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Aneurysm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5396`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_FoulFeast() -> Any:
    """``UtilityAI_Spell.au3:5408`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FoulFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5413`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned")


def CanUse_ShellShock() -> Any:
    """``UtilityAI_Spell.au3:5423`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShellShock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5428`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_HealingRibbon() -> Any:
    """``UtilityAI_Spell.au3:5438`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealingRibbon(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5443`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_DrainMinion() -> Any:
    """``UtilityAI_Spell.au3:5453`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DrainMinion(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5458`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FleshreaversEscape() -> Any:
    """``UtilityAI_Spell.au3:5468`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FleshreaversEscape(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5473`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MandragorsCharge() -> Any:
    """``UtilityAI_Spell.au3:5478`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MandragorsCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5483`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RockSlide() -> Any:
    """``UtilityAI_Spell.au3:5489`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RockSlide(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5494`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvalancheEffect() -> Any:
    """``UtilityAI_Spell.au3:5503`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AvalancheEffect(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5508`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CeilingCollapse() -> Any:
    """``UtilityAI_Spell.au3:5513`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CeilingCollapse(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5518`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_SummonSpiritsKurzick() -> Any:
    """``UtilityAI_Spell.au3:5528`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpiritsAt5000 = UAI_CountAgents(-2, 5000, "UAI_Filter_IsControlledSpirit")
    if lSpiritsAt5000 == 0:
        return False
    lSpiritsAt1000 = UAI_CountAgents(-2, 1000, "UAI_Filter_IsControlledSpirit")
    if lSpiritsAt5000 > 0 and lSpiritsAt1000 == lSpiritsAt5000:
        lLowestSpirit = UAI_GetAgentLowest(-2, 1320, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsControlledSpirit")
        if UAI_GetAgentInfoByID(lLowestSpirit, _constants.GC_UAI_AGENT_HP) < 0.85:
            return True
        return False

        return True


def BestTarget_SummonSpiritsKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5544`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CryOfPain() -> Any:
    """``UtilityAI_Spell.au3:5549`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CryOfPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5554`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_GolemFireShield() -> Any:
    """``UtilityAI_Spell.au3:5564`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GolemFireShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5569`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DiamondshardGrave() -> Any:
    """``UtilityAI_Spell.au3:5578`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DiamondshardGrave(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5583`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DiamondshardMist() -> Any:
    """``UtilityAI_Spell.au3:5592`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DiamondshardMist(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5597`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenSwoopAGateTooFar() -> Any:
    """``UtilityAI_Spell.au3:5606`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RavenSwoopAGateTooFar(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5611`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AngorodonsGaze() -> Any:
    """``UtilityAI_Spell.au3:5617`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AngorodonsGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5622`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SlipperyGround() -> Any:
    """``UtilityAI_Spell.au3:5628`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SlipperyGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5633`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_GlowingIce() -> Any:
    """``UtilityAI_Spell.au3:5643`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GlowingIce(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5648`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyBlast() -> Any:
    """``UtilityAI_Spell.au3:5660`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergyBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5665`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MendingGrip() -> Any:
    """``UtilityAI_Spell.au3:5675`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendingGrip(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5680`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_AlkarsAlchemicalAcid() -> Any:
    """``UtilityAI_Spell.au3:5690`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AlkarsAlchemicalAcid(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5695`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LightOfDeldrimor() -> Any:
    """``UtilityAI_Spell.au3:5701`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightOfDeldrimor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5706`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BreathOfTheGreatDwarf() -> Any:
    """``UtilityAI_Spell.au3:5715`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BreathOfTheGreatDwarf(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5720`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SnowStorm() -> Any:
    """``UtilityAI_Spell.au3:5729`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SnowStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5734`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_SPELLCASTING, "UAI_Filter_IsLivingEnemy")


def CanUse_SummonMursaat() -> Any:
    """``UtilityAI_Spell.au3:5743`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpirit = UAI_FindAgentByPlayerNumber(5847, -2, 2500, "UAI_Filter_IsLivingAlly")
    if lSpirit != 0:
        if UAI_GetAgentInfoByID(lSpirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_SummonMursaat(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5755`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonRubyDjinn() -> Any:
    """``UtilityAI_Spell.au3:5764`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpirit = UAI_FindAgentByPlayerNumber(5848, -2, 2500, "UAI_Filter_IsLivingAlly")
    if lSpirit != 0:
        if UAI_GetAgentInfoByID(lSpirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_SummonRubyDjinn(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5776`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonIceImp() -> Any:
    """``UtilityAI_Spell.au3:5785`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpirit = UAI_FindAgentByPlayerNumber(5849, -2, 2500, "UAI_Filter_IsLivingAlly")
    if lSpirit != 0:
        if UAI_GetAgentInfoByID(lSpirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_SummonIceImp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5797`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonNagaShaman() -> Any:
    """``UtilityAI_Spell.au3:5806`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    lSpirit = UAI_FindAgentByPlayerNumber(5850, -2, 2500, "UAI_Filter_IsLivingAlly")
    if lSpirit != 0:
        if UAI_GetAgentInfoByID(lSpirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_SummonNagaShaman(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5818`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EbonVanguardSniperSupport() -> Any:
    """``UtilityAI_Spell.au3:5827`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EbonVanguardSniperSupport(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5832`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EbonVanguardAssassinSupport() -> Any:
    """``UtilityAI_Spell.au3:5842`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EbonVanguardAssassinSupport(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5848`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMonk|UAI_Filter_IsHexedOrConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster|UAI_Filter_IsHexedOrConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMonk")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockPowerDrain() -> Any:
    """``UtilityAI_Spell.au3:5875`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockPowerDrain(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5880`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_PolymockOverload() -> Any:
    """``UtilityAI_Spell.au3:5890`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockOverload(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5895`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_OrderOfUnholyVigor() -> Any:
    """``UtilityAI_Spell.au3:5907`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OrderOfUnholyVigor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5912`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfTheLich() -> Any:
    """``UtilityAI_Spell.au3:5921`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OrderOfTheLich(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5926`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MasterOfNecromancy() -> Any:
    """``UtilityAI_Spell.au3:5935`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MasterOfNecromancy(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5940`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnimateUndead() -> Any:
    """``UtilityAI_Spell.au3:5949`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateUndead(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5954`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockDeathlyChill() -> Any:
    """``UtilityAI_Spell.au3:5963`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockDeathlyChill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5968`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockRottingFlesh() -> Any:
    """``UtilityAI_Spell.au3:5978`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockRottingFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5983`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockLightningStrike() -> Any:
    """``UtilityAI_Spell.au3:5993`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockLightningStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:5998`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockLightningOrb() -> Any:
    """``UtilityAI_Spell.au3:6008`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockLightningOrb(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6013`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockFlare() -> Any:
    """``UtilityAI_Spell.au3:6023`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockFlare(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6028`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockImmolate() -> Any:
    """``UtilityAI_Spell.au3:6038`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockImmolate(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6043`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockMeteor() -> Any:
    """``UtilityAI_Spell.au3:6053`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockMeteor(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6058`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockIceSpear() -> Any:
    """``UtilityAI_Spell.au3:6070`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockIceSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6075`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockIcyPrison() -> Any:
    """``UtilityAI_Spell.au3:6085`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockIcyPrison(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6090`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")


def CanUse_PolymockMindFreeze() -> Any:
    """``UtilityAI_Spell.au3:6100`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockMindFreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6105`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockIceShardStorm() -> Any:
    """``UtilityAI_Spell.au3:6115`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockIceShardStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6120`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockFrozenTrident() -> Any:
    """``UtilityAI_Spell.au3:6130`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockFrozenTrident(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6135`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSmite() -> Any:
    """``UtilityAI_Spell.au3:6147`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSmite(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6152`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSmiteHex() -> Any:
    """``UtilityAI_Spell.au3:6162`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSmiteHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6167`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockStoneDaggers() -> Any:
    """``UtilityAI_Spell.au3:6177`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockStoneDaggers(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6182`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockObsidianFlame() -> Any:
    """``UtilityAI_Spell.au3:6192`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockObsidianFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6197`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockEarthquake() -> Any:
    """``UtilityAI_Spell.au3:6207`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockEarthquake(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6212`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockFireball() -> Any:
    """``UtilityAI_Spell.au3:6224`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockFireball(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6229`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockRodgortsInvocation() -> Any:
    """``UtilityAI_Spell.au3:6239`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockRodgortsInvocation(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6244`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockLamentation() -> Any:
    """``UtilityAI_Spell.au3:6250`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockLamentation(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6255`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSpiritRift() -> Any:
    """``UtilityAI_Spell.au3:6265`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSpiritRift(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6270`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockGlowingGaze() -> Any:
    """``UtilityAI_Spell.au3:6280`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockGlowingGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6285`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBurning")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSearingFlames() -> Any:
    """``UtilityAI_Spell.au3:6297`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSearingFlames(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6302`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBurning")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockStoning() -> Any:
    """``UtilityAI_Spell.au3:6314`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockStoning(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6319`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockEruption() -> Any:
    """``UtilityAI_Spell.au3:6329`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockEruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6334`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockShockArrow() -> Any:
    """``UtilityAI_Spell.au3:6344`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockShockArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6349`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockMindShock() -> Any:
    """``UtilityAI_Spell.au3:6359`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockMindShock(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6364`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockPiercingLightSpear() -> Any:
    """``UtilityAI_Spell.au3:6374`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockPiercingLightSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6379`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockMindBlast() -> Any:
    """``UtilityAI_Spell.au3:6389`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockMindBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6394`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSavannahHeat() -> Any:
    """``UtilityAI_Spell.au3:6404`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSavannahHeat(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6409`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockLightningBlast() -> Any:
    """``UtilityAI_Spell.au3:6419`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockLightningBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6424`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockPoisonedGround() -> Any:
    """``UtilityAI_Spell.au3:6434`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockPoisonedGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6439`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockSandstorm() -> Any:
    """``UtilityAI_Spell.au3:6449`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockSandstorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6454`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockBanish() -> Any:
    """``UtilityAI_Spell.au3:6466`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PolymockBanish(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6471`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MurakaisConsumption() -> Any:
    """``UtilityAI_Spell.au3:6481`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MurakaisConsumption(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6486`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_MurakaisCensure() -> Any:
    """``UtilityAI_Spell.au3:6492`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MurakaisCensure(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6497`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MurakaisCalamity() -> Any:
    """``UtilityAI_Spell.au3:6502`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MurakaisCalamity(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6507`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MurakaisStormOfSouls() -> Any:
    """``UtilityAI_Spell.au3:6512`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MurakaisStormOfSouls(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6517`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenSwoop() -> Any:
    """``UtilityAI_Spell.au3:6522`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RavenSwoop(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6527`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FilthyExplosion() -> Any:
    """``UtilityAI_Spell.au3:6537`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FilthyExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6542`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MurakaisCall() -> Any:
    """``UtilityAI_Spell.au3:6551`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MurakaisCall(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6556`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConsumeFlames() -> Any:
    """``UtilityAI_Spell.au3:6561`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ConsumeFlames(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6566`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SmoothCriminal() -> Any:
    """``UtilityAI_Spell.au3:6575`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SmoothCriminal(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6580`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Technobabble() -> Any:
    """``UtilityAI_Spell.au3:6590`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Technobabble(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6595`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_EbonEscape() -> Any:
    """``UtilityAI_Spell.au3:6605`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EbonEscape(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6610`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_DrydersFeast() -> Any:
    """``UtilityAI_Spell.au3:6622`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DrydersFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6627`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_ReversePolarityFireShield() -> Any:
    """``UtilityAI_Spell.au3:6633`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReversePolarityFireShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6638`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnimateUndeadPalawaJoko() -> Any:
    """``UtilityAI_Spell.au3:6647`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateUndeadPalawaJoko(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6652`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfUnholyVigorPalawaJoko() -> Any:
    """``UtilityAI_Spell.au3:6657`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OrderOfUnholyVigorPalawaJoko(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6662`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfTheLichPalawaJoko() -> Any:
    """``UtilityAI_Spell.au3:6667`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OrderOfTheLichPalawaJoko(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6672`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WurmSiegeEyeOfTheNorth() -> Any:
    """``UtilityAI_Spell.au3:6677`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WurmSiegeEyeOfTheNorth(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6682`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Enfeeble2() -> Any:
    """``UtilityAI_Spell.au3:6689`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Enfeeble2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6694`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SearingFlames2() -> Any:
    """``UtilityAI_Spell.au3:6701`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SearingFlames2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6706`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_GlowingGaze2() -> Any:
    """``UtilityAI_Spell.au3:6712`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GlowingGaze2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6717`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Steam2() -> Any:
    """``UtilityAI_Spell.au3:6723`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Steam2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6728`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LiquidFlam2() -> Any:
    """``UtilityAI_Spell.au3:6734`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LiquidFlam2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6739`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SmiteCondition2() -> Any:
    """``UtilityAI_Spell.au3:6746`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SmiteCondition2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6751`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpikeTrapSpell() -> Any:
    """``UtilityAI_Spell.au3:6757`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpikeTrapSpell(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6762`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireAndBrimstone() -> Any:
    """``UtilityAI_Spell.au3:6767`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FireAndBrimstone(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6772`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EssenceStrikeTogo() -> Any:
    """``UtilityAI_Spell.au3:6782`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EssenceStrikeTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6787`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritBurnTogo() -> Any:
    """``UtilityAI_Spell.au3:6793`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritBurnTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6798`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritRiftTogo() -> Any:
    """``UtilityAI_Spell.au3:6804`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritRiftTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6809`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MendBodyAndSoulTogo() -> Any:
    """``UtilityAI_Spell.au3:6815`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MendBodyAndSoulTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6820`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_OfferingOfSpiritTogo() -> Any:
    """``UtilityAI_Spell.au3:6826`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_OfferingOfSpiritTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6831`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RedemptionOfPurity() -> Any:
    """``UtilityAI_Spell.au3:6836`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RedemptionOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6841`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PurifyEnergy() -> Any:
    """``UtilityAI_Spell.au3:6851`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PurifyEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6856`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PurifyingFlame() -> Any:
    """``UtilityAI_Spell.au3:6865`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PurifyingFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6870`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PurifyingPrayer() -> Any:
    """``UtilityAI_Spell.au3:6879`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PurifyingPrayer(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6884`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly|UAI_Filter_IsConditioned|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsAlly")


def CanUse_PurifySoul() -> Any:
    """``UtilityAI_Spell.au3:6896`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PurifySoul(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6901`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JadeBrotherhoodBomb() -> Any:
    """``UtilityAI_Spell.au3:6910`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_JadeBrotherhoodBomb(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6915`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RocketPropelledGobstopper() -> Any:
    """``UtilityAI_Spell.au3:6924`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RocketPropelledGobstopper(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6929`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RainOfTerrorSpell() -> Any:
    """``UtilityAI_Spell.au3:6935`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RainOfTerrorSpell(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6940`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SugarInfusion() -> Any:
    """``UtilityAI_Spell.au3:6946`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SugarInfusion(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6951`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_FeastOfVengeance() -> Any:
    """``UtilityAI_Spell.au3:6961`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FeastOfVengeance(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6966`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnimateCandyMinions() -> Any:
    """``UtilityAI_Spell.au3:6976`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnimateCandyMinions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6981`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TasteOfUndeath() -> Any:
    """``UtilityAI_Spell.au3:6990`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TasteOfUndeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:6995`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ScourgeOfCandy() -> Any:
    """``UtilityAI_Spell.au3:7005`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ScourgeOfCandy(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7010`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MadKingPonySupport() -> Any:
    """``UtilityAI_Spell.au3:7020`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MadKingPonySupport(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7025`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MindShockPvp() -> Any:
    """``UtilityAI_Spell.au3:7040`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MindShockPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7045`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RideTheLightningPvp() -> Any:
    """``UtilityAI_Spell.au3:7051`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_RideTheLightningPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7056`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ObsidianFlamePvp() -> Any:
    """``UtilityAI_Spell.au3:7062`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ObsidianFlamePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7067`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyDrainPvp() -> Any:
    """``UtilityAI_Spell.au3:7076`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergyDrainPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7081`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnergyTapPvp() -> Any:
    """``UtilityAI_Spell.au3:7089`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnergyTapPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7094`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningOrbPvp() -> Any:
    """``UtilityAI_Spell.au3:7102`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningOrbPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7107`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnfeeblePvp() -> Any:
    """``UtilityAI_Spell.au3:7113`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnfeeblePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7118`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DiscordPvp() -> Any:
    """``UtilityAI_Spell.au3:7124`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DiscordPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7129`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FleshOfMyFleshPvp() -> Any:
    """``UtilityAI_Spell.au3:7135`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_FleshOfMyFleshPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7141`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_BlindingSurgePvp() -> Any:
    """``UtilityAI_Spell.au3:7147`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BlindingSurgePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7152`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LightOfDeliverancePvp() -> Any:
    """``UtilityAI_Spell.au3:7158`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightOfDeliverancePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7163`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnfeeblingBloodPvp() -> Any:
    """``UtilityAI_Spell.au3:7169`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EnfeeblingBloodPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7174`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ReactorBlast() -> Any:
    """``UtilityAI_Spell.au3:7180`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReactorBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7185`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoxBeam() -> Any:
    """``UtilityAI_Spell.au3:7194`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxBeam(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7199`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_NoxionBuster() -> Any:
    """``UtilityAI_Spell.au3:7205`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxionBuster(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7210`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BitGolemBreaker() -> Any:
    """``UtilityAI_Spell.au3:7216`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BitGolemBreaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7221`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BitGolemCrash() -> Any:
    """``UtilityAI_Spell.au3:7231`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BitGolemCrash(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7236`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BitGolemForce() -> Any:
    """``UtilityAI_Spell.au3:7245`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_BitGolemForce(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7250`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoxThunder() -> Any:
    """``UtilityAI_Spell.au3:7259`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxThunder(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7264`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_NoxFire() -> Any:
    """``UtilityAI_Spell.au3:7270`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7275`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoxKnuckle() -> Any:
    """``UtilityAI_Spell.au3:7280`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxKnuckle(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7285`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_NoxDividerDrive() -> Any:
    """``UtilityAI_Spell.au3:7291`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_NoxDividerDrive(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7296`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShrineBacklash() -> Any:
    """``UtilityAI_Spell.au3:7302`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShrineBacklash(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7307`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WesternHealthShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:7323`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_WesternHealthShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7328`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EasternHealthShrineBonus() -> Any:
    """``UtilityAI_Spell.au3:7337`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EasternHealthShrineBonus(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7342`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Snowball2() -> Any:
    """``UtilityAI_Spell.au3:7351`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Snowball2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7356`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SavannahHeatPvp() -> Any:
    """``UtilityAI_Spell.au3:7362`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SavannahHeatPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7367`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritSiphonMasterRiyo() -> Any:
    """``UtilityAI_Spell.au3:7373`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritSiphonMasterRiyo(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7378`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UnholyFeastPvp() -> Any:
    """``UtilityAI_Spell.au3:7384`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UnholyFeastPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7389`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EverlastingMobstopperSkill() -> Any:
    """``UtilityAI_Spell.au3:7394`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EverlastingMobstopperSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7399`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CurseOfDhuum() -> Any:
    """``UtilityAI_Spell.au3:7405`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_CurseOfDhuum(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7410`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DhuumsRestReaperSkill() -> Any:
    """``UtilityAI_Spell.au3:7419`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DhuumsRestReaperSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7424`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonChampion() -> Any:
    """``UtilityAI_Spell.au3:7429`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SummonChampion(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7434`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummonMinions() -> Any:
    """``UtilityAI_Spell.au3:7443`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SummonMinions(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7448`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JudgmentOfDhuum() -> Any:
    """``UtilityAI_Spell.au3:7457`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_JudgmentOfDhuum(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7462`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DhuumsRest() -> Any:
    """``UtilityAI_Spell.au3:7471`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DhuumsRest(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7476`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritualHealing() -> Any:
    """``UtilityAI_Spell.au3:7481`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritualHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7486`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_EncaseSkeletal() -> Any:
    """``UtilityAI_Spell.au3:7496`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EncaseSkeletal(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7501`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ReversalOfDeath() -> Any:
    """``UtilityAI_Spell.au3:7511`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReversalOfDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7516`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_GhostlyFury() -> Any:
    """``UtilityAI_Spell.au3:7526`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GhostlyFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7531`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritualHealingReaperSkill() -> Any:
    """``UtilityAI_Spell.au3:7541`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritualHealingReaperSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7546`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")


def CanUse_GhostlyFuryReaperSkill() -> Any:
    """``UtilityAI_Spell.au3:7552`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GhostlyFuryReaperSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7557`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GolemPilebunker() -> Any:
    """``UtilityAI_Spell.au3:7563`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_GolemPilebunker(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7568`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KorosGaze() -> Any:
    """``UtilityAI_Spell.au3:7581`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_KorosGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7586`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EbonVanguardAssassinSupportNpc() -> Any:
    """``UtilityAI_Spell.au3:7592`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_EbonVanguardAssassinSupportNpc(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7597`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShatterDelusionsPvp() -> Any:
    """``UtilityAI_Spell.au3:7603`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ShatterDelusionsPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7608`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_AccumulatedPainPvp() -> Any:
    """``UtilityAI_Spell.au3:7616`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AccumulatedPainPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7621`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PsychicInstabilityPvp() -> Any:
    """``UtilityAI_Spell.au3:7627`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PsychicInstabilityPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7632`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritualPainPvp() -> Any:
    """``UtilityAI_Spell.au3:7638`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SpiritualPainPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7643`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MirrorOfDisenchantmentPvp() -> Any:
    """``UtilityAI_Spell.au3:7649`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MirrorOfDisenchantmentPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7654`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_Adoration() -> Any:
    """``UtilityAI_Spell.au3:7660`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Adoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7665`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_HealPartyPvp() -> Any:
    """``UtilityAI_Spell.au3:7675`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_HealPartyPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7680`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ComingOfSpring() -> Any:
    """``UtilityAI_Spell.au3:7685`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ComingOfSpring(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7690`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathsEmbrace() -> Any:
    """``UtilityAI_Spell.au3:7696`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_DeathsEmbrace(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7701`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UltraSnowball() -> Any:
    """``UtilityAI_Spell.au3:7707`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UltraSnowball(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7712`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Blizzard() -> Any:
    """``UtilityAI_Spell.au3:7722`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_Blizzard(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7727`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UltraSnowball2() -> Any:
    """``UtilityAI_Spell.au3:7737`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UltraSnowball2(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7742`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UltraSnowball3() -> Any:
    """``UtilityAI_Spell.au3:7748`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UltraSnowball3(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7753`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UltraSnowball4() -> Any:
    """``UtilityAI_Spell.au3:7759`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UltraSnowball4(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7764`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UltraSnowball5() -> Any:
    """``UtilityAI_Spell.au3:7770`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_UltraSnowball5(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7775`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MysticHealingPvp() -> Any:
    """``UtilityAI_Spell.au3:7781`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MysticHealingPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7786`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StunGrenade() -> Any:
    """``UtilityAI_Spell.au3:7791`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_StunGrenade(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7796`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FragmentationGrenade() -> Any:
    """``UtilityAI_Spell.au3:7806`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_FragmentationGrenade(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7811`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_TearGas() -> Any:
    """``UtilityAI_Spell.au3:7821`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_TearGas(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7826`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_PhasedPlasmaBurst() -> Any:
    """``UtilityAI_Spell.au3:7836`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PhasedPlasmaBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7841`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PlasmaShot() -> Any:
    """``UtilityAI_Spell.au3:7851`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PlasmaShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7856`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MirrorShatter() -> Any:
    """``UtilityAI_Spell.au3:7866`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_MirrorShatter(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7871`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PhaseShield() -> Any:
    """``UtilityAI_Spell.au3:7876`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_PhaseShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7881`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReactorBurst() -> Any:
    """``UtilityAI_Spell.au3:7890`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_ReactorBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7895`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnnihilatorBeam() -> Any:
    """``UtilityAI_Spell.au3:7904`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_AnnihilatorBeam(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7909`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningHammerPvp() -> Any:
    """``UtilityAI_Spell.au3:7919`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_LightningHammerPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7924`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SlipperyGroundPvp() -> Any:
    """``UtilityAI_Spell.au3:7930`` -- transcribed from GwAu3's own body."""

    if Anti_Spell():
        return False
    return True


def BestTarget_SlipperyGroundPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Spell.au3:7935`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


__all__ = [
    "BestTarget_AccumulatedPain",
    "BestTarget_AccumulatedPainPvp",
    "BestTarget_Adoration",
    "BestTarget_Aftershock",
    "BestTarget_AlkarsAlchemicalAcid",
    "BestTarget_AltarBuff",
    "BestTarget_Aneurysm",
    "BestTarget_AngorodonsGaze",
    "BestTarget_AnimateBoneFiend",
    "BestTarget_AnimateBoneHorror",
    "BestTarget_AnimateBoneMinions",
    "BestTarget_AnimateCandyMinions",
    "BestTarget_AnimateFleshGolem",
    "BestTarget_AnimateShamblingHorror",
    "BestTarget_AnimateUndead",
    "BestTarget_AnimateUndeadPalawaJoko",
    "BestTarget_AnimateVampiricHorror",
    "BestTarget_AnnihilatorBeam",
    "BestTarget_ArcLightning",
    "BestTarget_ArcaneLarceny",
    "BestTarget_ArcaneMimicry",
    "BestTarget_ArcaneThievery",
    "BestTarget_ArchemorusStrike",
    "BestTarget_ArchemorusStrikeCelestialSummoning",
    "BestTarget_ArgosCry",
    "BestTarget_AvalancheEffect",
    "BestTarget_AvalancheSkill",
    "BestTarget_Banish",
    "BestTarget_BanishEnchantment",
    "BestTarget_BattleCry1",
    "BestTarget_BattleCry2",
    "BestTarget_BedOfCoals",
    "BestTarget_BeguilingHaze",
    "BestTarget_BitGolemBreaker",
    "BestTarget_BitGolemCrash",
    "BestTarget_BitGolemForce",
    "BestTarget_BitterChill",
    "BestTarget_BlastFurnace",
    "BestTarget_BlessedLight",
    "BestTarget_BlindingFlash",
    "BestTarget_BlindingPowder",
    "BestTarget_BlindingSnow",
    "BestTarget_BlindingSurge",
    "BestTarget_BlindingSurgePvp",
    "BestTarget_Blizzard",
    "BestTarget_BloodDrinker",
    "BestTarget_BloodFlowerSkill",
    "BestTarget_BloodOfTheAggressor",
    "BestTarget_BloodOfTheMaster",
    "BestTarget_BloodOfZuHeltzer",
    "BestTarget_BreathOfFire",
    "BestTarget_BreathOfTheGreatDwarf",
    "BestTarget_BurningGround",
    "BestTarget_Caltrops",
    "BestTarget_CapturePoint",
    "BestTarget_CaretakersCharge",
    "BestTarget_CathedralCollapse2",
    "BestTarget_CeilingCollapse",
    "BestTarget_CelestialHaste",
    "BestTarget_ChainLightning",
    "BestTarget_ChainLightningEnvironment",
    "BestTarget_ChanneledStrike",
    "BestTarget_ChaosStorm",
    "BestTarget_Chilblains",
    "BestTarget_Chomper",
    "BestTarget_ChurningEarth",
    "BestTarget_ClamorOfSouls",
    "BestTarget_ComingOfSpring",
    "BestTarget_Complicate",
    "BestTarget_ConsumeCorpse",
    "BestTarget_ConsumeFlames",
    "BestTarget_ConsumeSoul",
    "BestTarget_ConvertHexes",
    "BestTarget_CorruptedDragonScales",
    "BestTarget_CorruptedDragonSpores",
    "BestTarget_CorruptedHealing",
    "BestTarget_CripplingDagger",
    "BestTarget_CryOfFrustration",
    "BestTarget_CryOfLament",
    "BestTarget_CryOfPain",
    "BestTarget_CrystalWave",
    "BestTarget_CureHex",
    "BestTarget_CurseOfDhuum",
    "BestTarget_CurseOfTheBloodstone",
    "BestTarget_DancingDaggers",
    "BestTarget_DarkPact",
    "BestTarget_DeathlyChill",
    "BestTarget_DeathlySwarm",
    "BestTarget_DeathsCharge",
    "BestTarget_DeathsEmbrace",
    "BestTarget_DeathsRetreat",
    "BestTarget_DefileEnchantments",
    "BestTarget_DenyHexes",
    "BestTarget_DesecrateEnchantments",
    "BestTarget_DhuumsRest",
    "BestTarget_DhuumsRestReaperSkill",
    "BestTarget_DiamondshardGrave",
    "BestTarget_DiamondshardMist",
    "BestTarget_DischargeEnchantment",
    "BestTarget_Discord",
    "BestTarget_DiscordPvp",
    "BestTarget_DismissCondition",
    "BestTarget_DisruptingDagger",
    "BestTarget_DivertHexes",
    "BestTarget_DivineHealing",
    "BestTarget_DomainOfElements",
    "BestTarget_DomainOfEnergyDraining",
    "BestTarget_DomainOfHealthDraining",
    "BestTarget_DomainOfSkillDamage",
    "BestTarget_DomainOfSlow",
    "BestTarget_Doom",
    "BestTarget_DragonsStomp",
    "BestTarget_DrainDelusions",
    "BestTarget_DrainEnchantment",
    "BestTarget_DrainMinion",
    "BestTarget_DrawConditions",
    "BestTarget_DrawSpirit",
    "BestTarget_DrydersFeast",
    "BestTarget_DwaynasKiss",
    "BestTarget_DwaynasTouch",
    "BestTarget_Earthquake",
    "BestTarget_EasternHealthShrineBonus",
    "BestTarget_EbonEscape",
    "BestTarget_EbonHawk",
    "BestTarget_EbonVanguardAssassinSupport",
    "BestTarget_EbonVanguardAssassinSupportNpc",
    "BestTarget_EbonVanguardSniperSupport",
    "BestTarget_ElementalDefenseZone",
    "BestTarget_EmpathicRemoval",
    "BestTarget_EncaseSkeletal",
    "BestTarget_EnergyBlast",
    "BestTarget_EnergyBurn",
    "BestTarget_EnergyDrain",
    "BestTarget_EnergyDrainPvp",
    "BestTarget_EnergyShrineBonus",
    "BestTarget_EnergySurge",
    "BestTarget_EnergyTap",
    "BestTarget_EnergyTapPvp",
    "BestTarget_EnervatingCharge",
    "BestTarget_Enfeeble1",
    "BestTarget_Enfeeble2",
    "BestTarget_EnfeeblePvp",
    "BestTarget_EnfeeblingBlood",
    "BestTarget_EnfeeblingBloodPvp",
    "BestTarget_EntanglingAsp",
    "BestTarget_EnvenomEnchantments",
    "BestTarget_Epidemic",
    "BestTarget_Eruption",
    "BestTarget_EruptionEnvironment",
    "BestTarget_EssenceStrike",
    "BestTarget_EssenceStrikeTogo",
    "BestTarget_EtherFeast",
    "BestTarget_EtherealLight",
    "BestTarget_EverlastingMobstopperSkill",
    "BestTarget_ExpelHexes",
    "BestTarget_ExplodingBarrel",
    "BestTarget_ExtendConditions",
    "BestTarget_Extinguish",
    "BestTarget_FakeSpell",
    "BestTarget_FeastForTheDead",
    "BestTarget_FeastOfCorruption",
    "BestTarget_FeastOfSouls",
    "BestTarget_FeastOfVengeance",
    "BestTarget_Feedback",
    "BestTarget_FetidGround",
    "BestTarget_FilthyExplosion",
    "BestTarget_FireAndBrimstone",
    "BestTarget_FireDart",
    "BestTarget_FireFlowerSkill",
    "BestTarget_FireJet",
    "BestTarget_FireSpout",
    "BestTarget_FireStorm",
    "BestTarget_FireStormEnvironment",
    "BestTarget_Fireball",
    "BestTarget_FireballObelisk",
    "BestTarget_FlameBurst",
    "BestTarget_Flare",
    "BestTarget_FleshOfMyFlesh",
    "BestTarget_FleshOfMyFleshPvp",
    "BestTarget_FleshreaversEscape",
    "BestTarget_FlurryOfIce",
    "BestTarget_FoulFeast",
    "BestTarget_FountOfMaguuma",
    "BestTarget_FragmentationGrenade",
    "BestTarget_FreezingGround",
    "BestTarget_Gale",
    "BestTarget_GazeFromBeyond",
    "BestTarget_GazeOfContempt",
    "BestTarget_GhostlyFury",
    "BestTarget_GhostlyFuryReaperSkill",
    "BestTarget_GhostmirrorLight",
    "BestTarget_GiftOfHealth",
    "BestTarget_GlimmerOfLight",
    "BestTarget_GlowingGaze1",
    "BestTarget_GlowingGaze2",
    "BestTarget_GlowingIce",
    "BestTarget_Glowstone",
    "BestTarget_GolemFireShield",
    "BestTarget_GolemPilebunker",
    "BestTarget_GrenthsBalance",
    "BestTarget_GuardianPacify",
    "BestTarget_HealArea",
    "BestTarget_HealOther",
    "BestTarget_HealParty",
    "BestTarget_HealPartyPvp",
    "BestTarget_HealingBurst",
    "BestTarget_HealingFountain",
    "BestTarget_HealingLight",
    "BestTarget_HealingRibbon",
    "BestTarget_HealingRing",
    "BestTarget_HealingTouch",
    "BestTarget_HealingWhisper",
    "BestTarget_HeartOfShadow",
    "BestTarget_HeavensDelight",
    "BestTarget_HexEaterVortex",
    "BestTarget_HolidayBlues",
    "BestTarget_Hypochondria",
    "BestTarget_IceDart",
    "BestTarget_IcyGround",
    "BestTarget_IcyPrism",
    "BestTarget_ImbueHealth",
    "BestTarget_Immolate",
    "BestTarget_Inferno",
    "BestTarget_InfuseHealth",
    "BestTarget_InspiredEnchantment",
    "BestTarget_InspiredHex",
    "BestTarget_InvokeLightning",
    "BestTarget_JadeBrotherhoodBomb",
    "BestTarget_JadeFury",
    "BestTarget_JameisGaze",
    "BestTarget_JanthirsGaze",
    "BestTarget_JudgmentOfDhuum",
    "BestTarget_KareisHealingCircle",
    "BestTarget_KirinsWrath",
    "BestTarget_KorosGaze",
    "BestTarget_LavaArrows",
    "BestTarget_LavaFont",
    "BestTarget_LifebaneStrike",
    "BestTarget_LightOfDeldrimor",
    "BestTarget_LightOfDeliverance",
    "BestTarget_LightOfDeliverancePvp",
    "BestTarget_LightOfDwayna",
    "BestTarget_LightningBolt",
    "BestTarget_LightningHammer",
    "BestTarget_LightningHammerPvp",
    "BestTarget_LightningJavelin",
    "BestTarget_LightningOrb1",
    "BestTarget_LightningOrb2",
    "BestTarget_LightningOrbPvp",
    "BestTarget_LightningStorm",
    "BestTarget_LiquidFlam2",
    "BestTarget_LiquidFlame",
    "BestTarget_LyssasBalance",
    "BestTarget_MadKingPonySupport",
    "BestTarget_Maelstrom",
    "BestTarget_MaelstromEnvironment",
    "BestTarget_MandragorsCharge",
    "BestTarget_MantisTouch",
    "BestTarget_Martyr",
    "BestTarget_MasterOfNecromancy",
    "BestTarget_MegaSnowball",
    "BestTarget_MeleeDefenseZone",
    "BestTarget_MendAilment",
    "BestTarget_MendBodyAndSoul",
    "BestTarget_MendBodyAndSoulTogo",
    "BestTarget_MendCondition",
    "BestTarget_MendingGrip",
    "BestTarget_MendingShrineBonus",
    "BestTarget_MendingTouch",
    "BestTarget_Meteor",
    "BestTarget_MeteorShower",
    "BestTarget_Mimic",
    "BestTarget_MindBlast",
    "BestTarget_MindBurn",
    "BestTarget_MindShock",
    "BestTarget_MindShockPvp",
    "BestTarget_MirrorOfDisenchantment",
    "BestTarget_MirrorOfDisenchantmentPvp",
    "BestTarget_MirrorShatter",
    "BestTarget_MurakaisCalamity",
    "BestTarget_MurakaisCall",
    "BestTarget_MurakaisCensure",
    "BestTarget_MurakaisConsumption",
    "BestTarget_MurakaisStormOfSouls",
    "BestTarget_MursaatTowerSkill",
    "BestTarget_MysticHealing",
    "BestTarget_MysticHealingPvp",
    "BestTarget_MysticSandstorm",
    "BestTarget_MysticTwister",
    "BestTarget_NaturalHealing",
    "BestTarget_NecroticTraversal",
    "BestTarget_Nibble",
    "BestTarget_NorthernHealthShrineBonus",
    "BestTarget_NoxBeam",
    "BestTarget_NoxDividerDrive",
    "BestTarget_NoxFire",
    "BestTarget_NoxKnuckle",
    "BestTarget_NoxThunder",
    "BestTarget_NoxionBuster",
    "BestTarget_OathOfHealing",
    "BestTarget_ObeliskLightning",
    "BestTarget_ObsidianFlame",
    "BestTarget_ObsidianFlamePvp",
    "BestTarget_OfRoyalBlood",
    "BestTarget_OfferingOfBlood",
    "BestTarget_OfferingOfSpirit",
    "BestTarget_OfferingOfSpiritTogo",
    "BestTarget_OppressiveGaze",
    "BestTarget_OrderOfTheLich",
    "BestTarget_OrderOfTheLichPalawaJoko",
    "BestTarget_OrderOfUndeath",
    "BestTarget_OrderOfUnholyVigor",
    "BestTarget_OrderOfUnholyVigorPalawaJoko",
    "BestTarget_OrisonOfHealing",
    "BestTarget_PainOfDisenchantment",
    "BestTarget_PassageToTahnnakai",
    "BestTarget_PhaseShield",
    "BestTarget_PhasedPlasmaBurst",
    "BestTarget_Phoenix",
    "BestTarget_PiousRestoration",
    "BestTarget_PlagueSending",
    "BestTarget_PlasmaShot",
    "BestTarget_PoisonArrowFlower",
    "BestTarget_PoisonDart",
    "BestTarget_PoisonGround",
    "BestTarget_PoisonJet",
    "BestTarget_PoisonSpout",
    "BestTarget_PoisonedHeart",
    "BestTarget_PolymockBanish",
    "BestTarget_PolymockDeathlyChill",
    "BestTarget_PolymockEarthquake",
    "BestTarget_PolymockEruption",
    "BestTarget_PolymockFireball",
    "BestTarget_PolymockFlare",
    "BestTarget_PolymockFrozenTrident",
    "BestTarget_PolymockGlowingGaze",
    "BestTarget_PolymockIceShardStorm",
    "BestTarget_PolymockIceSpear",
    "BestTarget_PolymockIcyPrison",
    "BestTarget_PolymockImmolate",
    "BestTarget_PolymockLamentation",
    "BestTarget_PolymockLightningBlast",
    "BestTarget_PolymockLightningOrb",
    "BestTarget_PolymockLightningStrike",
    "BestTarget_PolymockMeteor",
    "BestTarget_PolymockMindBlast",
    "BestTarget_PolymockMindFreeze",
    "BestTarget_PolymockMindShock",
    "BestTarget_PolymockObsidianFlame",
    "BestTarget_PolymockOverload",
    "BestTarget_PolymockPiercingLightSpear",
    "BestTarget_PolymockPoisonedGround",
    "BestTarget_PolymockPowerDrain",
    "BestTarget_PolymockRodgortsInvocation",
    "BestTarget_PolymockRottingFlesh",
    "BestTarget_PolymockSandstorm",
    "BestTarget_PolymockSavannahHeat",
    "BestTarget_PolymockSearingFlames",
    "BestTarget_PolymockShockArrow",
    "BestTarget_PolymockSmite",
    "BestTarget_PolymockSmiteHex",
    "BestTarget_PolymockSpiritRift",
    "BestTarget_PolymockStoneDaggers",
    "BestTarget_PolymockStoning",
    "BestTarget_PowerBlock",
    "BestTarget_PowerDrain",
    "BestTarget_PowerLeak",
    "BestTarget_PowerLock",
    "BestTarget_PowerReturn",
    "BestTarget_PowerSpike",
    "BestTarget_PsychicDistraction",
    "BestTarget_PsychicInstability",
    "BestTarget_PsychicInstabilityPvp",
    "BestTarget_PurgeConditions",
    "BestTarget_PurifyEnergy",
    "BestTarget_PurifySoul",
    "BestTarget_PurifyingFlame",
    "BestTarget_PurifyingPrayer",
    "BestTarget_PutridExplosion",
    "BestTarget_PutridFlames",
    "BestTarget_PutridFlesh",
    "BestTarget_QuestSkill",
    "BestTarget_QuicksandEnvironmentEffect",
    "BestTarget_RainOfTerrorSpell",
    "BestTarget_RavenSwoop",
    "BestTarget_RavenSwoopAGateTooFar",
    "BestTarget_RavenousGaze",
    "BestTarget_RayOfJudgment",
    "BestTarget_ReactorBlast",
    "BestTarget_ReactorBurst",
    "BestTarget_Rebirth",
    "BestTarget_ReclaimEssence",
    "BestTarget_RedemptionOfPurity",
    "BestTarget_ReleaseEnchantments",
    "BestTarget_RemoveHex",
    "BestTarget_RendEnchantments",
    "BestTarget_RendingTouch",
    "BestTarget_RenewLife",
    "BestTarget_RestoreCondition",
    "BestTarget_RestoreLife",
    "BestTarget_Resurrect",
    "BestTarget_ResurrectGargoyle",
    "BestTarget_ResurrectionChant",
    "BestTarget_Return",
    "BestTarget_RevealedEnchantment",
    "BestTarget_RevealedHex",
    "BestTarget_ReversalOfDeath",
    "BestTarget_ReversePolarityFireShield",
    "BestTarget_RideTheLightning",
    "BestTarget_RideTheLightningPvp",
    "BestTarget_RipEnchantment",
    "BestTarget_RiseFromYourGrave",
    "BestTarget_RockSlide",
    "BestTarget_RocketPropelledGobstopper",
    "BestTarget_RodgortsInvocation",
    "BestTarget_RottingFlesh",
    "BestTarget_RuptureSoul",
    "BestTarget_RurikMustLive",
    "BestTarget_Sandstorm",
    "BestTarget_SarcophagusSpores",
    "BestTarget_SavannahHeat",
    "BestTarget_SavannahHeatPvp",
    "BestTarget_ScourgeOfCandy",
    "BestTarget_SearingFlames1",
    "BestTarget_SearingFlames2",
    "BestTarget_SearingHeat",
    "BestTarget_SecondWind",
    "BestTarget_ShadowStrike",
    "BestTarget_ShatterDelusions",
    "BestTarget_ShatterDelusionsPvp",
    "BestTarget_ShatterEnchantment",
    "BestTarget_ShatterHex",
    "BestTarget_ShatterStorm",
    "BestTarget_ShellShock",
    "BestTarget_ShieldOfSaintViktor",
    "BestTarget_ShieldOfSaintViktorCelestialSummoning",
    "BestTarget_ShieldingUrnSkill",
    "BestTarget_ShiverTouch",
    "BestTarget_ShockArrow",
    "BestTarget_Shockwave",
    "BestTarget_ShrineBacklash",
    "BestTarget_SimpleThievery",
    "BestTarget_SlipperyGround",
    "BestTarget_SlipperyGroundPvp",
    "BestTarget_Smite",
    "BestTarget_SmiteCondition",
    "BestTarget_SmiteCondition2",
    "BestTarget_SmiteHex",
    "BestTarget_SmoothCriminal",
    "BestTarget_SnowStorm",
    "BestTarget_Snowball",
    "BestTarget_Snowball2",
    "BestTarget_SnowballNpc",
    "BestTarget_SoothingMemories",
    "BestTarget_SorrowsFist",
    "BestTarget_SorrowsFlame",
    "BestTarget_SoulFeast",
    "BestTarget_SoulVortex",
    "BestTarget_SouthernHealthShrineBonus",
    "BestTarget_SpearOfArchemorusLevel1",
    "BestTarget_SpearOfArchemorusLevel2",
    "BestTarget_SpearOfArchemorusLevel3",
    "BestTarget_SpearOfArchemorusLevel4",
    "BestTarget_SpearOfArchemorusLevel5",
    "BestTarget_SpearOfLight",
    "BestTarget_SpikeTrapSpell",
    "BestTarget_SpiritBoonStrike",
    "BestTarget_SpiritBurn",
    "BestTarget_SpiritBurnTogo",
    "BestTarget_SpiritLight",
    "BestTarget_SpiritRift",
    "BestTarget_SpiritRiftTogo",
    "BestTarget_SpiritSiphon",
    "BestTarget_SpiritSiphonMasterRiyo",
    "BestTarget_SpiritToFlesh",
    "BestTarget_SpiritTransfer",
    "BestTarget_SpiritWalk",
    "BestTarget_SpiritualHealing",
    "BestTarget_SpiritualHealingReaperSkill",
    "BestTarget_SpiritualPain",
    "BestTarget_SpiritualPainPvp",
    "BestTarget_StarBurst",
    "BestTarget_StatuesBlessing",
    "BestTarget_Steam1",
    "BestTarget_Steam2",
    "BestTarget_StoneDaggers",
    "BestTarget_Stoning",
    "BestTarget_StopPump",
    "BestTarget_StormcallerSkill",
    "BestTarget_StripEnchantment",
    "BestTarget_StunGrenade",
    "BestTarget_SugarInfusion",
    "BestTarget_SummonChampion",
    "BestTarget_SummonIceImp",
    "BestTarget_SummonMinions",
    "BestTarget_SummonMursaat",
    "BestTarget_SummonNagaShaman",
    "BestTarget_SummonRubyDjinn",
    "BestTarget_SummonSpiritsKurzick",
    "BestTarget_SummonSpiritsLuxon",
    "BestTarget_SummonTorment",
    "BestTarget_SummoningOfTheScepter",
    "BestTarget_SunspearSiege",
    "BestTarget_SwampWater",
    "BestTarget_Swap",
    "BestTarget_SymbolOfWrath",
    "BestTarget_Tar",
    "BestTarget_TasteOfDeath",
    "BestTarget_TasteOfPain",
    "BestTarget_TasteOfUndeath",
    "BestTarget_TearGas",
    "BestTarget_Tease",
    "BestTarget_Technobabble",
    "BestTarget_TeinaisCrystals",
    "BestTarget_TeinaisWind",
    "BestTarget_TestOfFaith",
    "BestTarget_Thunderclap",
    "BestTarget_ToThePainHeroBattles",
    "BestTarget_ToxicChill",
    "BestTarget_TurretArrow",
    "BestTarget_UltraSnowball",
    "BestTarget_UltraSnowball2",
    "BestTarget_UltraSnowball3",
    "BestTarget_UltraSnowball4",
    "BestTarget_UltraSnowball5",
    "BestTarget_UnholyFeast",
    "BestTarget_UnholyFeastPvp",
    "BestTarget_UnsteadyGround",
    "BestTarget_UnyieldingAnguish",
    "BestTarget_UrnOfSaintViktorLevel1",
    "BestTarget_UrnOfSaintViktorLevel2",
    "BestTarget_UrnOfSaintViktorLevel3",
    "BestTarget_UrnOfSaintViktorLevel4",
    "BestTarget_UrnOfSaintViktorLevel5",
    "BestTarget_VampiricGaze",
    "BestTarget_VampiricSwarm",
    "BestTarget_Vanish",
    "BestTarget_VaporBlade",
    "BestTarget_VeratasGaze",
    "BestTarget_VeratasSacrifice",
    "BestTarget_VipersDefense",
    "BestTarget_Virulence",
    "BestTarget_WasteNotWantNot",
    "BestTarget_WaterTrident",
    "BestTarget_WaveOfTorment",
    "BestTarget_WeakenArmor",
    "BestTarget_WesternHealthShrineBonus",
    "BestTarget_Whirlwind",
    "BestTarget_WieldersBoon",
    "BestTarget_WieldersStrike",
    "BestTarget_WindsOfDisenchantment",
    "BestTarget_WithdrawHexes",
    "BestTarget_WordOfCensure",
    "BestTarget_WordOfHealing",
    "BestTarget_WordsOfComfort",
    "BestTarget_WurmSiege",
    "BestTarget_WurmSiegeDunesOfDespair",
    "BestTarget_WurmSiegeEyeOfTheNorth",
    "BestTarget_ZealousBenediction",
    "CanUse_AccumulatedPain",
    "CanUse_AccumulatedPainPvp",
    "CanUse_Adoration",
    "CanUse_Aftershock",
    "CanUse_AlkarsAlchemicalAcid",
    "CanUse_AltarBuff",
    "CanUse_Aneurysm",
    "CanUse_AngorodonsGaze",
    "CanUse_AnimateBoneFiend",
    "CanUse_AnimateBoneHorror",
    "CanUse_AnimateBoneMinions",
    "CanUse_AnimateCandyMinions",
    "CanUse_AnimateFleshGolem",
    "CanUse_AnimateShamblingHorror",
    "CanUse_AnimateUndead",
    "CanUse_AnimateUndeadPalawaJoko",
    "CanUse_AnimateVampiricHorror",
    "CanUse_AnnihilatorBeam",
    "CanUse_ArcLightning",
    "CanUse_ArcaneLarceny",
    "CanUse_ArcaneMimicry",
    "CanUse_ArcaneThievery",
    "CanUse_ArchemorusStrike",
    "CanUse_ArchemorusStrikeCelestialSummoning",
    "CanUse_ArgosCry",
    "CanUse_AvalancheEffect",
    "CanUse_AvalancheSkill",
    "CanUse_Banish",
    "CanUse_BanishEnchantment",
    "CanUse_BattleCry1",
    "CanUse_BattleCry2",
    "CanUse_BedOfCoals",
    "CanUse_BeguilingHaze",
    "CanUse_BitGolemBreaker",
    "CanUse_BitGolemCrash",
    "CanUse_BitGolemForce",
    "CanUse_BitterChill",
    "CanUse_BlastFurnace",
    "CanUse_BlessedLight",
    "CanUse_BlindingFlash",
    "CanUse_BlindingPowder",
    "CanUse_BlindingSnow",
    "CanUse_BlindingSurge",
    "CanUse_BlindingSurgePvp",
    "CanUse_Blizzard",
    "CanUse_BloodDrinker",
    "CanUse_BloodFlowerSkill",
    "CanUse_BloodOfTheAggressor",
    "CanUse_BloodOfTheMaster",
    "CanUse_BloodOfZuHeltzer",
    "CanUse_BreathOfFire",
    "CanUse_BreathOfTheGreatDwarf",
    "CanUse_BurningGround",
    "CanUse_Caltrops",
    "CanUse_CapturePoint",
    "CanUse_CaretakersCharge",
    "CanUse_CathedralCollapse2",
    "CanUse_CeilingCollapse",
    "CanUse_CelestialHaste",
    "CanUse_ChainLightning",
    "CanUse_ChainLightningEnvironment",
    "CanUse_ChanneledStrike",
    "CanUse_ChaosStorm",
    "CanUse_Chilblains",
    "CanUse_Chomper",
    "CanUse_ChurningEarth",
    "CanUse_ClamorOfSouls",
    "CanUse_ComingOfSpring",
    "CanUse_Complicate",
    "CanUse_ConsumeCorpse",
    "CanUse_ConsumeFlames",
    "CanUse_ConsumeSoul",
    "CanUse_ConvertHexes",
    "CanUse_CorruptedDragonScales",
    "CanUse_CorruptedDragonSpores",
    "CanUse_CorruptedHealing",
    "CanUse_CripplingDagger",
    "CanUse_CryOfFrustration",
    "CanUse_CryOfLament",
    "CanUse_CryOfPain",
    "CanUse_CrystalWave",
    "CanUse_CureHex",
    "CanUse_CurseOfDhuum",
    "CanUse_CurseOfTheBloodstone",
    "CanUse_DancingDaggers",
    "CanUse_DarkPact",
    "CanUse_DeathlyChill",
    "CanUse_DeathlySwarm",
    "CanUse_DeathsCharge",
    "CanUse_DeathsEmbrace",
    "CanUse_DeathsRetreat",
    "CanUse_DefileEnchantments",
    "CanUse_DenyHexes",
    "CanUse_DesecrateEnchantments",
    "CanUse_DhuumsRest",
    "CanUse_DhuumsRestReaperSkill",
    "CanUse_DiamondshardGrave",
    "CanUse_DiamondshardMist",
    "CanUse_DischargeEnchantment",
    "CanUse_Discord",
    "CanUse_DiscordPvp",
    "CanUse_DismissCondition",
    "CanUse_DisruptingDagger",
    "CanUse_DivertHexes",
    "CanUse_DivineHealing",
    "CanUse_DomainOfElements",
    "CanUse_DomainOfEnergyDraining",
    "CanUse_DomainOfHealthDraining",
    "CanUse_DomainOfSkillDamage",
    "CanUse_DomainOfSlow",
    "CanUse_Doom",
    "CanUse_DragonsStomp",
    "CanUse_DrainDelusions",
    "CanUse_DrainEnchantment",
    "CanUse_DrainMinion",
    "CanUse_DrawConditions",
    "CanUse_DrawSpirit",
    "CanUse_DrydersFeast",
    "CanUse_DwaynasKiss",
    "CanUse_DwaynasTouch",
    "CanUse_Earthquake",
    "CanUse_EasternHealthShrineBonus",
    "CanUse_EbonEscape",
    "CanUse_EbonHawk",
    "CanUse_EbonVanguardAssassinSupport",
    "CanUse_EbonVanguardAssassinSupportNpc",
    "CanUse_EbonVanguardSniperSupport",
    "CanUse_ElementalDefenseZone",
    "CanUse_EmpathicRemoval",
    "CanUse_EncaseSkeletal",
    "CanUse_EnergyBlast",
    "CanUse_EnergyBurn",
    "CanUse_EnergyDrain",
    "CanUse_EnergyDrainPvp",
    "CanUse_EnergyShrineBonus",
    "CanUse_EnergySurge",
    "CanUse_EnergyTap",
    "CanUse_EnergyTapPvp",
    "CanUse_EnervatingCharge",
    "CanUse_Enfeeble1",
    "CanUse_Enfeeble2",
    "CanUse_EnfeeblePvp",
    "CanUse_EnfeeblingBlood",
    "CanUse_EnfeeblingBloodPvp",
    "CanUse_EntanglingAsp",
    "CanUse_EnvenomEnchantments",
    "CanUse_Epidemic",
    "CanUse_Eruption",
    "CanUse_EruptionEnvironment",
    "CanUse_EssenceStrike",
    "CanUse_EssenceStrikeTogo",
    "CanUse_EtherFeast",
    "CanUse_EtherealLight",
    "CanUse_EverlastingMobstopperSkill",
    "CanUse_ExpelHexes",
    "CanUse_ExplodingBarrel",
    "CanUse_ExtendConditions",
    "CanUse_Extinguish",
    "CanUse_FakeSpell",
    "CanUse_FeastForTheDead",
    "CanUse_FeastOfCorruption",
    "CanUse_FeastOfSouls",
    "CanUse_FeastOfVengeance",
    "CanUse_Feedback",
    "CanUse_FetidGround",
    "CanUse_FilthyExplosion",
    "CanUse_FireAndBrimstone",
    "CanUse_FireDart",
    "CanUse_FireFlowerSkill",
    "CanUse_FireJet",
    "CanUse_FireSpout",
    "CanUse_FireStorm",
    "CanUse_FireStormEnvironment",
    "CanUse_Fireball",
    "CanUse_FireballObelisk",
    "CanUse_FlameBurst",
    "CanUse_Flare",
    "CanUse_FleshOfMyFlesh",
    "CanUse_FleshOfMyFleshPvp",
    "CanUse_FleshreaversEscape",
    "CanUse_FlurryOfIce",
    "CanUse_FoulFeast",
    "CanUse_FountOfMaguuma",
    "CanUse_FragmentationGrenade",
    "CanUse_FreezingGround",
    "CanUse_Gale",
    "CanUse_GazeFromBeyond",
    "CanUse_GazeOfContempt",
    "CanUse_GhostlyFury",
    "CanUse_GhostlyFuryReaperSkill",
    "CanUse_GhostmirrorLight",
    "CanUse_GiftOfHealth",
    "CanUse_GlimmerOfLight",
    "CanUse_GlowingGaze1",
    "CanUse_GlowingGaze2",
    "CanUse_GlowingIce",
    "CanUse_Glowstone",
    "CanUse_GolemFireShield",
    "CanUse_GolemPilebunker",
    "CanUse_GrenthsBalance",
    "CanUse_GuardianPacify",
    "CanUse_HealArea",
    "CanUse_HealOther",
    "CanUse_HealParty",
    "CanUse_HealPartyPvp",
    "CanUse_HealingBurst",
    "CanUse_HealingFountain",
    "CanUse_HealingLight",
    "CanUse_HealingRibbon",
    "CanUse_HealingRing",
    "CanUse_HealingTouch",
    "CanUse_HealingWhisper",
    "CanUse_HeartOfShadow",
    "CanUse_HeavensDelight",
    "CanUse_HexEaterVortex",
    "CanUse_HolidayBlues",
    "CanUse_Hypochondria",
    "CanUse_IceDart",
    "CanUse_IcyGround",
    "CanUse_IcyPrism",
    "CanUse_ImbueHealth",
    "CanUse_Immolate",
    "CanUse_Inferno",
    "CanUse_InfuseHealth",
    "CanUse_InspiredEnchantment",
    "CanUse_InspiredHex",
    "CanUse_InvokeLightning",
    "CanUse_JadeBrotherhoodBomb",
    "CanUse_JadeFury",
    "CanUse_JameisGaze",
    "CanUse_JanthirsGaze",
    "CanUse_JudgmentOfDhuum",
    "CanUse_KareisHealingCircle",
    "CanUse_KirinsWrath",
    "CanUse_KorosGaze",
    "CanUse_LavaArrows",
    "CanUse_LavaFont",
    "CanUse_LifebaneStrike",
    "CanUse_LightOfDeldrimor",
    "CanUse_LightOfDeliverance",
    "CanUse_LightOfDeliverancePvp",
    "CanUse_LightOfDwayna",
    "CanUse_LightningBolt",
    "CanUse_LightningHammer",
    "CanUse_LightningHammerPvp",
    "CanUse_LightningJavelin",
    "CanUse_LightningOrb1",
    "CanUse_LightningOrb2",
    "CanUse_LightningOrbPvp",
    "CanUse_LightningStorm",
    "CanUse_LiquidFlam2",
    "CanUse_LiquidFlame",
    "CanUse_LyssasBalance",
    "CanUse_MadKingPonySupport",
    "CanUse_Maelstrom",
    "CanUse_MaelstromEnvironment",
    "CanUse_MandragorsCharge",
    "CanUse_MantisTouch",
    "CanUse_Martyr",
    "CanUse_MasterOfNecromancy",
    "CanUse_MegaSnowball",
    "CanUse_MeleeDefenseZone",
    "CanUse_MendAilment",
    "CanUse_MendBodyAndSoul",
    "CanUse_MendBodyAndSoulTogo",
    "CanUse_MendCondition",
    "CanUse_MendingGrip",
    "CanUse_MendingShrineBonus",
    "CanUse_MendingTouch",
    "CanUse_Meteor",
    "CanUse_MeteorShower",
    "CanUse_Mimic",
    "CanUse_MindBlast",
    "CanUse_MindBurn",
    "CanUse_MindShock",
    "CanUse_MindShockPvp",
    "CanUse_MirrorOfDisenchantment",
    "CanUse_MirrorOfDisenchantmentPvp",
    "CanUse_MirrorShatter",
    "CanUse_MurakaisCalamity",
    "CanUse_MurakaisCall",
    "CanUse_MurakaisCensure",
    "CanUse_MurakaisConsumption",
    "CanUse_MurakaisStormOfSouls",
    "CanUse_MursaatTowerSkill",
    "CanUse_MysticHealing",
    "CanUse_MysticHealingPvp",
    "CanUse_MysticSandstorm",
    "CanUse_MysticTwister",
    "CanUse_NaturalHealing",
    "CanUse_NecroticTraversal",
    "CanUse_Nibble",
    "CanUse_NorthernHealthShrineBonus",
    "CanUse_NoxBeam",
    "CanUse_NoxDividerDrive",
    "CanUse_NoxFire",
    "CanUse_NoxKnuckle",
    "CanUse_NoxThunder",
    "CanUse_NoxionBuster",
    "CanUse_OathOfHealing",
    "CanUse_ObeliskLightning",
    "CanUse_ObsidianFlame",
    "CanUse_ObsidianFlamePvp",
    "CanUse_OfRoyalBlood",
    "CanUse_OfferingOfBlood",
    "CanUse_OfferingOfSpirit",
    "CanUse_OfferingOfSpiritTogo",
    "CanUse_OppressiveGaze",
    "CanUse_OrderOfTheLich",
    "CanUse_OrderOfTheLichPalawaJoko",
    "CanUse_OrderOfUndeath",
    "CanUse_OrderOfUnholyVigor",
    "CanUse_OrderOfUnholyVigorPalawaJoko",
    "CanUse_OrisonOfHealing",
    "CanUse_PainOfDisenchantment",
    "CanUse_PassageToTahnnakai",
    "CanUse_PhaseShield",
    "CanUse_PhasedPlasmaBurst",
    "CanUse_Phoenix",
    "CanUse_PiousRestoration",
    "CanUse_PlagueSending",
    "CanUse_PlasmaShot",
    "CanUse_PoisonArrowFlower",
    "CanUse_PoisonDart",
    "CanUse_PoisonGround",
    "CanUse_PoisonJet",
    "CanUse_PoisonSpout",
    "CanUse_PoisonedHeart",
    "CanUse_PolymockBanish",
    "CanUse_PolymockDeathlyChill",
    "CanUse_PolymockEarthquake",
    "CanUse_PolymockEruption",
    "CanUse_PolymockFireball",
    "CanUse_PolymockFlare",
    "CanUse_PolymockFrozenTrident",
    "CanUse_PolymockGlowingGaze",
    "CanUse_PolymockIceShardStorm",
    "CanUse_PolymockIceSpear",
    "CanUse_PolymockIcyPrison",
    "CanUse_PolymockImmolate",
    "CanUse_PolymockLamentation",
    "CanUse_PolymockLightningBlast",
    "CanUse_PolymockLightningOrb",
    "CanUse_PolymockLightningStrike",
    "CanUse_PolymockMeteor",
    "CanUse_PolymockMindBlast",
    "CanUse_PolymockMindFreeze",
    "CanUse_PolymockMindShock",
    "CanUse_PolymockObsidianFlame",
    "CanUse_PolymockOverload",
    "CanUse_PolymockPiercingLightSpear",
    "CanUse_PolymockPoisonedGround",
    "CanUse_PolymockPowerDrain",
    "CanUse_PolymockRodgortsInvocation",
    "CanUse_PolymockRottingFlesh",
    "CanUse_PolymockSandstorm",
    "CanUse_PolymockSavannahHeat",
    "CanUse_PolymockSearingFlames",
    "CanUse_PolymockShockArrow",
    "CanUse_PolymockSmite",
    "CanUse_PolymockSmiteHex",
    "CanUse_PolymockSpiritRift",
    "CanUse_PolymockStoneDaggers",
    "CanUse_PolymockStoning",
    "CanUse_PowerBlock",
    "CanUse_PowerDrain",
    "CanUse_PowerLeak",
    "CanUse_PowerLock",
    "CanUse_PowerReturn",
    "CanUse_PowerSpike",
    "CanUse_PsychicDistraction",
    "CanUse_PsychicInstability",
    "CanUse_PsychicInstabilityPvp",
    "CanUse_PurgeConditions",
    "CanUse_PurifyEnergy",
    "CanUse_PurifySoul",
    "CanUse_PurifyingFlame",
    "CanUse_PurifyingPrayer",
    "CanUse_PutridExplosion",
    "CanUse_PutridFlames",
    "CanUse_PutridFlesh",
    "CanUse_QuestSkill",
    "CanUse_QuicksandEnvironmentEffect",
    "CanUse_RainOfTerrorSpell",
    "CanUse_RavenSwoop",
    "CanUse_RavenSwoopAGateTooFar",
    "CanUse_RavenousGaze",
    "CanUse_RayOfJudgment",
    "CanUse_ReactorBlast",
    "CanUse_ReactorBurst",
    "CanUse_Rebirth",
    "CanUse_ReclaimEssence",
    "CanUse_RedemptionOfPurity",
    "CanUse_ReleaseEnchantments",
    "CanUse_RemoveHex",
    "CanUse_RendEnchantments",
    "CanUse_RendingTouch",
    "CanUse_RenewLife",
    "CanUse_RestoreCondition",
    "CanUse_RestoreLife",
    "CanUse_Resurrect",
    "CanUse_ResurrectGargoyle",
    "CanUse_ResurrectionChant",
    "CanUse_Return",
    "CanUse_RevealedEnchantment",
    "CanUse_RevealedHex",
    "CanUse_ReversalOfDeath",
    "CanUse_ReversePolarityFireShield",
    "CanUse_RideTheLightning",
    "CanUse_RideTheLightningPvp",
    "CanUse_RipEnchantment",
    "CanUse_RiseFromYourGrave",
    "CanUse_RockSlide",
    "CanUse_RocketPropelledGobstopper",
    "CanUse_RodgortsInvocation",
    "CanUse_RottingFlesh",
    "CanUse_RuptureSoul",
    "CanUse_RurikMustLive",
    "CanUse_Sandstorm",
    "CanUse_SarcophagusSpores",
    "CanUse_SavannahHeat",
    "CanUse_SavannahHeatPvp",
    "CanUse_ScourgeOfCandy",
    "CanUse_SearingFlames1",
    "CanUse_SearingFlames2",
    "CanUse_SearingHeat",
    "CanUse_SecondWind",
    "CanUse_ShadowStrike",
    "CanUse_ShatterDelusions",
    "CanUse_ShatterDelusionsPvp",
    "CanUse_ShatterEnchantment",
    "CanUse_ShatterHex",
    "CanUse_ShatterStorm",
    "CanUse_ShellShock",
    "CanUse_ShieldOfSaintViktor",
    "CanUse_ShieldOfSaintViktorCelestialSummoning",
    "CanUse_ShieldingUrnSkill",
    "CanUse_ShiverTouch",
    "CanUse_ShockArrow",
    "CanUse_Shockwave",
    "CanUse_ShrineBacklash",
    "CanUse_SimpleThievery",
    "CanUse_SlipperyGround",
    "CanUse_SlipperyGroundPvp",
    "CanUse_Smite",
    "CanUse_SmiteCondition",
    "CanUse_SmiteCondition2",
    "CanUse_SmiteHex",
    "CanUse_SmoothCriminal",
    "CanUse_SnowStorm",
    "CanUse_Snowball",
    "CanUse_Snowball2",
    "CanUse_SnowballNpc",
    "CanUse_SoothingMemories",
    "CanUse_SorrowsFist",
    "CanUse_SorrowsFlame",
    "CanUse_SoulFeast",
    "CanUse_SoulVortex",
    "CanUse_SouthernHealthShrineBonus",
    "CanUse_SpearOfArchemorusLevel1",
    "CanUse_SpearOfArchemorusLevel2",
    "CanUse_SpearOfArchemorusLevel3",
    "CanUse_SpearOfArchemorusLevel4",
    "CanUse_SpearOfArchemorusLevel5",
    "CanUse_SpearOfLight",
    "CanUse_SpikeTrapSpell",
    "CanUse_SpiritBoonStrike",
    "CanUse_SpiritBurn",
    "CanUse_SpiritBurnTogo",
    "CanUse_SpiritLight",
    "CanUse_SpiritRift",
    "CanUse_SpiritRiftTogo",
    "CanUse_SpiritSiphon",
    "CanUse_SpiritSiphonMasterRiyo",
    "CanUse_SpiritToFlesh",
    "CanUse_SpiritTransfer",
    "CanUse_SpiritWalk",
    "CanUse_SpiritualHealing",
    "CanUse_SpiritualHealingReaperSkill",
    "CanUse_SpiritualPain",
    "CanUse_SpiritualPainPvp",
    "CanUse_StarBurst",
    "CanUse_StatuesBlessing",
    "CanUse_Steam1",
    "CanUse_Steam2",
    "CanUse_StoneDaggers",
    "CanUse_Stoning",
    "CanUse_StopPump",
    "CanUse_StormcallerSkill",
    "CanUse_StripEnchantment",
    "CanUse_StunGrenade",
    "CanUse_SugarInfusion",
    "CanUse_SummonChampion",
    "CanUse_SummonIceImp",
    "CanUse_SummonMinions",
    "CanUse_SummonMursaat",
    "CanUse_SummonNagaShaman",
    "CanUse_SummonRubyDjinn",
    "CanUse_SummonSpiritsKurzick",
    "CanUse_SummonSpiritsLuxon",
    "CanUse_SummonTorment",
    "CanUse_SummoningOfTheScepter",
    "CanUse_SunspearSiege",
    "CanUse_SwampWater",
    "CanUse_Swap",
    "CanUse_SymbolOfWrath",
    "CanUse_Tar",
    "CanUse_TasteOfDeath",
    "CanUse_TasteOfPain",
    "CanUse_TasteOfUndeath",
    "CanUse_TearGas",
    "CanUse_Tease",
    "CanUse_Technobabble",
    "CanUse_TeinaisCrystals",
    "CanUse_TeinaisWind",
    "CanUse_TestOfFaith",
    "CanUse_Thunderclap",
    "CanUse_ToThePainHeroBattles",
    "CanUse_ToxicChill",
    "CanUse_TurretArrow",
    "CanUse_UltraSnowball",
    "CanUse_UltraSnowball2",
    "CanUse_UltraSnowball3",
    "CanUse_UltraSnowball4",
    "CanUse_UltraSnowball5",
    "CanUse_UnholyFeast",
    "CanUse_UnholyFeastPvp",
    "CanUse_UnsteadyGround",
    "CanUse_UnyieldingAnguish",
    "CanUse_UrnOfSaintViktorLevel1",
    "CanUse_UrnOfSaintViktorLevel2",
    "CanUse_UrnOfSaintViktorLevel3",
    "CanUse_UrnOfSaintViktorLevel4",
    "CanUse_UrnOfSaintViktorLevel5",
    "CanUse_VampiricGaze",
    "CanUse_VampiricSwarm",
    "CanUse_Vanish",
    "CanUse_VaporBlade",
    "CanUse_VeratasGaze",
    "CanUse_VeratasSacrifice",
    "CanUse_VipersDefense",
    "CanUse_Virulence",
    "CanUse_WasteNotWantNot",
    "CanUse_WaterTrident",
    "CanUse_WaveOfTorment",
    "CanUse_WeakenArmor",
    "CanUse_WesternHealthShrineBonus",
    "CanUse_Whirlwind",
    "CanUse_WieldersBoon",
    "CanUse_WieldersStrike",
    "CanUse_WindsOfDisenchantment",
    "CanUse_WithdrawHexes",
    "CanUse_WordOfCensure",
    "CanUse_WordOfHealing",
    "CanUse_WordsOfComfort",
    "CanUse_WurmSiege",
    "CanUse_WurmSiegeDunesOfDespair",
    "CanUse_WurmSiegeEyeOfTheNorth",
    "CanUse_ZealousBenediction",
]
