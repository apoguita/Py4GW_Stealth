"""GwAu3's ``UtilityAI_Attack.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **590 of this file's 590 are transcribed and 0
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
from .data_agent import Agent_GetCurrentTarget
from .uai_agent import (
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_dynamic_skill_cache import UAI_GetDynamicSkillInfo
from .uai_effects import (
    UAI_GetFeederEnchOnTop,
    UAI_PlayerHasEffect,
)
from .uai_filter import UAI_Filter_IsLastStrikeLeadOrOffHand
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestAOETarget,
    UAI_GetBestSingleTarget,
    UAI_GetNearestAgent,
)
from .uai_static_skill_cache import UAI_GetStaticSkillInfo


def CanUse_Hamstring() -> Any:
    """``UtilityAI_Attack.au3:26`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Hamstring(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:31`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WildBlow() -> Any:
    """``UtilityAI_Attack.au3:40`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WildBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:45`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PowerAttack() -> Any:
    """``UtilityAI_Attack.au3:54`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PowerAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:59`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DesperationBlow() -> Any:
    """``UtilityAI_Attack.au3:68`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DesperationBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:73`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ThrillOfVictory() -> Any:
    """``UtilityAI_Attack.au3:82`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ThrillOfVictory(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:87`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DistractingBlow() -> Any:
    """``UtilityAI_Attack.au3:96`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DistractingBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:101`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ProtectorsStrike() -> Any:
    """``UtilityAI_Attack.au3:110`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ProtectorsStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:115`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GriffonsSweep() -> Any:
    """``UtilityAI_Attack.au3:124`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GriffonsSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:129`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PureStrike() -> Any:
    """``UtilityAI_Attack.au3:138`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PureStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:143`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SkullCrack() -> Any:
    """``UtilityAI_Attack.au3:152`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SkullCrack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:157`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CycloneAxe() -> Any:
    """``UtilityAI_Attack.au3:166`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_CountAgents(uai_const.g_i_BestTarget, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy") < 2:
        return False
    return True


def BestTarget_CycloneAxe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:172`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HammerBash() -> Any:
    """``UtilityAI_Attack.au3:181`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HammerBash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:186`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BullsStrike() -> Any:
    """``UtilityAI_Attack.au3:195`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BullsStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:200`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AxeRake() -> Any:
    """``UtilityAI_Attack.au3:209`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AxeRake(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:214`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsDeepWounded")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Cleave() -> Any:
    """``UtilityAI_Attack.au3:225`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Cleave(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:230`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ExecutionersStrike() -> Any:
    """``UtilityAI_Attack.au3:239`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ExecutionersStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:244`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Dismember() -> Any:
    """``UtilityAI_Attack.au3:253`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Dismember(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:258`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Eviscerate() -> Any:
    """``UtilityAI_Attack.au3:267`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Eviscerate(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:272`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PenetratingBlow() -> Any:
    """``UtilityAI_Attack.au3:281`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PenetratingBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:286`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DisruptingChop() -> Any:
    """``UtilityAI_Attack.au3:295`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DisruptingChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:300`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SwiftChop() -> Any:
    """``UtilityAI_Attack.au3:309`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SwiftChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:314`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AxeTwist() -> Any:
    """``UtilityAI_Attack.au3:323`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AxeTwist(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:328`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsDeepWounded")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BellySmash() -> Any:
    """``UtilityAI_Attack.au3:339`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BellySmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:344`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MightyBlow() -> Any:
    """``UtilityAI_Attack.au3:355`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MightyBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:360`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CrushingBlow() -> Any:
    """``UtilityAI_Attack.au3:369`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CrushingBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:374`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CrudeSwing() -> Any:
    """``UtilityAI_Attack.au3:385`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CrudeSwing(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:390`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EarthShaker() -> Any:
    """``UtilityAI_Attack.au3:399`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EarthShaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:404`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DevastatingHammer() -> Any:
    """``UtilityAI_Attack.au3:413`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DevastatingHammer(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:418`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IrresistibleBlow() -> Any:
    """``UtilityAI_Attack.au3:427`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_IrresistibleBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:432`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CounterBlow() -> Any:
    """``UtilityAI_Attack.au3:441`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CounterBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:446`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Backbreaker() -> Any:
    """``UtilityAI_Attack.au3:457`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Backbreaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:462`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HeavyBlow() -> Any:
    """``UtilityAI_Attack.au3:471`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HeavyBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:476`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsWeakened")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StaggeringBlow() -> Any:
    """``UtilityAI_Attack.au3:487`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_StaggeringBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:492`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SeverArtery() -> Any:
    """``UtilityAI_Attack.au3:501`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SeverArtery(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:506`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GalrathSlash() -> Any:
    """``UtilityAI_Attack.au3:515`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GalrathSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:520`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Gash() -> Any:
    """``UtilityAI_Attack.au3:529`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Gash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:534`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBleeding")


def CanUse_FinalThrust() -> Any:
    """``UtilityAI_Attack.au3:543`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FinalThrust(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:548`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SeekingBlade() -> Any:
    """``UtilityAI_Attack.au3:557`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SeekingBlade(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:562`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SavageSlash() -> Any:
    """``UtilityAI_Attack.au3:571`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SavageSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:576`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HuntersShot() -> Any:
    """``UtilityAI_Attack.au3:585`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HuntersShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:590`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PinDown() -> Any:
    """``UtilityAI_Attack.au3:599`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PinDown(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:604`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingShot() -> Any:
    """``UtilityAI_Attack.au3:613`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CripplingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:618`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PowerShot() -> Any:
    """``UtilityAI_Attack.au3:627`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PowerShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:632`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Barrage() -> Any:
    """``UtilityAI_Attack.au3:641`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Barrage(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:646`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DualShot() -> Any:
    """``UtilityAI_Attack.au3:655`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DualShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:660`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_QuickShot() -> Any:
    """``UtilityAI_Attack.au3:669`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_QuickShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:674`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PenetratingAttack() -> Any:
    """``UtilityAI_Attack.au3:683`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PenetratingAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:688`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DistractingShot() -> Any:
    """``UtilityAI_Attack.au3:697`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DistractingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:702`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PrecisionShot() -> Any:
    """``UtilityAI_Attack.au3:711`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PrecisionShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:716`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DeterminedShot() -> Any:
    """``UtilityAI_Attack.au3:726`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DeterminedShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:731`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CalledShot() -> Any:
    """``UtilityAI_Attack.au3:740`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CalledShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:745`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PoisonArrow() -> Any:
    """``UtilityAI_Attack.au3:754`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PoisonArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:759`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_OathShot() -> Any:
    """``UtilityAI_Attack.au3:768`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_OathShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:773`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DebilitatingShot() -> Any:
    """``UtilityAI_Attack.au3:782`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DebilitatingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:787`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PointBlankShot() -> Any:
    """``UtilityAI_Attack.au3:796`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_CountAgents(uai_const.g_i_BestTarget, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy") < 1:
        return False
    return True


def BestTarget_PointBlankShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:803`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ConcussionShot() -> Any:
    """``UtilityAI_Attack.au3:812`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ConcussionShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:817`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PunishingShot() -> Any:
    """``UtilityAI_Attack.au3:826`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PunishingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:831`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SavageShot() -> Any:
    """``UtilityAI_Attack.au3:840`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SavageShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:845`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IncendiaryArrows() -> Any:
    """``UtilityAI_Attack.au3:854`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_IncendiaryArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:859`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeAttack4() -> Any:
    """``UtilityAI_Attack.au3:868`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SiegeAttack4(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:873`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BrutalMauling() -> Any:
    """``UtilityAI_Attack.au3:878`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BrutalMauling(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:883`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingAttack() -> Any:
    """``UtilityAI_Attack.au3:892`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CripplingAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:897`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DozenShot() -> Any:
    """``UtilityAI_Attack.au3:906`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DozenShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:911`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GiantStomp() -> Any:
    """``UtilityAI_Attack.au3:920`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GiantStomp(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:925`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AgnarsRage() -> Any:
    """``UtilityAI_Attack.au3:934`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AgnarsRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:939`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HungerOfTheLich() -> Any:
    """``UtilityAI_Attack.au3:944`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HungerOfTheLich(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:949`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeAttack1() -> Any:
    """``UtilityAI_Attack.au3:958`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SiegeAttack1(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:963`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SiegeAttack2() -> Any:
    """``UtilityAI_Attack.au3:968`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SiegeAttack2(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:973`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathBlossom() -> Any:
    """``UtilityAI_Attack.au3:978`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DeathBlossom(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:983`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_TwistingFangs() -> Any:
    """``UtilityAI_Attack.au3:992`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TwistingFangs(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:997`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_HornsOfTheOx() -> Any:
    """``UtilityAI_Attack.au3:1006`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HornsOfTheOx(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1011`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_FallingSpider() -> Any:
    """``UtilityAI_Attack.au3:1020`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FallingSpider(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1025`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")


def CanUse_BlackLotusStrike() -> Any:
    """``UtilityAI_Attack.au3:1034`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_BlackLotusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1041`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FoxFangs() -> Any:
    """``UtilityAI_Attack.au3:1052`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FoxFangs(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1057`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_MoebiusStrike() -> Any:
    """``UtilityAI_Attack.au3:1066`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MoebiusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1071`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsDual")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsDual")


def CanUse_JaggedStrike() -> Any:
    """``UtilityAI_Attack.au3:1082`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_JaggedStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1089`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UnsuspectingStrike() -> Any:
    """``UtilityAI_Attack.au3:1098`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_UnsuspectingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1105`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LaceratingChop() -> Any:
    """``UtilityAI_Attack.au3:1114`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_LaceratingChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1119`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FierceBlow() -> Any:
    """``UtilityAI_Attack.au3:1130`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FierceBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1135`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsWeakened")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SunAndMoonSlash() -> Any:
    """``UtilityAI_Attack.au3:1146`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SunAndMoonSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1151`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SplinterShot() -> Any:
    """``UtilityAI_Attack.au3:1160`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SplinterShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1165`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MelandrusShot() -> Any:
    """``UtilityAI_Attack.au3:1174`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MelandrusShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1179`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowsongAttack() -> Any:
    """``UtilityAI_Attack.au3:1188`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ShadowsongAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1193`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ConsumingFlames() -> Any:
    """``UtilityAI_Attack.au3:1202`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ConsumingFlames(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1207`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WhirlingAxe() -> Any:
    """``UtilityAI_Attack.au3:1216`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WhirlingAxe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1221`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ForcefulBlow() -> Any:
    """``UtilityAI_Attack.au3:1230`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ForcefulBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1235`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_QuiveringBlade() -> Any:
    """``UtilityAI_Attack.au3:1244`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_QuiveringBlade(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1249`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FuriousAxe() -> Any:
    """``UtilityAI_Attack.au3:1258`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FuriousAxe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1263`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AuspiciousBlow() -> Any:
    """``UtilityAI_Attack.au3:1272`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AuspiciousBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1277`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DragonSlash() -> Any:
    """``UtilityAI_Attack.au3:1286`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DragonSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1291`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MaraudersShot() -> Any:
    """``UtilityAI_Attack.au3:1300`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MaraudersShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1305`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FocusedShot() -> Any:
    """``UtilityAI_Attack.au3:1311`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FocusedShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1316`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DissonanceAttack() -> Any:
    """``UtilityAI_Attack.au3:1325`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DissonanceAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1330`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DisenchantmentAttack() -> Any:
    """``UtilityAI_Attack.au3:1336`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DisenchantmentAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1341`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DesperateStrike() -> Any:
    """``UtilityAI_Attack.au3:1347`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_DesperateStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1354`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ExhaustingAssault() -> Any:
    """``UtilityAI_Attack.au3:1363`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ExhaustingAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1368`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_RepeatingStrike() -> Any:
    """``UtilityAI_Attack.au3:1377`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RepeatingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1382`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_NineTailStrike() -> Any:
    """``UtilityAI_Attack.au3:1391`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_NineTailStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1396`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_TempleStrike() -> Any:
    """``UtilityAI_Attack.au3:1405`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TempleStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1410`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_GoldenPhoenixStrike() -> Any:
    """``UtilityAI_Attack.au3:1419`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsEnchanted):
        return False
    return True


def BestTarget_GoldenPhoenixStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1425`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TripleChop() -> Any:
    """``UtilityAI_Attack.au3:1434`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TripleChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1439`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnragedSmash() -> Any:
    """``UtilityAI_Attack.au3:1448`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EnragedSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1453`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RenewingSmash() -> Any:
    """``UtilityAI_Attack.au3:1462`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RenewingSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1467`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StandingSlash() -> Any:
    """``UtilityAI_Attack.au3:1476`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_StandingSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1481`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CriticalStrike() -> Any:
    """``UtilityAI_Attack.au3:1491`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CriticalStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1496`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_BladesOfSteel() -> Any:
    """``UtilityAI_Attack.au3:1506`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BladesOfSteel(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1511`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_JungleStrike() -> Any:
    """``UtilityAI_Attack.au3:1521`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_JungleStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1526`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_WildStrike() -> Any:
    """``UtilityAI_Attack.au3:1536`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WildStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1541`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_LeapingMantisSting() -> Any:
    """``UtilityAI_Attack.au3:1550`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_LeapingMantisSting(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1557`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BlackMantisThrust() -> Any:
    """``UtilityAI_Attack.au3:1567`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_BlackMantisThrust(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1574`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DisruptingStab() -> Any:
    """``UtilityAI_Attack.au3:1585`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_DisruptingStab(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1592`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GoldenLotusStrike() -> Any:
    """``UtilityAI_Attack.au3:1601`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_GoldenLotusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1608`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_DrunkenBlow() -> Any:
    """``UtilityAI_Attack.au3:1617`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DrunkenBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1622`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LeviathansSweep() -> Any:
    """``UtilityAI_Attack.au3:1631`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_LeviathansSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1636`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_JaizhenjuStrike() -> Any:
    """``UtilityAI_Attack.au3:1642`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_JaizhenjuStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1647`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PenetratingChop() -> Any:
    """``UtilityAI_Attack.au3:1656`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PenetratingChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1661`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_YetiSmash() -> Any:
    """``UtilityAI_Attack.au3:1670`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_YetiSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1675`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SilverwingSlash() -> Any:
    """``UtilityAI_Attack.au3:1684`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SilverwingSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1689`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DarkChainLightning() -> Any:
    """``UtilityAI_Attack.au3:1698`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DarkChainLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1703`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SunderingAttack() -> Any:
    """``UtilityAI_Attack.au3:1712`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SunderingAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1717`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ZojunsShot() -> Any:
    """``UtilityAI_Attack.au3:1726`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ZojunsShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1731`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_NeedlingShot() -> Any:
    """``UtilityAI_Attack.au3:1737`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_NeedlingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1742`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BroadHeadArrow() -> Any:
    """``UtilityAI_Attack.au3:1751`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BroadHeadArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1756`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttack() -> Any:
    """``UtilityAI_Attack.au3:1765`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1770`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BloodsongAttack() -> Any:
    """``UtilityAI_Attack.au3:1776`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BloodsongAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1781`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WanderlustAttack() -> Any:
    """``UtilityAI_Attack.au3:1787`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WanderlustAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1792`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SuicideEnergy() -> Any:
    """``UtilityAI_Attack.au3:1798`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SuicideEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1803`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SuicideHealth() -> Any:
    """``UtilityAI_Attack.au3:1812`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SuicideHealth(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1817`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeAttack3() -> Any:
    """``UtilityAI_Attack.au3:1827`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SiegeAttack3(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1832`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CriticalChop() -> Any:
    """``UtilityAI_Attack.au3:1837`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CriticalChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1842`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AgonizingChop() -> Any:
    """``UtilityAI_Attack.au3:1851`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AgonizingChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1856`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MokeleSmash() -> Any:
    """``UtilityAI_Attack.au3:1865`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MokeleSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1870`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_OverbearingSmash() -> Any:
    """``UtilityAI_Attack.au3:1879`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_OverbearingSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1884`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingSlash() -> Any:
    """``UtilityAI_Attack.au3:1893`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CripplingSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1898`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BarbarousSlice() -> Any:
    """``UtilityAI_Attack.au3:1907`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BarbarousSlice(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1912`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FeedingFrenzySkill() -> Any:
    """``UtilityAI_Attack.au3:1921`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FeedingFrenzySkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1926`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_QuakeOfAhdashim() -> Any:
    """``UtilityAI_Attack.au3:1932`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_QuakeOfAhdashim(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1937`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HungersBite() -> Any:
    """``UtilityAI_Attack.au3:1946`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HungersBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1951`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EarthVortex() -> Any:
    """``UtilityAI_Attack.au3:1957`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EarthVortex(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1962`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FrostVortex() -> Any:
    """``UtilityAI_Attack.au3:1971`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FrostVortex(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1976`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PreparedShot() -> Any:
    """``UtilityAI_Attack.au3:1985`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PreparedShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:1990`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BurningArrow() -> Any:
    """``UtilityAI_Attack.au3:1999`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BurningArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2004`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ArcingShot() -> Any:
    """``UtilityAI_Attack.au3:2013`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ArcingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2018`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Crossfire() -> Any:
    """``UtilityAI_Attack.au3:2027`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Crossfire(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2032`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BanishingStrike() -> Any:
    """``UtilityAI_Attack.au3:2041`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BanishingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2046`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MysticSweep() -> Any:
    """``UtilityAI_Attack.au3:2055`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsEnchanted):
        return False
    return True


def BestTarget_MysticSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2062`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_EremitesAttack() -> Any:
    """``UtilityAI_Attack.au3:2071`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    if UAI_CountAgents(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy") <= 1:
        return False
    return True


def BestTarget_EremitesAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2078`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ReapImpurities() -> Any:
    """``UtilityAI_Attack.au3:2083`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ReapImpurities(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2088`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TwinMoonSweep() -> Any:
    """``UtilityAI_Attack.au3:2097`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_TwinMoonSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2103`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VictoriousSweep() -> Any:
    """``UtilityAI_Attack.au3:2112`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_VictoriousSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2117`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IrresistibleSweep() -> Any:
    """``UtilityAI_Attack.au3:2126`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_IrresistibleSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2132`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PiousAssault() -> Any:
    """``UtilityAI_Attack.au3:2141`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_PiousAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2147`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingSweep() -> Any:
    """``UtilityAI_Attack.au3:2156`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CripplingSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2161`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WoundingStrike() -> Any:
    """``UtilityAI_Attack.au3:2170`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WoundingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2175`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WearyingStrike() -> Any:
    """``UtilityAI_Attack.au3:2184`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_WearyingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2190`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LyssasAssault() -> Any:
    """``UtilityAI_Attack.au3:2199`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_LyssasAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2204`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ChillingVictory() -> Any:
    """``UtilityAI_Attack.au3:2210`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ChillingVictory(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2215`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BlazingSpear() -> Any:
    """``UtilityAI_Attack.au3:2224`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BlazingSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2229`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MightyThrow() -> Any:
    """``UtilityAI_Attack.au3:2238`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MightyThrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2243`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CruelSpear() -> Any:
    """``UtilityAI_Attack.au3:2252`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CruelSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2257`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_HarriersToss() -> Any:
    """``UtilityAI_Attack.au3:2266`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HarriersToss(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2271`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UnblockableThrow() -> Any:
    """``UtilityAI_Attack.au3:2277`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_UnblockableThrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2282`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearOfLightning() -> Any:
    """``UtilityAI_Attack.au3:2291`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SpearOfLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2296`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WearyingSpear() -> Any:
    """``UtilityAI_Attack.au3:2305`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WearyingSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2310`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BarbedSpear() -> Any:
    """``UtilityAI_Attack.au3:2319`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BarbedSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2324`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentHighest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ViciousAttack() -> Any:
    """``UtilityAI_Attack.au3:2335`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ViciousAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2340`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StunningStrike() -> Any:
    """``UtilityAI_Attack.au3:2349`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_StunningStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2354`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MercilessSpear() -> Any:
    """``UtilityAI_Attack.au3:2363`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MercilessSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2368`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.5:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DisruptingThrow() -> Any:
    """``UtilityAI_Attack.au3:2379`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DisruptingThrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2384`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WildThrow() -> Any:
    """``UtilityAI_Attack.au3:2393`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WildThrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2398`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MaliciousStrike() -> Any:
    """``UtilityAI_Attack.au3:2407`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MaliciousStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2412`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShatteringAssault() -> Any:
    """``UtilityAI_Attack.au3:2421`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ShatteringAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2426`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_GoldenSkullStrike() -> Any:
    """``UtilityAI_Attack.au3:2435`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsEnchanted):
        return False
    return True


def BestTarget_GoldenSkullStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2441`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BlackSpiderStrike() -> Any:
    """``UtilityAI_Attack.au3:2450`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BlackSpiderStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2455`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")


def CanUse_GoldenFoxStrike() -> Any:
    """``UtilityAI_Attack.au3:2464`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_GoldenFoxStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2471`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeAttackBombardment() -> Any:
    """``UtilityAI_Attack.au3:2480`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SiegeAttackBombardment(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2485`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Counterattack() -> Any:
    """``UtilityAI_Attack.au3:2490`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Counterattack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2495`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MagehunterStrike() -> Any:
    """``UtilityAI_Attack.au3:2506`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MagehunterStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2511`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SoldiersStrike() -> Any:
    """``UtilityAI_Attack.au3:2522`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SoldiersStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2527`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Decapitate() -> Any:
    """``UtilityAI_Attack.au3:2533`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Decapitate(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2538`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MagehuntersSmash() -> Any:
    """``UtilityAI_Attack.au3:2547`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MagehuntersSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2552`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SteelfangSlash() -> Any:
    """``UtilityAI_Attack.au3:2558`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SteelfangSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2563`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EarthShatteringBlow() -> Any:
    """``UtilityAI_Attack.au3:2574`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EarthShatteringBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2579`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ScreamingShot() -> Any:
    """``UtilityAI_Attack.au3:2588`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ScreamingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2593`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KeenArrow() -> Any:
    """``UtilityAI_Attack.au3:2602`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KeenArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2607`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ForkedArrow() -> Any:
    """``UtilityAI_Attack.au3:2616`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ForkedArrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2621`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MagebaneShot() -> Any:
    """``UtilityAI_Attack.au3:2630`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MagebaneShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2635`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GazeOfFuryAttack() -> Any:
    """``UtilityAI_Attack.au3:2644`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GazeOfFuryAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2649`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnguishAttack() -> Any:
    """``UtilityAI_Attack.au3:2655`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AnguishAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2660`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RendingSweep() -> Any:
    """``UtilityAI_Attack.au3:2666`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_RendingSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2672`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ReapersSweep() -> Any:
    """``UtilityAI_Attack.au3:2681`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ReapersSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2686`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SlayersSpear() -> Any:
    """``UtilityAI_Attack.au3:2692`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SlayersSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2697`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SwiftJavelin() -> Any:
    """``UtilityAI_Attack.au3:2703`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SwiftJavelin(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2708`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WildSmash() -> Any:
    """``UtilityAI_Attack.au3:2717`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WildSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2722`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_JadothsStormOfJudgment() -> Any:
    """``UtilityAI_Attack.au3:2731`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_JadothsStormOfJudgment(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2736`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TorturousEmbers() -> Any:
    """``UtilityAI_Attack.au3:2742`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TorturousEmbers(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2747`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TripleShotLuxon() -> Any:
    """``UtilityAI_Attack.au3:2756`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TripleShotLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2761`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearOfFuryLuxon() -> Any:
    """``UtilityAI_Attack.au3:2767`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SpearOfFuryLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2772`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VampiricAssault() -> Any:
    """``UtilityAI_Attack.au3:2778`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_VampiricAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2783`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_LotusStrike() -> Any:
    """``UtilityAI_Attack.au3:2792`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_LotusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2797`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GoldenFangStrike() -> Any:
    """``UtilityAI_Attack.au3:2806`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GoldenFangStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2811`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_FallingLotusStrike() -> Any:
    """``UtilityAI_Attack.au3:2820`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FallingLotusStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2825`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")


def CanUse_PulverizingSmash() -> Any:
    """``UtilityAI_Attack.au3:2834`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PulverizingSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2839`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KeenChop() -> Any:
    """``UtilityAI_Attack.au3:2848`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KeenChop(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2853`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KneeCutter() -> Any:
    """``UtilityAI_Attack.au3:2862`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KneeCutter(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2867`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RadiantScythe() -> Any:
    """``UtilityAI_Attack.au3:2876`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RadiantScythe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2881`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FarmersScythe() -> Any:
    """``UtilityAI_Attack.au3:2890`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FarmersScythe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2895`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Disarm() -> Any:
    """``UtilityAI_Attack.au3:2901`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Disarm(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2906`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SlothHuntersShot() -> Any:
    """``UtilityAI_Attack.au3:2915`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SlothHuntersShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2920`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AuraSlicer() -> Any:
    """``UtilityAI_Attack.au3:2925`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AuraSlicer(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2930`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ZealousSweep() -> Any:
    """``UtilityAI_Attack.au3:2939`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ZealousSweep(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2944`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ChestThumper() -> Any:
    """``UtilityAI_Attack.au3:2953`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ChestThumper(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2958`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TripleShotKurzick() -> Any:
    """``UtilityAI_Attack.au3:2967`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TripleShotKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2972`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearOfFuryKurzick() -> Any:
    """``UtilityAI_Attack.au3:2978`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SpearOfFuryKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2983`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WhirlwindAttack() -> Any:
    """``UtilityAI_Attack.au3:2989`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WhirlwindAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:2994`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VampirismAttack() -> Any:
    """``UtilityAI_Attack.au3:3003`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_VampirismAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3008`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SneakAttack() -> Any:
    """``UtilityAI_Attack.au3:3014`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    l_i_CurrentTarget = Agent_GetCurrentTarget()
    if l_i_CurrentTarget != 0:
        return not UAI_Filter_IsLastStrikeLeadOrOffHand(l_i_CurrentTarget)
    return True


def BestTarget_SneakAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3021`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShatteredSpirit() -> Any:
    """``UtilityAI_Attack.au3:3030`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ShatteredSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3035`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnseenAggression() -> Any:
    """``UtilityAI_Attack.au3:3044`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_UnseenAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3049`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TramplingOx() -> Any:
    """``UtilityAI_Attack.au3:3058`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TramplingOx(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3063`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCrippled")


def CanUse_DisruptingShot() -> Any:
    """``UtilityAI_Attack.au3:3072`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DisruptingShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3077`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Volley() -> Any:
    """``UtilityAI_Attack.au3:3086`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Volley(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3091`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingVictory() -> Any:
    """``UtilityAI_Attack.au3:3100`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_CripplingVictory(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3105`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MaimingSpear() -> Any:
    """``UtilityAI_Attack.au3:3114`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MaimingSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3119`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GolemStrike() -> Any:
    """``UtilityAI_Attack.au3:3128`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GolemStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3133`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BloodstoneSlash() -> Any:
    """``UtilityAI_Attack.au3:3142`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BloodstoneSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3147`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RollingShift() -> Any:
    """``UtilityAI_Attack.au3:3158`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RollingShift(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3163`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DistractingStrike() -> Any:
    """``UtilityAI_Attack.au3:3172`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DistractingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3177`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SymbolicStrike() -> Any:
    """``UtilityAI_Attack.au3:3186`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SymbolicStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3191`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BodyBlow() -> Any:
    """``UtilityAI_Attack.au3:3200`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BodyBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3205`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BodyShot() -> Any:
    """``UtilityAI_Attack.au3:3214`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BodyShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3219`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HolySpear() -> Any:
    """``UtilityAI_Attack.au3:3228`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HolySpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3233`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearSwipe() -> Any:
    """``UtilityAI_Attack.au3:3242`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SpearSwipe(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3247`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DeftStrike() -> Any:
    """``UtilityAI_Attack.au3:3256`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DeftStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3261`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SpearOfRedemption() -> Any:
    """``UtilityAI_Attack.au3:3270`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SpearOfRedemption(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3275`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingJab1() -> Any:
    """``UtilityAI_Attack.au3:3285`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    if UAI_GetDynamicSkillInfo(3, _constants.GC_UAI_DYNAMIC_SKILL_IsRecharged):
        return False
    if UAI_GetDynamicSkillInfo(4, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(4, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    if UAI_GetDynamicSkillInfo(5, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(5, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    if UAI_GetDynamicSkillInfo(6, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(6, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    return True


def BestTarget_BrawlingJab1(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3295`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingJab2() -> Any:
    """``UtilityAI_Attack.au3:3307`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    if UAI_GetDynamicSkillInfo(3, _constants.GC_UAI_DYNAMIC_SKILL_IsRecharged):
        return False
    if UAI_GetDynamicSkillInfo(4, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(4, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    if UAI_GetDynamicSkillInfo(5, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(5, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    if UAI_GetDynamicSkillInfo(6, _constants.GC_UAI_DYNAMIC_SKILL_Adrenaline) >= UAI_GetStaticSkillInfo(6, _constants.GC_UAI_STATIC_SKILL_Adrenaline):
        return False
    return True


def BestTarget_BrawlingJab2(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3317`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingStraightRight() -> Any:
    """``UtilityAI_Attack.au3:3329`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingStraightRight(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3335`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingHook1() -> Any:
    """``UtilityAI_Attack.au3:3352`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingHook1(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3358`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingHook2() -> Any:
    """``UtilityAI_Attack.au3:3370`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingHook2(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3376`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingUppercut() -> Any:
    """``UtilityAI_Attack.au3:3388`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingUppercut(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3394`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingComboPunch() -> Any:
    """``UtilityAI_Attack.au3:3410`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingComboPunch(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3416`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingHeadbuttBrawlingSkill() -> Any:
    """``UtilityAI_Attack.au3:3432`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BRAWLING_BLOCK):
        return False
    return True


def BestTarget_BrawlingHeadbuttBrawlingSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3438`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetBestSingleTarget(-2, _constants.GC_I_RANGE_ADJACENT, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")
    if l_i_TargetID != 0:
        return l_i_TargetID
    l_i_TargetID = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsBoss")
    if l_i_TargetID != 0:
        return l_i_TargetID
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ClubOfAThousandBears() -> Any:
    """``UtilityAI_Attack.au3:3450`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ClubOfAThousandBears(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3455`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ThunderfistStrike() -> Any:
    """``UtilityAI_Attack.au3:3464`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ThunderfistStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3469`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ParasiticBite() -> Any:
    """``UtilityAI_Attack.au3:3478`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ParasiticBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3483`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TheSnipersSpear() -> Any:
    """``UtilityAI_Attack.au3:3492`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TheSnipersSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3497`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WhirlwindAttackTuraiOssa() -> Any:
    """``UtilityAI_Attack.au3:3507`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WhirlwindAttackTuraiOssa(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3512`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DragonSlashTuraiOssa() -> Any:
    """``UtilityAI_Attack.au3:3518`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DragonSlashTuraiOssa(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3523`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FalkensFireFist() -> Any:
    """``UtilityAI_Attack.au3:3529`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FalkensFireFist(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3534`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnragedSmashPvP() -> Any:
    """``UtilityAI_Attack.au3:3540`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EnragedSmashPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3545`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PenetratingAttackPvP() -> Any:
    """``UtilityAI_Attack.au3:3551`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PenetratingAttackPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3556`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SunderingAttackPvP() -> Any:
    """``UtilityAI_Attack.au3:3562`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SunderingAttackPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3567`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MysticSweepPvP() -> Any:
    """``UtilityAI_Attack.au3:3573`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_MysticSweepPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3578`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EremitesAttackPvP() -> Any:
    """``UtilityAI_Attack.au3:3584`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_EremitesAttackPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3589`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HarriersTossPvP() -> Any:
    """``UtilityAI_Attack.au3:3595`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_HarriersTossPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3600`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ChillingVictoryPvP() -> Any:
    """``UtilityAI_Attack.au3:3606`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ChillingVictoryPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3611`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SlothHuntersShotPvP() -> Any:
    """``UtilityAI_Attack.au3:3617`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_SlothHuntersShotPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3622`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackTogo1() -> Any:
    """``UtilityAI_Attack.au3:3632`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttackTogo1(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3637`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackTogo2() -> Any:
    """``UtilityAI_Attack.au3:3643`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttackTogo2(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3648`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackTogo3() -> Any:
    """``UtilityAI_Attack.au3:3654`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttackTogo3(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3659`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DeathBlossomPvP() -> Any:
    """``UtilityAI_Attack.au3:3665`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_DeathBlossomPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3670`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsOffHand")


def CanUse_BoneSpike() -> Any:
    """``UtilityAI_Attack.au3:3676`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BoneSpike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3681`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FlurryOfSplinters() -> Any:
    """``UtilityAI_Attack.au3:3690`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FlurryOfSplinters(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3695`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ReapingOfDhuum() -> Any:
    """``UtilityAI_Attack.au3:3704`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ReapingOfDhuum(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3709`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WeightOfDhuum() -> Any:
    """``UtilityAI_Attack.au3:3718`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WeightOfDhuum(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3723`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StaggeringBlowPvP() -> Any:
    """``UtilityAI_Attack.au3:3732`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_StaggeringBlowPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3737`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FierceBlowPvP() -> Any:
    """``UtilityAI_Attack.au3:3743`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FierceBlowPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3748`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RenewingSmashPvP() -> Any:
    """``UtilityAI_Attack.au3:3754`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RenewingSmashPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3759`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KeenArrowPvP() -> Any:
    """``UtilityAI_Attack.au3:3765`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KeenArrowPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3770`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackSignetOfSpirits1() -> Any:
    """``UtilityAI_Attack.au3:3776`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PainAttackSignetOfSpirits1(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3780`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackSignetOfSpirits2() -> Any:
    """``UtilityAI_Attack.au3:3786`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttackSignetOfSpirits2(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3791`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PainAttackSignetOfSpirits3() -> Any:
    """``UtilityAI_Attack.au3:3797`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PainAttackSignetOfSpirits3(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3802`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KeiransSniperShot() -> Any:
    """``UtilityAI_Attack.au3:3808`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KeiransSniperShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3813`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FalkenPunch() -> Any:
    """``UtilityAI_Attack.au3:3819`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FalkenPunch(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3824`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_KeiransSniperShotHeartsOfTheNorth() -> Any:
    """``UtilityAI_Attack.au3:3833`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_KeiransSniperShotHeartsOfTheNorth(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3838`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GravestoneMarker() -> Any:
    """``UtilityAI_Attack.au3:3844`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_GravestoneMarker(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3849`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsWeakened")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TerminalVelocity() -> Any:
    """``UtilityAI_Attack.au3:3860`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TerminalVelocity(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3865`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBleeding")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RelentlessAssault() -> Any:
    """``UtilityAI_Attack.au3:3876`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RelentlessAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3881`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WitheringBlade() -> Any:
    """``UtilityAI_Attack.au3:3890`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WitheringBlade(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3895`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VenomFang() -> Any:
    """``UtilityAI_Attack.au3:3904`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_VenomFang(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3909`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsDeepWounded")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RainOfArrows() -> Any:
    """``UtilityAI_Attack.au3:3920`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_RainOfArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3925`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_FoxFangsPvP() -> Any:
    """``UtilityAI_Attack.au3:3935`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_FoxFangsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3940`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_WildStrikePvP() -> Any:
    """``UtilityAI_Attack.au3:3946`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WildStrikePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3951`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsLead")


def CanUse_BanishingStrikePvP() -> Any:
    """``UtilityAI_Attack.au3:3957`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_BanishingStrikePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3962`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TwinMoonSweepPvP() -> Any:
    """``UtilityAI_Attack.au3:3968`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_TwinMoonSweepPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3973`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IrresistibleSweepPvP() -> Any:
    """``UtilityAI_Attack.au3:3979`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_IrresistibleSweepPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3984`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PiousAssaultPvP() -> Any:
    """``UtilityAI_Attack.au3:3990`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_PiousAssaultPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:3995`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ClubStrike() -> Any:
    """``UtilityAI_Attack.au3:4001`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_ClubStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4006`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_HasCondition")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Bludgeon() -> Any:
    """``UtilityAI_Attack.au3:4017`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_Bludgeon(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4022`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnnihilatorBash() -> Any:
    """``UtilityAI_Attack.au3:4033`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AnnihilatorBash(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4038`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WoundingStrikePvP() -> Any:
    """``UtilityAI_Attack.au3:4047`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_WoundingStrikePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4052`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnnihilatorStrike() -> Any:
    """``UtilityAI_Attack.au3:4058`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AnnihilatorStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4063`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AnnihilatorKnuckle() -> Any:
    """``UtilityAI_Attack.au3:4072`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_AnnihilatorKnuckle(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4077`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_JudgmentStrike() -> Any:
    """``UtilityAI_Attack.au3:4086`` -- transcribed from GwAu3's own body."""

    if Anti_Attack():
        return False
    return True


def BestTarget_JudgmentStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Attack.au3:4091`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


__all__ = [
    "BestTarget_AgnarsRage",
    "BestTarget_AgonizingChop",
    "BestTarget_AnguishAttack",
    "BestTarget_AnnihilatorBash",
    "BestTarget_AnnihilatorKnuckle",
    "BestTarget_AnnihilatorStrike",
    "BestTarget_ArcingShot",
    "BestTarget_AuraSlicer",
    "BestTarget_AuspiciousBlow",
    "BestTarget_AxeRake",
    "BestTarget_AxeTwist",
    "BestTarget_Backbreaker",
    "BestTarget_BanishingStrike",
    "BestTarget_BanishingStrikePvP",
    "BestTarget_BarbarousSlice",
    "BestTarget_BarbedSpear",
    "BestTarget_Barrage",
    "BestTarget_BellySmash",
    "BestTarget_BlackLotusStrike",
    "BestTarget_BlackMantisThrust",
    "BestTarget_BlackSpiderStrike",
    "BestTarget_BladesOfSteel",
    "BestTarget_BlazingSpear",
    "BestTarget_BloodsongAttack",
    "BestTarget_BloodstoneSlash",
    "BestTarget_Bludgeon",
    "BestTarget_BodyBlow",
    "BestTarget_BodyShot",
    "BestTarget_BoneSpike",
    "BestTarget_BrawlingComboPunch",
    "BestTarget_BrawlingHeadbuttBrawlingSkill",
    "BestTarget_BrawlingHook1",
    "BestTarget_BrawlingHook2",
    "BestTarget_BrawlingJab1",
    "BestTarget_BrawlingJab2",
    "BestTarget_BrawlingStraightRight",
    "BestTarget_BrawlingUppercut",
    "BestTarget_BroadHeadArrow",
    "BestTarget_BrutalMauling",
    "BestTarget_BullsStrike",
    "BestTarget_BurningArrow",
    "BestTarget_CalledShot",
    "BestTarget_ChestThumper",
    "BestTarget_ChillingVictory",
    "BestTarget_ChillingVictoryPvP",
    "BestTarget_Cleave",
    "BestTarget_ClubOfAThousandBears",
    "BestTarget_ClubStrike",
    "BestTarget_ConcussionShot",
    "BestTarget_ConsumingFlames",
    "BestTarget_CounterBlow",
    "BestTarget_Counterattack",
    "BestTarget_CripplingAttack",
    "BestTarget_CripplingShot",
    "BestTarget_CripplingSlash",
    "BestTarget_CripplingSweep",
    "BestTarget_CripplingVictory",
    "BestTarget_CriticalChop",
    "BestTarget_CriticalStrike",
    "BestTarget_Crossfire",
    "BestTarget_CrudeSwing",
    "BestTarget_CruelSpear",
    "BestTarget_CrushingBlow",
    "BestTarget_CycloneAxe",
    "BestTarget_DarkChainLightning",
    "BestTarget_DeathBlossom",
    "BestTarget_DeathBlossomPvP",
    "BestTarget_DebilitatingShot",
    "BestTarget_Decapitate",
    "BestTarget_DeftStrike",
    "BestTarget_DesperateStrike",
    "BestTarget_DesperationBlow",
    "BestTarget_DeterminedShot",
    "BestTarget_DevastatingHammer",
    "BestTarget_Disarm",
    "BestTarget_DisenchantmentAttack",
    "BestTarget_Dismember",
    "BestTarget_DisruptingChop",
    "BestTarget_DisruptingShot",
    "BestTarget_DisruptingStab",
    "BestTarget_DisruptingThrow",
    "BestTarget_DissonanceAttack",
    "BestTarget_DistractingBlow",
    "BestTarget_DistractingShot",
    "BestTarget_DistractingStrike",
    "BestTarget_DozenShot",
    "BestTarget_DragonSlash",
    "BestTarget_DragonSlashTuraiOssa",
    "BestTarget_DrunkenBlow",
    "BestTarget_DualShot",
    "BestTarget_EarthShaker",
    "BestTarget_EarthShatteringBlow",
    "BestTarget_EarthVortex",
    "BestTarget_EnragedSmash",
    "BestTarget_EnragedSmashPvP",
    "BestTarget_EremitesAttack",
    "BestTarget_EremitesAttackPvP",
    "BestTarget_Eviscerate",
    "BestTarget_ExecutionersStrike",
    "BestTarget_ExhaustingAssault",
    "BestTarget_FalkenPunch",
    "BestTarget_FalkensFireFist",
    "BestTarget_FallingLotusStrike",
    "BestTarget_FallingSpider",
    "BestTarget_FarmersScythe",
    "BestTarget_FeedingFrenzySkill",
    "BestTarget_FierceBlow",
    "BestTarget_FierceBlowPvP",
    "BestTarget_FinalThrust",
    "BestTarget_FlurryOfSplinters",
    "BestTarget_FocusedShot",
    "BestTarget_ForcefulBlow",
    "BestTarget_ForkedArrow",
    "BestTarget_FoxFangs",
    "BestTarget_FoxFangsPvP",
    "BestTarget_FrostVortex",
    "BestTarget_FuriousAxe",
    "BestTarget_GalrathSlash",
    "BestTarget_Gash",
    "BestTarget_GazeOfFuryAttack",
    "BestTarget_GiantStomp",
    "BestTarget_GoldenFangStrike",
    "BestTarget_GoldenFoxStrike",
    "BestTarget_GoldenLotusStrike",
    "BestTarget_GoldenPhoenixStrike",
    "BestTarget_GoldenSkullStrike",
    "BestTarget_GolemStrike",
    "BestTarget_GravestoneMarker",
    "BestTarget_GriffonsSweep",
    "BestTarget_HammerBash",
    "BestTarget_Hamstring",
    "BestTarget_HarriersToss",
    "BestTarget_HarriersTossPvP",
    "BestTarget_HeavyBlow",
    "BestTarget_HolySpear",
    "BestTarget_HornsOfTheOx",
    "BestTarget_HungerOfTheLich",
    "BestTarget_HungersBite",
    "BestTarget_HuntersShot",
    "BestTarget_IncendiaryArrows",
    "BestTarget_IrresistibleBlow",
    "BestTarget_IrresistibleSweep",
    "BestTarget_IrresistibleSweepPvP",
    "BestTarget_JadothsStormOfJudgment",
    "BestTarget_JaggedStrike",
    "BestTarget_JaizhenjuStrike",
    "BestTarget_JudgmentStrike",
    "BestTarget_JungleStrike",
    "BestTarget_KeenArrow",
    "BestTarget_KeenArrowPvP",
    "BestTarget_KeenChop",
    "BestTarget_KeiransSniperShot",
    "BestTarget_KeiransSniperShotHeartsOfTheNorth",
    "BestTarget_KneeCutter",
    "BestTarget_LaceratingChop",
    "BestTarget_LeapingMantisSting",
    "BestTarget_LeviathansSweep",
    "BestTarget_LotusStrike",
    "BestTarget_LyssasAssault",
    "BestTarget_MagebaneShot",
    "BestTarget_MagehunterStrike",
    "BestTarget_MagehuntersSmash",
    "BestTarget_MaimingSpear",
    "BestTarget_MaliciousStrike",
    "BestTarget_MaraudersShot",
    "BestTarget_MelandrusShot",
    "BestTarget_MercilessSpear",
    "BestTarget_MightyBlow",
    "BestTarget_MightyThrow",
    "BestTarget_MoebiusStrike",
    "BestTarget_MokeleSmash",
    "BestTarget_MysticSweep",
    "BestTarget_MysticSweepPvP",
    "BestTarget_NeedlingShot",
    "BestTarget_NineTailStrike",
    "BestTarget_OathShot",
    "BestTarget_OverbearingSmash",
    "BestTarget_PainAttack",
    "BestTarget_PainAttackSignetOfSpirits1",
    "BestTarget_PainAttackSignetOfSpirits2",
    "BestTarget_PainAttackSignetOfSpirits3",
    "BestTarget_PainAttackTogo1",
    "BestTarget_PainAttackTogo2",
    "BestTarget_PainAttackTogo3",
    "BestTarget_ParasiticBite",
    "BestTarget_PenetratingAttack",
    "BestTarget_PenetratingAttackPvP",
    "BestTarget_PenetratingBlow",
    "BestTarget_PenetratingChop",
    "BestTarget_PinDown",
    "BestTarget_PiousAssault",
    "BestTarget_PiousAssaultPvP",
    "BestTarget_PointBlankShot",
    "BestTarget_PoisonArrow",
    "BestTarget_PowerAttack",
    "BestTarget_PowerShot",
    "BestTarget_PrecisionShot",
    "BestTarget_PreparedShot",
    "BestTarget_ProtectorsStrike",
    "BestTarget_PulverizingSmash",
    "BestTarget_PunishingShot",
    "BestTarget_PureStrike",
    "BestTarget_QuakeOfAhdashim",
    "BestTarget_QuickShot",
    "BestTarget_QuiveringBlade",
    "BestTarget_RadiantScythe",
    "BestTarget_RainOfArrows",
    "BestTarget_ReapImpurities",
    "BestTarget_ReapersSweep",
    "BestTarget_ReapingOfDhuum",
    "BestTarget_RelentlessAssault",
    "BestTarget_RendingSweep",
    "BestTarget_RenewingSmash",
    "BestTarget_RenewingSmashPvP",
    "BestTarget_RepeatingStrike",
    "BestTarget_RollingShift",
    "BestTarget_SavageShot",
    "BestTarget_SavageSlash",
    "BestTarget_ScreamingShot",
    "BestTarget_SeekingBlade",
    "BestTarget_SeverArtery",
    "BestTarget_ShadowsongAttack",
    "BestTarget_ShatteredSpirit",
    "BestTarget_ShatteringAssault",
    "BestTarget_SiegeAttack1",
    "BestTarget_SiegeAttack2",
    "BestTarget_SiegeAttack3",
    "BestTarget_SiegeAttack4",
    "BestTarget_SiegeAttackBombardment",
    "BestTarget_SilverwingSlash",
    "BestTarget_SkullCrack",
    "BestTarget_SlayersSpear",
    "BestTarget_SlothHuntersShot",
    "BestTarget_SlothHuntersShotPvP",
    "BestTarget_SneakAttack",
    "BestTarget_SoldiersStrike",
    "BestTarget_SpearOfFuryKurzick",
    "BestTarget_SpearOfFuryLuxon",
    "BestTarget_SpearOfLightning",
    "BestTarget_SpearOfRedemption",
    "BestTarget_SpearSwipe",
    "BestTarget_SplinterShot",
    "BestTarget_StaggeringBlow",
    "BestTarget_StaggeringBlowPvP",
    "BestTarget_StandingSlash",
    "BestTarget_SteelfangSlash",
    "BestTarget_StunningStrike",
    "BestTarget_SuicideEnergy",
    "BestTarget_SuicideHealth",
    "BestTarget_SunAndMoonSlash",
    "BestTarget_SunderingAttack",
    "BestTarget_SunderingAttackPvP",
    "BestTarget_SwiftChop",
    "BestTarget_SwiftJavelin",
    "BestTarget_SymbolicStrike",
    "BestTarget_TempleStrike",
    "BestTarget_TerminalVelocity",
    "BestTarget_TheSnipersSpear",
    "BestTarget_ThrillOfVictory",
    "BestTarget_ThunderfistStrike",
    "BestTarget_TorturousEmbers",
    "BestTarget_TramplingOx",
    "BestTarget_TripleChop",
    "BestTarget_TripleShotKurzick",
    "BestTarget_TripleShotLuxon",
    "BestTarget_TwinMoonSweep",
    "BestTarget_TwinMoonSweepPvP",
    "BestTarget_TwistingFangs",
    "BestTarget_UnblockableThrow",
    "BestTarget_UnseenAggression",
    "BestTarget_UnsuspectingStrike",
    "BestTarget_VampiricAssault",
    "BestTarget_VampirismAttack",
    "BestTarget_VenomFang",
    "BestTarget_ViciousAttack",
    "BestTarget_VictoriousSweep",
    "BestTarget_Volley",
    "BestTarget_WanderlustAttack",
    "BestTarget_WearyingSpear",
    "BestTarget_WearyingStrike",
    "BestTarget_WeightOfDhuum",
    "BestTarget_WhirlingAxe",
    "BestTarget_WhirlwindAttack",
    "BestTarget_WhirlwindAttackTuraiOssa",
    "BestTarget_WildBlow",
    "BestTarget_WildSmash",
    "BestTarget_WildStrike",
    "BestTarget_WildStrikePvP",
    "BestTarget_WildThrow",
    "BestTarget_WitheringBlade",
    "BestTarget_WoundingStrike",
    "BestTarget_WoundingStrikePvP",
    "BestTarget_YetiSmash",
    "BestTarget_ZealousSweep",
    "BestTarget_ZojunsShot",
    "CanUse_AgnarsRage",
    "CanUse_AgonizingChop",
    "CanUse_AnguishAttack",
    "CanUse_AnnihilatorBash",
    "CanUse_AnnihilatorKnuckle",
    "CanUse_AnnihilatorStrike",
    "CanUse_ArcingShot",
    "CanUse_AuraSlicer",
    "CanUse_AuspiciousBlow",
    "CanUse_AxeRake",
    "CanUse_AxeTwist",
    "CanUse_Backbreaker",
    "CanUse_BanishingStrike",
    "CanUse_BanishingStrikePvP",
    "CanUse_BarbarousSlice",
    "CanUse_BarbedSpear",
    "CanUse_Barrage",
    "CanUse_BellySmash",
    "CanUse_BlackLotusStrike",
    "CanUse_BlackMantisThrust",
    "CanUse_BlackSpiderStrike",
    "CanUse_BladesOfSteel",
    "CanUse_BlazingSpear",
    "CanUse_BloodsongAttack",
    "CanUse_BloodstoneSlash",
    "CanUse_Bludgeon",
    "CanUse_BodyBlow",
    "CanUse_BodyShot",
    "CanUse_BoneSpike",
    "CanUse_BrawlingComboPunch",
    "CanUse_BrawlingHeadbuttBrawlingSkill",
    "CanUse_BrawlingHook1",
    "CanUse_BrawlingHook2",
    "CanUse_BrawlingJab1",
    "CanUse_BrawlingJab2",
    "CanUse_BrawlingStraightRight",
    "CanUse_BrawlingUppercut",
    "CanUse_BroadHeadArrow",
    "CanUse_BrutalMauling",
    "CanUse_BullsStrike",
    "CanUse_BurningArrow",
    "CanUse_CalledShot",
    "CanUse_ChestThumper",
    "CanUse_ChillingVictory",
    "CanUse_ChillingVictoryPvP",
    "CanUse_Cleave",
    "CanUse_ClubOfAThousandBears",
    "CanUse_ClubStrike",
    "CanUse_ConcussionShot",
    "CanUse_ConsumingFlames",
    "CanUse_CounterBlow",
    "CanUse_Counterattack",
    "CanUse_CripplingAttack",
    "CanUse_CripplingShot",
    "CanUse_CripplingSlash",
    "CanUse_CripplingSweep",
    "CanUse_CripplingVictory",
    "CanUse_CriticalChop",
    "CanUse_CriticalStrike",
    "CanUse_Crossfire",
    "CanUse_CrudeSwing",
    "CanUse_CruelSpear",
    "CanUse_CrushingBlow",
    "CanUse_CycloneAxe",
    "CanUse_DarkChainLightning",
    "CanUse_DeathBlossom",
    "CanUse_DeathBlossomPvP",
    "CanUse_DebilitatingShot",
    "CanUse_Decapitate",
    "CanUse_DeftStrike",
    "CanUse_DesperateStrike",
    "CanUse_DesperationBlow",
    "CanUse_DeterminedShot",
    "CanUse_DevastatingHammer",
    "CanUse_Disarm",
    "CanUse_DisenchantmentAttack",
    "CanUse_Dismember",
    "CanUse_DisruptingChop",
    "CanUse_DisruptingShot",
    "CanUse_DisruptingStab",
    "CanUse_DisruptingThrow",
    "CanUse_DissonanceAttack",
    "CanUse_DistractingBlow",
    "CanUse_DistractingShot",
    "CanUse_DistractingStrike",
    "CanUse_DozenShot",
    "CanUse_DragonSlash",
    "CanUse_DragonSlashTuraiOssa",
    "CanUse_DrunkenBlow",
    "CanUse_DualShot",
    "CanUse_EarthShaker",
    "CanUse_EarthShatteringBlow",
    "CanUse_EarthVortex",
    "CanUse_EnragedSmash",
    "CanUse_EnragedSmashPvP",
    "CanUse_EremitesAttack",
    "CanUse_EremitesAttackPvP",
    "CanUse_Eviscerate",
    "CanUse_ExecutionersStrike",
    "CanUse_ExhaustingAssault",
    "CanUse_FalkenPunch",
    "CanUse_FalkensFireFist",
    "CanUse_FallingLotusStrike",
    "CanUse_FallingSpider",
    "CanUse_FarmersScythe",
    "CanUse_FeedingFrenzySkill",
    "CanUse_FierceBlow",
    "CanUse_FierceBlowPvP",
    "CanUse_FinalThrust",
    "CanUse_FlurryOfSplinters",
    "CanUse_FocusedShot",
    "CanUse_ForcefulBlow",
    "CanUse_ForkedArrow",
    "CanUse_FoxFangs",
    "CanUse_FoxFangsPvP",
    "CanUse_FrostVortex",
    "CanUse_FuriousAxe",
    "CanUse_GalrathSlash",
    "CanUse_Gash",
    "CanUse_GazeOfFuryAttack",
    "CanUse_GiantStomp",
    "CanUse_GoldenFangStrike",
    "CanUse_GoldenFoxStrike",
    "CanUse_GoldenLotusStrike",
    "CanUse_GoldenPhoenixStrike",
    "CanUse_GoldenSkullStrike",
    "CanUse_GolemStrike",
    "CanUse_GravestoneMarker",
    "CanUse_GriffonsSweep",
    "CanUse_HammerBash",
    "CanUse_Hamstring",
    "CanUse_HarriersToss",
    "CanUse_HarriersTossPvP",
    "CanUse_HeavyBlow",
    "CanUse_HolySpear",
    "CanUse_HornsOfTheOx",
    "CanUse_HungerOfTheLich",
    "CanUse_HungersBite",
    "CanUse_HuntersShot",
    "CanUse_IncendiaryArrows",
    "CanUse_IrresistibleBlow",
    "CanUse_IrresistibleSweep",
    "CanUse_IrresistibleSweepPvP",
    "CanUse_JadothsStormOfJudgment",
    "CanUse_JaggedStrike",
    "CanUse_JaizhenjuStrike",
    "CanUse_JudgmentStrike",
    "CanUse_JungleStrike",
    "CanUse_KeenArrow",
    "CanUse_KeenArrowPvP",
    "CanUse_KeenChop",
    "CanUse_KeiransSniperShot",
    "CanUse_KeiransSniperShotHeartsOfTheNorth",
    "CanUse_KneeCutter",
    "CanUse_LaceratingChop",
    "CanUse_LeapingMantisSting",
    "CanUse_LeviathansSweep",
    "CanUse_LotusStrike",
    "CanUse_LyssasAssault",
    "CanUse_MagebaneShot",
    "CanUse_MagehunterStrike",
    "CanUse_MagehuntersSmash",
    "CanUse_MaimingSpear",
    "CanUse_MaliciousStrike",
    "CanUse_MaraudersShot",
    "CanUse_MelandrusShot",
    "CanUse_MercilessSpear",
    "CanUse_MightyBlow",
    "CanUse_MightyThrow",
    "CanUse_MoebiusStrike",
    "CanUse_MokeleSmash",
    "CanUse_MysticSweep",
    "CanUse_MysticSweepPvP",
    "CanUse_NeedlingShot",
    "CanUse_NineTailStrike",
    "CanUse_OathShot",
    "CanUse_OverbearingSmash",
    "CanUse_PainAttack",
    "CanUse_PainAttackSignetOfSpirits1",
    "CanUse_PainAttackSignetOfSpirits2",
    "CanUse_PainAttackSignetOfSpirits3",
    "CanUse_PainAttackTogo1",
    "CanUse_PainAttackTogo2",
    "CanUse_PainAttackTogo3",
    "CanUse_ParasiticBite",
    "CanUse_PenetratingAttack",
    "CanUse_PenetratingAttackPvP",
    "CanUse_PenetratingBlow",
    "CanUse_PenetratingChop",
    "CanUse_PinDown",
    "CanUse_PiousAssault",
    "CanUse_PiousAssaultPvP",
    "CanUse_PointBlankShot",
    "CanUse_PoisonArrow",
    "CanUse_PowerAttack",
    "CanUse_PowerShot",
    "CanUse_PrecisionShot",
    "CanUse_PreparedShot",
    "CanUse_ProtectorsStrike",
    "CanUse_PulverizingSmash",
    "CanUse_PunishingShot",
    "CanUse_PureStrike",
    "CanUse_QuakeOfAhdashim",
    "CanUse_QuickShot",
    "CanUse_QuiveringBlade",
    "CanUse_RadiantScythe",
    "CanUse_RainOfArrows",
    "CanUse_ReapImpurities",
    "CanUse_ReapersSweep",
    "CanUse_ReapingOfDhuum",
    "CanUse_RelentlessAssault",
    "CanUse_RendingSweep",
    "CanUse_RenewingSmash",
    "CanUse_RenewingSmashPvP",
    "CanUse_RepeatingStrike",
    "CanUse_RollingShift",
    "CanUse_SavageShot",
    "CanUse_SavageSlash",
    "CanUse_ScreamingShot",
    "CanUse_SeekingBlade",
    "CanUse_SeverArtery",
    "CanUse_ShadowsongAttack",
    "CanUse_ShatteredSpirit",
    "CanUse_ShatteringAssault",
    "CanUse_SiegeAttack1",
    "CanUse_SiegeAttack2",
    "CanUse_SiegeAttack3",
    "CanUse_SiegeAttack4",
    "CanUse_SiegeAttackBombardment",
    "CanUse_SilverwingSlash",
    "CanUse_SkullCrack",
    "CanUse_SlayersSpear",
    "CanUse_SlothHuntersShot",
    "CanUse_SlothHuntersShotPvP",
    "CanUse_SneakAttack",
    "CanUse_SoldiersStrike",
    "CanUse_SpearOfFuryKurzick",
    "CanUse_SpearOfFuryLuxon",
    "CanUse_SpearOfLightning",
    "CanUse_SpearOfRedemption",
    "CanUse_SpearSwipe",
    "CanUse_SplinterShot",
    "CanUse_StaggeringBlow",
    "CanUse_StaggeringBlowPvP",
    "CanUse_StandingSlash",
    "CanUse_SteelfangSlash",
    "CanUse_StunningStrike",
    "CanUse_SuicideEnergy",
    "CanUse_SuicideHealth",
    "CanUse_SunAndMoonSlash",
    "CanUse_SunderingAttack",
    "CanUse_SunderingAttackPvP",
    "CanUse_SwiftChop",
    "CanUse_SwiftJavelin",
    "CanUse_SymbolicStrike",
    "CanUse_TempleStrike",
    "CanUse_TerminalVelocity",
    "CanUse_TheSnipersSpear",
    "CanUse_ThrillOfVictory",
    "CanUse_ThunderfistStrike",
    "CanUse_TorturousEmbers",
    "CanUse_TramplingOx",
    "CanUse_TripleChop",
    "CanUse_TripleShotKurzick",
    "CanUse_TripleShotLuxon",
    "CanUse_TwinMoonSweep",
    "CanUse_TwinMoonSweepPvP",
    "CanUse_TwistingFangs",
    "CanUse_UnblockableThrow",
    "CanUse_UnseenAggression",
    "CanUse_UnsuspectingStrike",
    "CanUse_VampiricAssault",
    "CanUse_VampirismAttack",
    "CanUse_VenomFang",
    "CanUse_ViciousAttack",
    "CanUse_VictoriousSweep",
    "CanUse_Volley",
    "CanUse_WanderlustAttack",
    "CanUse_WearyingSpear",
    "CanUse_WearyingStrike",
    "CanUse_WeightOfDhuum",
    "CanUse_WhirlingAxe",
    "CanUse_WhirlwindAttack",
    "CanUse_WhirlwindAttackTuraiOssa",
    "CanUse_WildBlow",
    "CanUse_WildSmash",
    "CanUse_WildStrike",
    "CanUse_WildStrikePvP",
    "CanUse_WildThrow",
    "CanUse_WitheringBlade",
    "CanUse_WoundingStrike",
    "CanUse_WoundingStrikePvP",
    "CanUse_YetiSmash",
    "CanUse_ZealousSweep",
    "CanUse_ZojunsShot",
]
