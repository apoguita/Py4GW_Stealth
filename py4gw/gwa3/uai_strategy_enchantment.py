"""GwAu3's ``UtilityAI_Enchantment.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **580 of this file's 580 are transcribed and 0
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
from .cmd_skill import Skill_UseSkill
from .uai_agent import (
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_effects import (
    UAI_AgentHasEffect,
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
)
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_GetAgentLowest,
    UAI_GetNearestAgent,
    _cached_distance,
)
from .uai_utils import Skill_GetSlotByID


def CanUse_IllusionOfWeakness() -> Any:
    """``UtilityAI_Enchantment.au3:29`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IllusionOfWeakness(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:34`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IllusionaryWeaponry() -> Any:
    """``UtilityAI_Enchantment.au3:43`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IllusionaryWeaponry(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:48`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SympatheticVisage() -> Any:
    """``UtilityAI_Enchantment.au3:57`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SympatheticVisage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:62`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IllusionOfHaste() -> Any:
    """``UtilityAI_Enchantment.au3:73`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IllusionOfHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:78`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Channeling() -> Any:
    """``UtilityAI_Enchantment.au3:87`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Channeling(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:92`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Echo() -> Any:
    """``UtilityAI_Enchantment.au3:101`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Echo(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:106`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArcaneEcho() -> Any:
    """``UtilityAI_Enchantment.au3:115`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArcaneEcho(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:120`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfRecall() -> Any:
    """``UtilityAI_Enchantment.au3:129`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MantraOfRecall(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:134`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VeratasAura() -> Any:
    """``UtilityAI_Enchantment.au3:143`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VeratasAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:148`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathNova() -> Any:
    """``UtilityAI_Enchantment.au3:153`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DeathNova(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:158`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AwakenTheBlood() -> Any:
    """``UtilityAI_Enchantment.au3:169`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AwakenTheBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:174`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TaintedFlesh() -> Any:
    """``UtilityAI_Enchantment.au3:183`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_TaintedFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:188`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfTheLich() -> Any:
    """``UtilityAI_Enchantment.au3:199`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfTheLich(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:204`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodRenewal() -> Any:
    """``UtilityAI_Enchantment.au3:213`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BloodRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:218`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkAura() -> Any:
    """``UtilityAI_Enchantment.au3:227`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_DARK_AURA, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_DarkAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:233`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodIsPower() -> Any:
    """``UtilityAI_Enchantment.au3:242`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BloodIsPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:247`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DemonicFlesh() -> Any:
    """``UtilityAI_Enchantment.au3:258`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DemonicFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:263`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfPain() -> Any:
    """``UtilityAI_Enchantment.au3:272`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_OrderOfPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:277`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkBond() -> Any:
    """``UtilityAI_Enchantment.au3:286`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DarkBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:291`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InfuseCondition() -> Any:
    """``UtilityAI_Enchantment.au3:300`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_InfuseCondition(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:305`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkFury() -> Any:
    """``UtilityAI_Enchantment.au3:314`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DarkFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:319`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfTheVampire() -> Any:
    """``UtilityAI_Enchantment.au3:328`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_OrderOfTheVampire(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:333`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodRitual() -> Any:
    """``UtilityAI_Enchantment.au3:342`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BloodRitual(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:347`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WindborneSpeed() -> Any:
    """``UtilityAI_Enchantment.au3:358`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WindborneSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:363`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:374`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ElementalAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:379`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfEarth() -> Any:
    """``UtilityAI_Enchantment.au3:388`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArmorOfEarth(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:393`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KineticArmor() -> Any:
    """``UtilityAI_Enchantment.au3:402`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_KineticArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:407`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MagneticAura() -> Any:
    """``UtilityAI_Enchantment.au3:416`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MagneticAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:421`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EarthAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:430`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EarthAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:435`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EtherProdigy() -> Any:
    """``UtilityAI_Enchantment.au3:444`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EtherProdigy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:449`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfRestoration() -> Any:
    """``UtilityAI_Enchantment.au3:458`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:463`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EtherRenewal() -> Any:
    """``UtilityAI_Enchantment.au3:472`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EtherRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:477`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConjureFlame() -> Any:
    """``UtilityAI_Enchantment.au3:486`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ConjureFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:491`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FireAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:500`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FireAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:505`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfFrost() -> Any:
    """``UtilityAI_Enchantment.au3:514`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArmorOfFrost(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:519`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConjureFrost() -> Any:
    """``UtilityAI_Enchantment.au3:528`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ConjureFrost(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:533`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WaterAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:542`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WaterAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:547`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IceSpear() -> Any:
    """``UtilityAI_Enchantment.au3:556`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IceSpear(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:561`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_IronMist() -> Any:
    """``UtilityAI_Enchantment.au3:570`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IronMist(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:575`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ObsidianFlesh() -> Any:
    """``UtilityAI_Enchantment.au3:584`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ObsidianFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:589`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConjureLightning() -> Any:
    """``UtilityAI_Enchantment.au3:598`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ConjureLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:603`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AirAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:612`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AirAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:617`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SwirlingAura() -> Any:
    """``UtilityAI_Enchantment.au3:626`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SwirlingAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:631`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MistForm() -> Any:
    """``UtilityAI_Enchantment.au3:640`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MistForm(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:645`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfMist() -> Any:
    """``UtilityAI_Enchantment.au3:654`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArmorOfMist(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:659`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifeBond() -> Any:
    """``UtilityAI_Enchantment.au3:668`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LifeBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:673`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalthazarsSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:684`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BalthazarsSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:689`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StrengthOfHonor() -> Any:
    """``UtilityAI_Enchantment.au3:700`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StrengthOfHonor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:705`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifeAttunement() -> Any:
    """``UtilityAI_Enchantment.au3:716`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LifeAttunement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:721`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ProtectiveSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:732`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ProtectiveSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:737`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DivineIntervention() -> Any:
    """``UtilityAI_Enchantment.au3:748`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DivineIntervention(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:753`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Retribution() -> Any:
    """``UtilityAI_Enchantment.au3:764`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Retribution(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:769`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HolyWrath() -> Any:
    """``UtilityAI_Enchantment.au3:780`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HolyWrath(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:785`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EssenceBond() -> Any:
    """``UtilityAI_Enchantment.au3:796`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EssenceBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:801`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VigorousSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:812`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VigorousSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:817`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WatchfulSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:828`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WatchfulSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:833`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlessedAura() -> Any:
    """``UtilityAI_Enchantment.au3:844`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BlessedAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:849`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Aegis() -> Any:
    """``UtilityAI_Enchantment.au3:858`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Aegis(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:863`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Guardian() -> Any:
    """``UtilityAI_Enchantment.au3:872`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Guardian(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:877`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldOfDeflection() -> Any:
    """``UtilityAI_Enchantment.au3:888`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldOfDeflection(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:893`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfFaith() -> Any:
    """``UtilityAI_Enchantment.au3:904`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfFaith(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:909`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldOfRegeneration() -> Any:
    """``UtilityAI_Enchantment.au3:920`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldOfRegeneration(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:925`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldOfJudgment() -> Any:
    """``UtilityAI_Enchantment.au3:936`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldOfJudgment(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:941`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ProtectiveBond() -> Any:
    """``UtilityAI_Enchantment.au3:952`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ProtectiveBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:957`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PeaceAndHarmony() -> Any:
    """``UtilityAI_Enchantment.au3:968`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PeaceAndHarmony(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:973`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0 and UAI_GetAgentInfoByID(l_i_Target, _constants.GC_UAI_AGENT_HP) < 0.5:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JudgesInsight() -> Any:
    """``UtilityAI_Enchantment.au3:993`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_JudgesInsight(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:998`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnyieldingAura() -> Any:
    """``UtilityAI_Enchantment.au3:1004`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_UnyieldingAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1009`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MarkOfProtection() -> Any:
    """``UtilityAI_Enchantment.au3:1018`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MarkOfProtection(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1023`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifeBarrier() -> Any:
    """``UtilityAI_Enchantment.au3:1034`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LifeBarrier(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1039`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ZealotsFire() -> Any:
    """``UtilityAI_Enchantment.au3:1050`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ZealotsFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1055`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalthazarsAura() -> Any:
    """``UtilityAI_Enchantment.au3:1064`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BalthazarsAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1069`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpellBreaker() -> Any:
    """``UtilityAI_Enchantment.au3:1075`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpellBreaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1080`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingSeed() -> Any:
    """``UtilityAI_Enchantment.au3:1091`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HealingSeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1096`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DivineBoon() -> Any:
    """``UtilityAI_Enchantment.au3:1107`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DivineBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1112`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingHands() -> Any:
    """``UtilityAI_Enchantment.au3:1121`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HealingHands(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1126`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingBreeze() -> Any:
    """``UtilityAI_Enchantment.au3:1137`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) > 0.8:
        return False
    return True


def BestTarget_HealingBreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1143`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_VitalBlessing() -> Any:
    """``UtilityAI_Enchantment.au3:1152`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VitalBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1157`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Mending() -> Any:
    """``UtilityAI_Enchantment.au3:1168`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Mending(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1173`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LiveVicariously() -> Any:
    """``UtilityAI_Enchantment.au3:1184`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LiveVicariously(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1189`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldingHands() -> Any:
    """``UtilityAI_Enchantment.au3:1200`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldingHands(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1205`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReversalOfFortune() -> Any:
    """``UtilityAI_Enchantment.au3:1216`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ReversalOfFortune(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1221`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Succor() -> Any:
    """``UtilityAI_Enchantment.au3:1232`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Succor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1237`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HolyVeil() -> Any:
    """``UtilityAI_Enchantment.au3:1248`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HolyVeil(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1253`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DivineSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:1267`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DivineSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1272`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Vengeance() -> Any:
    """``UtilityAI_Enchantment.au3:1281`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_Vengeance(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1287`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharrBuff() -> Any:
    """``UtilityAI_Enchantment.au3:1296`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_CharrBuff(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1301`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingBreezeAgnarsRage() -> Any:
    """``UtilityAI_Enchantment.au3:1310`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HealingBreezeAgnarsRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1315`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")


def CanUse_DivineFire() -> Any:
    """``UtilityAI_Enchantment.au3:1321`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DivineFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1326`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChimeraOfIntensity() -> Any:
    """``UtilityAI_Enchantment.au3:1335`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ChimeraOfIntensity(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1340`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JaundicedGaze() -> Any:
    """``UtilityAI_Enchantment.au3:1349`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_JaundicedGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1354`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AuraOfDisplacement() -> Any:
    """``UtilityAI_Enchantment.au3:1363`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfDisplacement(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1368`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CultistsFervor() -> Any:
    """``UtilityAI_Enchantment.au3:1377`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_CultistsFervor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1382`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LyssasAura() -> Any:
    """``UtilityAI_Enchantment.au3:1388`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LyssasAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1393`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowRefuge() -> Any:
    """``UtilityAI_Enchantment.au3:1398`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowRefuge(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1403`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VampiricSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:1412`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VampiricSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1417`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BurningSpeed() -> Any:
    """``UtilityAI_Enchantment.au3:1426`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BurningSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1431`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowForm() -> Any:
    """``UtilityAI_Enchantment.au3:1440`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowForm(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1445`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VeratasPromise() -> Any:
    """``UtilityAI_Enchantment.au3:1454`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VeratasPromise(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1459`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BorrowedEnergy() -> Any:
    """``UtilityAI_Enchantment.au3:1464`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BorrowedEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1469`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergyBoon() -> Any:
    """``UtilityAI_Enchantment.au3:1480`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EnergyBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1485`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DwaynasSorrow() -> Any:
    """``UtilityAI_Enchantment.au3:1496`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DwaynasSorrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1501`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Gust() -> Any:
    """``UtilityAI_Enchantment.au3:1507`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Gust(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1512`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReverseHex() -> Any:
    """``UtilityAI_Enchantment.au3:1523`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ReverseHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1528`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OrderOfApostasy() -> Any:
    """``UtilityAI_Enchantment.au3:1542`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_OrderOfApostasy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1547`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldGuardian() -> Any:
    """``UtilityAI_Enchantment.au3:1556`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldGuardian(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1561`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RestfulBreeze() -> Any:
    """``UtilityAI_Enchantment.au3:1570`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RestfulBreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1575`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Recall() -> Any:
    """``UtilityAI_Enchantment.au3:1586`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Recall(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1591`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SharpenDaggers() -> Any:
    """``UtilityAI_Enchantment.au3:1602`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SharpenDaggers(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1607`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuspiciousIncantation() -> Any:
    """``UtilityAI_Enchantment.au3:1616`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuspiciousIncantation(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1621`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheFox() -> Any:
    """``UtilityAI_Enchantment.au3:1630`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfTheFox(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1635`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergyFont() -> Any:
    """``UtilityAI_Enchantment.au3:1644`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EnergyFont(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1649`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpellShield() -> Any:
    """``UtilityAI_Enchantment.au3:1658`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpellShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1663`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheLotus() -> Any:
    """``UtilityAI_Enchantment.au3:1672`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfTheLotus(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1677`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TorchEnchantment() -> Any:
    """``UtilityAI_Enchantment.au3:1686`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_TorchEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1691`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheEmptyPalm() -> Any:
    """``UtilityAI_Enchantment.au3:1700`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfTheEmptyPalm(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1705`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IceFort() -> Any:
    """``UtilityAI_Enchantment.au3:1714`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IceFort(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1719`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IceBreaker() -> Any:
    """``UtilityAI_Enchantment.au3:1728`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IceBreaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1733`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CriticalDefenses() -> Any:
    """``UtilityAI_Enchantment.au3:1742`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_CriticalDefenses(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1747`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfPerfection() -> Any:
    """``UtilityAI_Enchantment.au3:1756`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfPerfection(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1761`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkApostasy() -> Any:
    """``UtilityAI_Enchantment.au3:1770`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DarkApostasy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1775`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LocustsFury() -> Any:
    """``UtilityAI_Enchantment.au3:1784`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LocustsFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1789`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShroudOfDistress() -> Any:
    """``UtilityAI_Enchantment.au3:1794`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShroudOfDistress(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1799`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AncestorsVisage() -> Any:
    """``UtilityAI_Enchantment.au3:1808`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AncestorsVisage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1813`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SliverArmor() -> Any:
    """``UtilityAI_Enchantment.au3:1819`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SliverArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1824`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DoubleDragon() -> Any:
    """``UtilityAI_Enchantment.au3:1833`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DoubleDragon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1838`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritBond() -> Any:
    """``UtilityAI_Enchantment.au3:1849`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1854`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AirOfEnchantment() -> Any:
    """``UtilityAI_Enchantment.au3:1865`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AirOfEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1870`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifeSheath() -> Any:
    """``UtilityAI_Enchantment.au3:1881`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LifeSheath(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1886`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DemonicAgility() -> Any:
    """``UtilityAI_Enchantment.au3:1900`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DemonicAgility(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1905`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlessingOfTheKirin() -> Any:
    """``UtilityAI_Enchantment.au3:1914`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BlessingOfTheKirin(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1919`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExplosiveGrowth() -> Any:
    """``UtilityAI_Enchantment.au3:1928`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ExplosiveGrowth(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1933`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BoonOfCreation() -> Any:
    """``UtilityAI_Enchantment.au3:1942`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BoonOfCreation(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1947`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritChanneling() -> Any:
    """``UtilityAI_Enchantment.au3:1956`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritChanneling(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1961`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GhostlyHaste() -> Any:
    """``UtilityAI_Enchantment.au3:1970`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GhostlyHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1975`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FrigidArmor() -> Any:
    """``UtilityAI_Enchantment.au3:1984`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FrigidArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:1989`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NightmareRefuge() -> Any:
    """``UtilityAI_Enchantment.au3:1998`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_NightmareRefuge(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2003`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarRushMedium() -> Any:
    """``UtilityAI_Enchantment.au3:2012`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SugarRushMedium(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2017`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PersistenceOfMemory() -> Any:
    """``UtilityAI_Enchantment.au3:2022`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PersistenceOfMemory(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2027`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SymbolicCelerity() -> Any:
    """``UtilityAI_Enchantment.au3:2036`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SymbolicCelerity(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2041`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JaggedBones() -> Any:
    """``UtilityAI_Enchantment.au3:2050`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_JaggedBones(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2055`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Contagion() -> Any:
    """``UtilityAI_Enchantment.au3:2064`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Contagion(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2069`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Bloodletting() -> Any:
    """``UtilityAI_Enchantment.au3:2078`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Bloodletting(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2083`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StormDjinnsHaste() -> Any:
    """``UtilityAI_Enchantment.au3:2092`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StormDjinnsHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2097`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StoneStriker() -> Any:
    """``UtilityAI_Enchantment.au3:2102`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StoneStriker(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2107`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StoneSheath() -> Any:
    """``UtilityAI_Enchantment.au3:2116`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StoneSheath(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2121`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StonefleshAura() -> Any:
    """``UtilityAI_Enchantment.au3:2132`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StonefleshAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2137`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MasterOfMagic() -> Any:
    """``UtilityAI_Enchantment.au3:2146`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MasterOfMagic(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2151`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlameDjinnsHaste1() -> Any:
    """``UtilityAI_Enchantment.au3:2160`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FlameDjinnsHaste1(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2165`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JudgesIntervention() -> Any:
    """``UtilityAI_Enchantment.au3:2170`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_JudgesIntervention(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2175`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SupportiveSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:2186`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SupportiveSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2191`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WatchfulHealing() -> Any:
    """``UtilityAI_Enchantment.au3:2202`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WatchfulHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2207`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealersBoon() -> Any:
    """``UtilityAI_Enchantment.au3:2218`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HealersBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2223`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealersCovenant() -> Any:
    """``UtilityAI_Enchantment.au3:2232`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HealersCovenant(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2237`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalthazarsPendulum() -> Any:
    """``UtilityAI_Enchantment.au3:2242`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BalthazarsPendulum(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2247`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldOfAbsorption() -> Any:
    """``UtilityAI_Enchantment.au3:2253`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldOfAbsorption(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2258`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReversalOfDamage() -> Any:
    """``UtilityAI_Enchantment.au3:2269`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ReversalOfDamage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2274`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AbaddonsConspiracy() -> Any:
    """``UtilityAI_Enchantment.au3:2285`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AbaddonsConspiracy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2290`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AbaddonsChosen() -> Any:
    """``UtilityAI_Enchantment.au3:2296`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AbaddonsChosen(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2301`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritsGift() -> Any:
    """``UtilityAI_Enchantment.au3:2306`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritsGift(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2311`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveWindPrayersSkill() -> Any:
    """``UtilityAI_Enchantment.au3:2316`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RemoveWindPrayersSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2321`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GrenthsFingers() -> Any:
    """``UtilityAI_Enchantment.au3:2326`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GrenthsFingers(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2331`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveBoonOfTheGods() -> Any:
    """``UtilityAI_Enchantment.au3:2336`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RemoveBoonOfTheGods(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2341`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfThorns() -> Any:
    """``UtilityAI_Enchantment.au3:2346`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfThorns(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2351`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalthazarsRage() -> Any:
    """``UtilityAI_Enchantment.au3:2360`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BalthazarsRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2365`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DustCloak() -> Any:
    """``UtilityAI_Enchantment.au3:2370`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DustCloak(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2375`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StaggeringForce() -> Any:
    """``UtilityAI_Enchantment.au3:2384`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_CountAgents(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy") <= 1:
        return False
    return True


def BestTarget_StaggeringForce(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2390`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiousRenewal() -> Any:
    """``UtilityAI_Enchantment.au3:2399`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PiousRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2404`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MirageCloak() -> Any:
    """``UtilityAI_Enchantment.au3:2413`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MirageCloak(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2418`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveBalthazarsRage() -> Any:
    """``UtilityAI_Enchantment.au3:2427`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RemoveBalthazarsRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2432`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArcaneZeal() -> Any:
    """``UtilityAI_Enchantment.au3:2437`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArcaneZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2442`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticVigor() -> Any:
    """``UtilityAI_Enchantment.au3:2451`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MysticVigor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2456`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WatchfulIntervention() -> Any:
    """``UtilityAI_Enchantment.au3:2465`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WatchfulIntervention(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2470`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VowOfPiety() -> Any:
    """``UtilityAI_Enchantment.au3:2481`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VowOfPiety(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2486`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VitalBoon() -> Any:
    """``UtilityAI_Enchantment.au3:2495`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VitalBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2500`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeartOfHolyFlame() -> Any:
    """``UtilityAI_Enchantment.au3:2509`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HeartOfHolyFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2514`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FaithfulIntervention() -> Any:
    """``UtilityAI_Enchantment.au3:2523`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FaithfulIntervention(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2528`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SandShards() -> Any:
    """``UtilityAI_Enchantment.au3:2537`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_CountAgents(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy") <= 1:
        return False
    return True


def BestTarget_SandShards(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2543`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IntimidatingAuraBetaVersion() -> Any:
    """``UtilityAI_Enchantment.au3:2552`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IntimidatingAuraBetaVersion(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2557`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LyssasHaste() -> Any:
    """``UtilityAI_Enchantment.au3:2562`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    l_i_NearestEnemy = UAI_GetNearestAgent(-2, 1320, "UAI_Filter_IsLivingEnemy")
    if _cached_distance(l_i_NearestEnemy) > _constants.GC_I_RANGE_ADJACENT:
        return False
    return True


def BestTarget_LyssasHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2569`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GuidingHands() -> Any:
    """``UtilityAI_Enchantment.au3:2578`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GuidingHands(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2583`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FleetingStability() -> Any:
    """``UtilityAI_Enchantment.au3:2592`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FleetingStability(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2597`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfSanctity() -> Any:
    """``UtilityAI_Enchantment.au3:2606`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArmorOfSanctity(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2611`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticRegeneration() -> Any:
    """``UtilityAI_Enchantment.au3:2620`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) >= 0.95:
        return False
    return True


def BestTarget_MysticRegeneration(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2626`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VowOfSilence() -> Any:
    """``UtilityAI_Enchantment.au3:2635`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VowOfSilence(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2640`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Meditation() -> Any:
    """``UtilityAI_Enchantment.au3:2649`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Meditation(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2654`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EremitesZeal() -> Any:
    """``UtilityAI_Enchantment.au3:2663`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_CountAgents(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsLivingEnemy") <= 0:
        return False
    return True


def BestTarget_EremitesZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2669`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IntimidatingAura() -> Any:
    """``UtilityAI_Enchantment.au3:2674`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IntimidatingAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2679`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Conviction() -> Any:
    """``UtilityAI_Enchantment.au3:2688`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Conviction(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2693`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnchantedHaste() -> Any:
    """``UtilityAI_Enchantment.au3:2702`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EnchantedHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2707`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WhirlingCharge() -> Any:
    """``UtilityAI_Enchantment.au3:2716`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WhirlingCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2721`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarRushLong() -> Any:
    """``UtilityAI_Enchantment.au3:2730`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SugarRushLong(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2735`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeadlyHaste() -> Any:
    """``UtilityAI_Enchantment.au3:2740`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DeadlyHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2745`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AssassinsRemedy() -> Any:
    """``UtilityAI_Enchantment.au3:2754`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AssassinsRemedy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2759`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FoxsPromise() -> Any:
    """``UtilityAI_Enchantment.au3:2764`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FoxsPromise(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2769`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeignedNeutrality() -> Any:
    """``UtilityAI_Enchantment.au3:2774`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FeignedNeutrality(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2779`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowMeld() -> Any:
    """``UtilityAI_Enchantment.au3:2788`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowMeld(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2793`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalFlame() -> Any:
    """``UtilityAI_Enchantment.au3:2804`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ElementalFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2809`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PensiveGuardian() -> Any:
    """``UtilityAI_Enchantment.au3:2818`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PensiveGuardian(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2823`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ScribesInsight() -> Any:
    """``UtilityAI_Enchantment.au3:2834`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ScribesInsight(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2839`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HolyHaste() -> Any:
    """``UtilityAI_Enchantment.au3:2844`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HolyHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2849`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritsStrength() -> Any:
    """``UtilityAI_Enchantment.au3:2858`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritsStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2863`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WieldersZeal() -> Any:
    """``UtilityAI_Enchantment.au3:2868`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WieldersZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2873`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SightBeyondSight() -> Any:
    """``UtilityAI_Enchantment.au3:2878`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SightBeyondSight(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2883`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RenewingMemories() -> Any:
    """``UtilityAI_Enchantment.au3:2892`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RenewingMemories(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2897`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WieldersRemedy() -> Any:
    """``UtilityAI_Enchantment.au3:2906`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WieldersRemedy(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2911`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Onslaught() -> Any:
    """``UtilityAI_Enchantment.au3:2916`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Onslaught(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2921`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticCorruption() -> Any:
    """``UtilityAI_Enchantment.au3:2930`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MysticCorruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2935`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GrenthsGrasp() -> Any:
    """``UtilityAI_Enchantment.au3:2944`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GrenthsGrasp(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2949`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VeilOfThorns() -> Any:
    """``UtilityAI_Enchantment.au3:2954`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VeilOfThorns(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2959`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HarriersGrasp() -> Any:
    """``UtilityAI_Enchantment.au3:2968`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HarriersGrasp(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2973`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VowOfStrength() -> Any:
    """``UtilityAI_Enchantment.au3:2978`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    l_b_SkillSlot = Skill_GetSlotByID(_constants.GC_I_SKILL_ID_EXTEND_ENCHANTMENTS)
    l_b_HasEffect = UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_EXTEND_ENCHANTMENTS, _constants.GC_UAI_EFFECT_TimeRemaining) > 500
    if l_b_SkillSlot > 0:
        if not l_b_HasEffect:
            Skill_UseSkill(l_b_SkillSlot)  # pyright: ignore[reportUnusedExpression]


            return True


def BestTarget_VowOfStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:2992`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EbonDustAura() -> Any:
    """``UtilityAI_Enchantment.au3:3001`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EbonDustAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3006`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ZealousVow() -> Any:
    """``UtilityAI_Enchantment.au3:3015`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ZealousVow(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3020`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ZealousRenewal() -> Any:
    """``UtilityAI_Enchantment.au3:3029`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ZealousRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3034`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AttackersInsight() -> Any:
    """``UtilityAI_Enchantment.au3:3043`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AttackersInsight(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3048`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RendingAura() -> Any:
    """``UtilityAI_Enchantment.au3:3053`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_RendingAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3058`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeatherfootGrace() -> Any:
    """``UtilityAI_Enchantment.au3:3067`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FeatherfootGrace(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3072`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HarriersHaste() -> Any:
    """``UtilityAI_Enchantment.au3:3081`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HarriersHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3086`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AcceleratedGrowth() -> Any:
    """``UtilityAI_Enchantment.au3:3091`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AcceleratedGrowth(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3096`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritFormRemainsOfSahlahja() -> Any:
    """``UtilityAI_Enchantment.au3:3105`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritFormRemainsOfSahlahja(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3110`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GodsBlessing() -> Any:
    """``UtilityAI_Enchantment.au3:3115`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GodsBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3120`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarRushShort() -> Any:
    """``UtilityAI_Enchantment.au3:3125`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SugarRushShort(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3130`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarJoltShort() -> Any:
    """``UtilityAI_Enchantment.au3:3135`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SugarJoltShort(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3140`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarJoltLong() -> Any:
    """``UtilityAI_Enchantment.au3:3145`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SugarJoltLong(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3150`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowSanctuaryLuxon2() -> Any:
    """``UtilityAI_Enchantment.au3:3155`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowSanctuaryLuxon2(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3160`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalLordLuxon() -> Any:
    """``UtilityAI_Enchantment.au3:3165`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ElementalLordLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3170`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SelflessSpiritLuxon() -> Any:
    """``UtilityAI_Enchantment.au3:3175`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SelflessSpiritLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3180`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfHolyMightLuxon() -> Any:
    """``UtilityAI_Enchantment.au3:3185`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_AgentHasEffect(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_SKILL_ID_PIOUS_RENEWAL):
        return False
    return True


def BestTarget_AuraOfHolyMightLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3191`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheMantis() -> Any:
    """``UtilityAI_Enchantment.au3:3196`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfTheMantis(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3201`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WitheringAura() -> Any:
    """``UtilityAI_Enchantment.au3:3210`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WitheringAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3215`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SmitersBoon() -> Any:
    """``UtilityAI_Enchantment.au3:3226`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SmitersBoon(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3231`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PurifyingVeil() -> Any:
    """``UtilityAI_Enchantment.au3:3236`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PurifyingVeil(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3241`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GrenthsAura() -> Any:
    """``UtilityAI_Enchantment.au3:3255`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    l_i_NearestEnemy = UAI_GetNearestAgent(-2, 1320, "UAI_Filter_IsLivingEnemy")
    if _cached_distance(l_i_NearestEnemy) > _constants.GC_I_RANGE_ADJACENT:
        return False
    return True


def BestTarget_GrenthsAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3262`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PatientSpirit() -> Any:
    """``UtilityAI_Enchantment.au3:3267`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PatientSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3272`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfStability() -> Any:
    """``UtilityAI_Enchantment.au3:3283`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfStability(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3288`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpotlessMind() -> Any:
    """``UtilityAI_Enchantment.au3:3299`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpotlessMind(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3304`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpotlessSoul() -> Any:
    """``UtilityAI_Enchantment.au3:3318`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpotlessSoul(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3323`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowSanctuaryKurzick() -> Any:
    """``UtilityAI_Enchantment.au3:3337`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowSanctuaryKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3342`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalLordKurzick() -> Any:
    """``UtilityAI_Enchantment.au3:3347`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ElementalLordKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3352`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SelflessSpiritKurzick() -> Any:
    """``UtilityAI_Enchantment.au3:3357`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SelflessSpiritKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3362`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfHolyMightKurzick() -> Any:
    """``UtilityAI_Enchantment.au3:3367`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_AgentHasEffect(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_SKILL_ID_PIOUS_RENEWAL):
        return False
    return True


def BestTarget_AuraOfHolyMightKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3373`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CriticalAgility() -> Any:
    """``UtilityAI_Enchantment.au3:3378`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_CriticalAgility(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3383`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SeedOfLife() -> Any:
    """``UtilityAI_Enchantment.au3:3392`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SeedOfLife(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3397`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EternalAura() -> Any:
    """``UtilityAI_Enchantment.au3:3408`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_EternalAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3414`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenPounceCurseOfTheNornbear() -> Any:
    """``UtilityAI_Enchantment.au3:3423`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VolfenPounceCurseOfTheNornbear(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3428`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HexersVigor() -> Any:
    """``UtilityAI_Enchantment.au3:3433`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HexersVigor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3438`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Masochism() -> Any:
    """``UtilityAI_Enchantment.au3:3443`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_MASOCHISM, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_Masochism(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3449`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheMaster() -> Any:
    """``UtilityAI_Enchantment.au3:3458`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_WayOfTheMaster(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3463`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MagneticSurge() -> Any:
    """``UtilityAI_Enchantment.au3:3472`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MagneticSurge(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3477`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShieldOfForce() -> Any:
    """``UtilityAI_Enchantment.au3:3486`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShieldOfForce(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3491`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GreatDwarfArmor() -> Any:
    """``UtilityAI_Enchantment.au3:3500`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GreatDwarfArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3505`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockBlock() -> Any:
    """``UtilityAI_Enchantment.au3:3516`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PolymockBlock(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3521`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockLightningDjinnsHaste() -> Any:
    """``UtilityAI_Enchantment.au3:3530`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PolymockLightningDjinnsHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3535`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockFrozenArmor() -> Any:
    """``UtilityAI_Enchantment.au3:3540`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_PolymockFrozenArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3545`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CrystalShield() -> Any:
    """``UtilityAI_Enchantment.au3:3554`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_CrystalShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3559`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenAgility() -> Any:
    """``UtilityAI_Enchantment.au3:3568`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VolfenAgility(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3573`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Mindbender() -> Any:
    """``UtilityAI_Enchantment.au3:3582`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_Mindbender(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3587`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MentalBlock() -> Any:
    """``UtilityAI_Enchantment.au3:3596`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MentalBlock(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3601`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DwarvenStability() -> Any:
    """``UtilityAI_Enchantment.au3:3610`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DwarvenStability(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3615`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlameDjinnsHaste2() -> Any:
    """``UtilityAI_Enchantment.au3:3624`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_FlameDjinnsHaste2(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3629`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DragonEmpireRage() -> Any:
    """``UtilityAI_Enchantment.au3:3635`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DragonEmpireRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3640`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfPurity() -> Any:
    """``UtilityAI_Enchantment.au3:3649`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3654`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MistFormPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3665`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MistFormPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3670`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AegisPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3675`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AegisPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3680`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EtherRenewalPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3686`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EtherRenewalPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3691`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowFormPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3696`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShadowFormPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3701`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AssassinsRemedyPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3706`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AssassinsRemedyPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3711`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MysticRegenerationPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3716`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MysticRegenerationPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3721`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnyieldingAuraPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3726`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_UnyieldingAuraPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3731`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritBondPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3737`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SpiritBondPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3742`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SmitersBoonPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3750`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_SmitersBoonPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3755`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BitGolemRectifier() -> Any:
    """``UtilityAI_Enchantment.au3:3760`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_BitGolemRectifier(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3765`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StrengthOfHonorPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3778`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_StrengthOfHonorPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3783`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfUnfeelingPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3789`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ArmorOfUnfeelingPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3794`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShroudOfDistressPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3799`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ShroudOfDistressPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3804`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MasochismPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3809`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_MasochismPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3814`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IllusionaryWeaponryPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3819`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IllusionaryWeaponryPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3824`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EbonDustAuraPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3829`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_EbonDustAuraPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3834`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeartOfHolyFlamePvP() -> Any:
    """``UtilityAI_Enchantment.au3:3839`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_HeartOfHolyFlamePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3844`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GuidingHandsPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3849`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_GuidingHandsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3854`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfThornsPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3859`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfThornsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3864`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DustCloakPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3869`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_DustCloakPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3874`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LyssasHastePvP() -> Any:
    """``UtilityAI_Enchantment.au3:3879`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_LyssasHastePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3884`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OnslaughtPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3889`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_OnslaughtPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3894`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IllusionOfHastePvP() -> Any:
    """``UtilityAI_Enchantment.au3:3899`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_IllusionOfHastePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3904`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfRestorationPvP() -> Any:
    """``UtilityAI_Enchantment.au3:3909`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_AuraOfRestorationPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3914`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalFlamePvP() -> Any:
    """``UtilityAI_Enchantment.au3:3919`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_ElementalFlamePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3924`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoulTaker() -> Any:
    """``UtilityAI_Enchantment.au3:3929`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_TAKER, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_SoulTaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3935`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OverTheLimit() -> Any:
    """``UtilityAI_Enchantment.au3:3944`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_OverTheLimit(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3949`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VowOfRevolution() -> Any:
    """``UtilityAI_Enchantment.au3:3958`` -- transcribed from GwAu3's own body."""

    if Anti_Enchantment():
        return False
    return True


def BestTarget_VowOfRevolution(a_f_AggroRange) -> Any:
    """``UtilityAI_Enchantment.au3:3963`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AbaddonsChosen",
    "BestTarget_AbaddonsConspiracy",
    "BestTarget_AcceleratedGrowth",
    "BestTarget_Aegis",
    "BestTarget_AegisPvP",
    "BestTarget_AirAttunement",
    "BestTarget_AirOfEnchantment",
    "BestTarget_AncestorsVisage",
    "BestTarget_ArcaneEcho",
    "BestTarget_ArcaneZeal",
    "BestTarget_ArmorOfEarth",
    "BestTarget_ArmorOfFrost",
    "BestTarget_ArmorOfMist",
    "BestTarget_ArmorOfSanctity",
    "BestTarget_ArmorOfUnfeelingPvP",
    "BestTarget_AssassinsRemedy",
    "BestTarget_AssassinsRemedyPvP",
    "BestTarget_AttackersInsight",
    "BestTarget_AuraOfDisplacement",
    "BestTarget_AuraOfFaith",
    "BestTarget_AuraOfHolyMightKurzick",
    "BestTarget_AuraOfHolyMightLuxon",
    "BestTarget_AuraOfPurity",
    "BestTarget_AuraOfRestoration",
    "BestTarget_AuraOfRestorationPvP",
    "BestTarget_AuraOfStability",
    "BestTarget_AuraOfTheLich",
    "BestTarget_AuraOfThorns",
    "BestTarget_AuraOfThornsPvP",
    "BestTarget_AuspiciousIncantation",
    "BestTarget_AwakenTheBlood",
    "BestTarget_BalthazarsAura",
    "BestTarget_BalthazarsPendulum",
    "BestTarget_BalthazarsRage",
    "BestTarget_BalthazarsSpirit",
    "BestTarget_BitGolemRectifier",
    "BestTarget_BlessedAura",
    "BestTarget_BlessingOfTheKirin",
    "BestTarget_BloodIsPower",
    "BestTarget_BloodRenewal",
    "BestTarget_BloodRitual",
    "BestTarget_Bloodletting",
    "BestTarget_BoonOfCreation",
    "BestTarget_BorrowedEnergy",
    "BestTarget_BurningSpeed",
    "BestTarget_Channeling",
    "BestTarget_CharrBuff",
    "BestTarget_ChimeraOfIntensity",
    "BestTarget_ConjureFlame",
    "BestTarget_ConjureFrost",
    "BestTarget_ConjureLightning",
    "BestTarget_Contagion",
    "BestTarget_Conviction",
    "BestTarget_CriticalAgility",
    "BestTarget_CriticalDefenses",
    "BestTarget_CrystalShield",
    "BestTarget_CultistsFervor",
    "BestTarget_DarkApostasy",
    "BestTarget_DarkAura",
    "BestTarget_DarkBond",
    "BestTarget_DarkFury",
    "BestTarget_DeadlyHaste",
    "BestTarget_DeathNova",
    "BestTarget_DemonicAgility",
    "BestTarget_DemonicFlesh",
    "BestTarget_DivineBoon",
    "BestTarget_DivineFire",
    "BestTarget_DivineIntervention",
    "BestTarget_DivineSpirit",
    "BestTarget_DoubleDragon",
    "BestTarget_DragonEmpireRage",
    "BestTarget_DustCloak",
    "BestTarget_DustCloakPvP",
    "BestTarget_DwarvenStability",
    "BestTarget_DwaynasSorrow",
    "BestTarget_EarthAttunement",
    "BestTarget_EbonDustAura",
    "BestTarget_EbonDustAuraPvP",
    "BestTarget_Echo",
    "BestTarget_ElementalAttunement",
    "BestTarget_ElementalFlame",
    "BestTarget_ElementalFlamePvP",
    "BestTarget_ElementalLordKurzick",
    "BestTarget_ElementalLordLuxon",
    "BestTarget_EnchantedHaste",
    "BestTarget_EnergyBoon",
    "BestTarget_EnergyFont",
    "BestTarget_EremitesZeal",
    "BestTarget_EssenceBond",
    "BestTarget_EternalAura",
    "BestTarget_EtherProdigy",
    "BestTarget_EtherRenewal",
    "BestTarget_EtherRenewalPvP",
    "BestTarget_ExplosiveGrowth",
    "BestTarget_FaithfulIntervention",
    "BestTarget_FeatherfootGrace",
    "BestTarget_FeignedNeutrality",
    "BestTarget_FireAttunement",
    "BestTarget_FlameDjinnsHaste1",
    "BestTarget_FlameDjinnsHaste2",
    "BestTarget_FleetingStability",
    "BestTarget_FoxsPromise",
    "BestTarget_FrigidArmor",
    "BestTarget_GhostlyHaste",
    "BestTarget_GodsBlessing",
    "BestTarget_GreatDwarfArmor",
    "BestTarget_GrenthsAura",
    "BestTarget_GrenthsFingers",
    "BestTarget_GrenthsGrasp",
    "BestTarget_Guardian",
    "BestTarget_GuidingHands",
    "BestTarget_GuidingHandsPvP",
    "BestTarget_Gust",
    "BestTarget_HarriersGrasp",
    "BestTarget_HarriersHaste",
    "BestTarget_HealersBoon",
    "BestTarget_HealersCovenant",
    "BestTarget_HealingBreeze",
    "BestTarget_HealingBreezeAgnarsRage",
    "BestTarget_HealingHands",
    "BestTarget_HealingSeed",
    "BestTarget_HeartOfHolyFlame",
    "BestTarget_HeartOfHolyFlamePvP",
    "BestTarget_HexersVigor",
    "BestTarget_HolyHaste",
    "BestTarget_HolyVeil",
    "BestTarget_HolyWrath",
    "BestTarget_IceBreaker",
    "BestTarget_IceFort",
    "BestTarget_IceSpear",
    "BestTarget_IllusionOfHaste",
    "BestTarget_IllusionOfHastePvP",
    "BestTarget_IllusionOfWeakness",
    "BestTarget_IllusionaryWeaponry",
    "BestTarget_IllusionaryWeaponryPvP",
    "BestTarget_InfuseCondition",
    "BestTarget_IntimidatingAura",
    "BestTarget_IntimidatingAuraBetaVersion",
    "BestTarget_IronMist",
    "BestTarget_JaggedBones",
    "BestTarget_JaundicedGaze",
    "BestTarget_JudgesInsight",
    "BestTarget_JudgesIntervention",
    "BestTarget_KineticArmor",
    "BestTarget_LifeAttunement",
    "BestTarget_LifeBarrier",
    "BestTarget_LifeBond",
    "BestTarget_LifeSheath",
    "BestTarget_LiveVicariously",
    "BestTarget_LocustsFury",
    "BestTarget_LyssasAura",
    "BestTarget_LyssasHaste",
    "BestTarget_LyssasHastePvP",
    "BestTarget_MagneticAura",
    "BestTarget_MagneticSurge",
    "BestTarget_MantraOfRecall",
    "BestTarget_MarkOfProtection",
    "BestTarget_Masochism",
    "BestTarget_MasochismPvP",
    "BestTarget_MasterOfMagic",
    "BestTarget_Meditation",
    "BestTarget_Mending",
    "BestTarget_MentalBlock",
    "BestTarget_Mindbender",
    "BestTarget_MirageCloak",
    "BestTarget_MistForm",
    "BestTarget_MistFormPvP",
    "BestTarget_MysticCorruption",
    "BestTarget_MysticRegeneration",
    "BestTarget_MysticRegenerationPvP",
    "BestTarget_MysticVigor",
    "BestTarget_NightmareRefuge",
    "BestTarget_ObsidianFlesh",
    "BestTarget_Onslaught",
    "BestTarget_OnslaughtPvP",
    "BestTarget_OrderOfApostasy",
    "BestTarget_OrderOfPain",
    "BestTarget_OrderOfTheVampire",
    "BestTarget_OverTheLimit",
    "BestTarget_PatientSpirit",
    "BestTarget_PeaceAndHarmony",
    "BestTarget_PensiveGuardian",
    "BestTarget_PersistenceOfMemory",
    "BestTarget_PiousRenewal",
    "BestTarget_PolymockBlock",
    "BestTarget_PolymockFrozenArmor",
    "BestTarget_PolymockLightningDjinnsHaste",
    "BestTarget_ProtectiveBond",
    "BestTarget_ProtectiveSpirit",
    "BestTarget_PurifyingVeil",
    "BestTarget_Recall",
    "BestTarget_RemoveBalthazarsRage",
    "BestTarget_RemoveBoonOfTheGods",
    "BestTarget_RemoveWindPrayersSkill",
    "BestTarget_RendingAura",
    "BestTarget_RenewingMemories",
    "BestTarget_RestfulBreeze",
    "BestTarget_Retribution",
    "BestTarget_ReversalOfDamage",
    "BestTarget_ReversalOfFortune",
    "BestTarget_ReverseHex",
    "BestTarget_SandShards",
    "BestTarget_ScribesInsight",
    "BestTarget_SeedOfLife",
    "BestTarget_SelflessSpiritKurzick",
    "BestTarget_SelflessSpiritLuxon",
    "BestTarget_ShadowForm",
    "BestTarget_ShadowFormPvP",
    "BestTarget_ShadowMeld",
    "BestTarget_ShadowRefuge",
    "BestTarget_ShadowSanctuaryKurzick",
    "BestTarget_ShadowSanctuaryLuxon2",
    "BestTarget_SharpenDaggers",
    "BestTarget_ShieldGuardian",
    "BestTarget_ShieldOfAbsorption",
    "BestTarget_ShieldOfDeflection",
    "BestTarget_ShieldOfForce",
    "BestTarget_ShieldOfJudgment",
    "BestTarget_ShieldOfRegeneration",
    "BestTarget_ShieldingHands",
    "BestTarget_ShroudOfDistress",
    "BestTarget_ShroudOfDistressPvP",
    "BestTarget_SightBeyondSight",
    "BestTarget_SliverArmor",
    "BestTarget_SmitersBoon",
    "BestTarget_SmitersBoonPvP",
    "BestTarget_SoulTaker",
    "BestTarget_SpellBreaker",
    "BestTarget_SpellShield",
    "BestTarget_SpiritBond",
    "BestTarget_SpiritBondPvP",
    "BestTarget_SpiritChanneling",
    "BestTarget_SpiritFormRemainsOfSahlahja",
    "BestTarget_SpiritsGift",
    "BestTarget_SpiritsStrength",
    "BestTarget_SpotlessMind",
    "BestTarget_SpotlessSoul",
    "BestTarget_StaggeringForce",
    "BestTarget_StoneSheath",
    "BestTarget_StoneStriker",
    "BestTarget_StonefleshAura",
    "BestTarget_StormDjinnsHaste",
    "BestTarget_StrengthOfHonor",
    "BestTarget_StrengthOfHonorPvP",
    "BestTarget_Succor",
    "BestTarget_SugarJoltLong",
    "BestTarget_SugarJoltShort",
    "BestTarget_SugarRushLong",
    "BestTarget_SugarRushMedium",
    "BestTarget_SugarRushShort",
    "BestTarget_SupportiveSpirit",
    "BestTarget_SwirlingAura",
    "BestTarget_SymbolicCelerity",
    "BestTarget_SympatheticVisage",
    "BestTarget_TaintedFlesh",
    "BestTarget_TorchEnchantment",
    "BestTarget_UnyieldingAura",
    "BestTarget_UnyieldingAuraPvP",
    "BestTarget_VampiricSpirit",
    "BestTarget_VeilOfThorns",
    "BestTarget_Vengeance",
    "BestTarget_VeratasAura",
    "BestTarget_VeratasPromise",
    "BestTarget_VigorousSpirit",
    "BestTarget_VitalBlessing",
    "BestTarget_VitalBoon",
    "BestTarget_VolfenAgility",
    "BestTarget_VolfenPounceCurseOfTheNornbear",
    "BestTarget_VowOfPiety",
    "BestTarget_VowOfRevolution",
    "BestTarget_VowOfSilence",
    "BestTarget_VowOfStrength",
    "BestTarget_WatchfulHealing",
    "BestTarget_WatchfulIntervention",
    "BestTarget_WatchfulSpirit",
    "BestTarget_WaterAttunement",
    "BestTarget_WayOfPerfection",
    "BestTarget_WayOfTheEmptyPalm",
    "BestTarget_WayOfTheFox",
    "BestTarget_WayOfTheLotus",
    "BestTarget_WayOfTheMantis",
    "BestTarget_WayOfTheMaster",
    "BestTarget_WhirlingCharge",
    "BestTarget_WieldersRemedy",
    "BestTarget_WieldersZeal",
    "BestTarget_WindborneSpeed",
    "BestTarget_WitheringAura",
    "BestTarget_ZealotsFire",
    "BestTarget_ZealousRenewal",
    "BestTarget_ZealousVow",
    "CanUse_AbaddonsChosen",
    "CanUse_AbaddonsConspiracy",
    "CanUse_AcceleratedGrowth",
    "CanUse_Aegis",
    "CanUse_AegisPvP",
    "CanUse_AirAttunement",
    "CanUse_AirOfEnchantment",
    "CanUse_AncestorsVisage",
    "CanUse_ArcaneEcho",
    "CanUse_ArcaneZeal",
    "CanUse_ArmorOfEarth",
    "CanUse_ArmorOfFrost",
    "CanUse_ArmorOfMist",
    "CanUse_ArmorOfSanctity",
    "CanUse_ArmorOfUnfeelingPvP",
    "CanUse_AssassinsRemedy",
    "CanUse_AssassinsRemedyPvP",
    "CanUse_AttackersInsight",
    "CanUse_AuraOfDisplacement",
    "CanUse_AuraOfFaith",
    "CanUse_AuraOfHolyMightKurzick",
    "CanUse_AuraOfHolyMightLuxon",
    "CanUse_AuraOfPurity",
    "CanUse_AuraOfRestoration",
    "CanUse_AuraOfRestorationPvP",
    "CanUse_AuraOfStability",
    "CanUse_AuraOfTheLich",
    "CanUse_AuraOfThorns",
    "CanUse_AuraOfThornsPvP",
    "CanUse_AuspiciousIncantation",
    "CanUse_AwakenTheBlood",
    "CanUse_BalthazarsAura",
    "CanUse_BalthazarsPendulum",
    "CanUse_BalthazarsRage",
    "CanUse_BalthazarsSpirit",
    "CanUse_BitGolemRectifier",
    "CanUse_BlessedAura",
    "CanUse_BlessingOfTheKirin",
    "CanUse_BloodIsPower",
    "CanUse_BloodRenewal",
    "CanUse_BloodRitual",
    "CanUse_Bloodletting",
    "CanUse_BoonOfCreation",
    "CanUse_BorrowedEnergy",
    "CanUse_BurningSpeed",
    "CanUse_Channeling",
    "CanUse_CharrBuff",
    "CanUse_ChimeraOfIntensity",
    "CanUse_ConjureFlame",
    "CanUse_ConjureFrost",
    "CanUse_ConjureLightning",
    "CanUse_Contagion",
    "CanUse_Conviction",
    "CanUse_CriticalAgility",
    "CanUse_CriticalDefenses",
    "CanUse_CrystalShield",
    "CanUse_CultistsFervor",
    "CanUse_DarkApostasy",
    "CanUse_DarkAura",
    "CanUse_DarkBond",
    "CanUse_DarkFury",
    "CanUse_DeadlyHaste",
    "CanUse_DeathNova",
    "CanUse_DemonicAgility",
    "CanUse_DemonicFlesh",
    "CanUse_DivineBoon",
    "CanUse_DivineFire",
    "CanUse_DivineIntervention",
    "CanUse_DivineSpirit",
    "CanUse_DoubleDragon",
    "CanUse_DragonEmpireRage",
    "CanUse_DustCloak",
    "CanUse_DustCloakPvP",
    "CanUse_DwarvenStability",
    "CanUse_DwaynasSorrow",
    "CanUse_EarthAttunement",
    "CanUse_EbonDustAura",
    "CanUse_EbonDustAuraPvP",
    "CanUse_Echo",
    "CanUse_ElementalAttunement",
    "CanUse_ElementalFlame",
    "CanUse_ElementalFlamePvP",
    "CanUse_ElementalLordKurzick",
    "CanUse_ElementalLordLuxon",
    "CanUse_EnchantedHaste",
    "CanUse_EnergyBoon",
    "CanUse_EnergyFont",
    "CanUse_EremitesZeal",
    "CanUse_EssenceBond",
    "CanUse_EternalAura",
    "CanUse_EtherProdigy",
    "CanUse_EtherRenewal",
    "CanUse_EtherRenewalPvP",
    "CanUse_ExplosiveGrowth",
    "CanUse_FaithfulIntervention",
    "CanUse_FeatherfootGrace",
    "CanUse_FeignedNeutrality",
    "CanUse_FireAttunement",
    "CanUse_FlameDjinnsHaste1",
    "CanUse_FlameDjinnsHaste2",
    "CanUse_FleetingStability",
    "CanUse_FoxsPromise",
    "CanUse_FrigidArmor",
    "CanUse_GhostlyHaste",
    "CanUse_GodsBlessing",
    "CanUse_GreatDwarfArmor",
    "CanUse_GrenthsAura",
    "CanUse_GrenthsFingers",
    "CanUse_GrenthsGrasp",
    "CanUse_Guardian",
    "CanUse_GuidingHands",
    "CanUse_GuidingHandsPvP",
    "CanUse_Gust",
    "CanUse_HarriersGrasp",
    "CanUse_HarriersHaste",
    "CanUse_HealersBoon",
    "CanUse_HealersCovenant",
    "CanUse_HealingBreeze",
    "CanUse_HealingBreezeAgnarsRage",
    "CanUse_HealingHands",
    "CanUse_HealingSeed",
    "CanUse_HeartOfHolyFlame",
    "CanUse_HeartOfHolyFlamePvP",
    "CanUse_HexersVigor",
    "CanUse_HolyHaste",
    "CanUse_HolyVeil",
    "CanUse_HolyWrath",
    "CanUse_IceBreaker",
    "CanUse_IceFort",
    "CanUse_IceSpear",
    "CanUse_IllusionOfHaste",
    "CanUse_IllusionOfHastePvP",
    "CanUse_IllusionOfWeakness",
    "CanUse_IllusionaryWeaponry",
    "CanUse_IllusionaryWeaponryPvP",
    "CanUse_InfuseCondition",
    "CanUse_IntimidatingAura",
    "CanUse_IntimidatingAuraBetaVersion",
    "CanUse_IronMist",
    "CanUse_JaggedBones",
    "CanUse_JaundicedGaze",
    "CanUse_JudgesInsight",
    "CanUse_JudgesIntervention",
    "CanUse_KineticArmor",
    "CanUse_LifeAttunement",
    "CanUse_LifeBarrier",
    "CanUse_LifeBond",
    "CanUse_LifeSheath",
    "CanUse_LiveVicariously",
    "CanUse_LocustsFury",
    "CanUse_LyssasAura",
    "CanUse_LyssasHaste",
    "CanUse_LyssasHastePvP",
    "CanUse_MagneticAura",
    "CanUse_MagneticSurge",
    "CanUse_MantraOfRecall",
    "CanUse_MarkOfProtection",
    "CanUse_Masochism",
    "CanUse_MasochismPvP",
    "CanUse_MasterOfMagic",
    "CanUse_Meditation",
    "CanUse_Mending",
    "CanUse_MentalBlock",
    "CanUse_Mindbender",
    "CanUse_MirageCloak",
    "CanUse_MistForm",
    "CanUse_MistFormPvP",
    "CanUse_MysticCorruption",
    "CanUse_MysticRegeneration",
    "CanUse_MysticRegenerationPvP",
    "CanUse_MysticVigor",
    "CanUse_NightmareRefuge",
    "CanUse_ObsidianFlesh",
    "CanUse_Onslaught",
    "CanUse_OnslaughtPvP",
    "CanUse_OrderOfApostasy",
    "CanUse_OrderOfPain",
    "CanUse_OrderOfTheVampire",
    "CanUse_OverTheLimit",
    "CanUse_PatientSpirit",
    "CanUse_PeaceAndHarmony",
    "CanUse_PensiveGuardian",
    "CanUse_PersistenceOfMemory",
    "CanUse_PiousRenewal",
    "CanUse_PolymockBlock",
    "CanUse_PolymockFrozenArmor",
    "CanUse_PolymockLightningDjinnsHaste",
    "CanUse_ProtectiveBond",
    "CanUse_ProtectiveSpirit",
    "CanUse_PurifyingVeil",
    "CanUse_Recall",
    "CanUse_RemoveBalthazarsRage",
    "CanUse_RemoveBoonOfTheGods",
    "CanUse_RemoveWindPrayersSkill",
    "CanUse_RendingAura",
    "CanUse_RenewingMemories",
    "CanUse_RestfulBreeze",
    "CanUse_Retribution",
    "CanUse_ReversalOfDamage",
    "CanUse_ReversalOfFortune",
    "CanUse_ReverseHex",
    "CanUse_SandShards",
    "CanUse_ScribesInsight",
    "CanUse_SeedOfLife",
    "CanUse_SelflessSpiritKurzick",
    "CanUse_SelflessSpiritLuxon",
    "CanUse_ShadowForm",
    "CanUse_ShadowFormPvP",
    "CanUse_ShadowMeld",
    "CanUse_ShadowRefuge",
    "CanUse_ShadowSanctuaryKurzick",
    "CanUse_ShadowSanctuaryLuxon2",
    "CanUse_SharpenDaggers",
    "CanUse_ShieldGuardian",
    "CanUse_ShieldOfAbsorption",
    "CanUse_ShieldOfDeflection",
    "CanUse_ShieldOfForce",
    "CanUse_ShieldOfJudgment",
    "CanUse_ShieldOfRegeneration",
    "CanUse_ShieldingHands",
    "CanUse_ShroudOfDistress",
    "CanUse_ShroudOfDistressPvP",
    "CanUse_SightBeyondSight",
    "CanUse_SliverArmor",
    "CanUse_SmitersBoon",
    "CanUse_SmitersBoonPvP",
    "CanUse_SoulTaker",
    "CanUse_SpellBreaker",
    "CanUse_SpellShield",
    "CanUse_SpiritBond",
    "CanUse_SpiritBondPvP",
    "CanUse_SpiritChanneling",
    "CanUse_SpiritFormRemainsOfSahlahja",
    "CanUse_SpiritsGift",
    "CanUse_SpiritsStrength",
    "CanUse_SpotlessMind",
    "CanUse_SpotlessSoul",
    "CanUse_StaggeringForce",
    "CanUse_StoneSheath",
    "CanUse_StoneStriker",
    "CanUse_StonefleshAura",
    "CanUse_StormDjinnsHaste",
    "CanUse_StrengthOfHonor",
    "CanUse_StrengthOfHonorPvP",
    "CanUse_Succor",
    "CanUse_SugarJoltLong",
    "CanUse_SugarJoltShort",
    "CanUse_SugarRushLong",
    "CanUse_SugarRushMedium",
    "CanUse_SugarRushShort",
    "CanUse_SupportiveSpirit",
    "CanUse_SwirlingAura",
    "CanUse_SymbolicCelerity",
    "CanUse_SympatheticVisage",
    "CanUse_TaintedFlesh",
    "CanUse_TorchEnchantment",
    "CanUse_UnyieldingAura",
    "CanUse_UnyieldingAuraPvP",
    "CanUse_VampiricSpirit",
    "CanUse_VeilOfThorns",
    "CanUse_Vengeance",
    "CanUse_VeratasAura",
    "CanUse_VeratasPromise",
    "CanUse_VigorousSpirit",
    "CanUse_VitalBlessing",
    "CanUse_VitalBoon",
    "CanUse_VolfenAgility",
    "CanUse_VolfenPounceCurseOfTheNornbear",
    "CanUse_VowOfPiety",
    "CanUse_VowOfRevolution",
    "CanUse_VowOfSilence",
    "CanUse_VowOfStrength",
    "CanUse_WatchfulHealing",
    "CanUse_WatchfulIntervention",
    "CanUse_WatchfulSpirit",
    "CanUse_WaterAttunement",
    "CanUse_WayOfPerfection",
    "CanUse_WayOfTheEmptyPalm",
    "CanUse_WayOfTheFox",
    "CanUse_WayOfTheLotus",
    "CanUse_WayOfTheMantis",
    "CanUse_WayOfTheMaster",
    "CanUse_WhirlingCharge",
    "CanUse_WieldersRemedy",
    "CanUse_WieldersZeal",
    "CanUse_WindborneSpeed",
    "CanUse_WitheringAura",
    "CanUse_ZealotsFire",
    "CanUse_ZealousRenewal",
    "CanUse_ZealousVow",
]
