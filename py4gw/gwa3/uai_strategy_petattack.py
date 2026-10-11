"""GwAu3's ``UtilityAI_PetAttack.au3`` strategy functions, transcribed.

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
from .uai_get_agent import (
    UAI_GetBestAOETarget,
    UAI_GetBestSingleTarget,
)


def CanUse_BestialPounce() -> Any:
    """``UtilityAI_PetAttack.au3:21`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_BestialPounce(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:26`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MaimingStrike() -> Any:
    """``UtilityAI_PetAttack.au3:41`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_MaimingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:46`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_FeralLunge() -> Any:
    """``UtilityAI_PetAttack.au3:61`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_FeralLunge(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:66`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ScavengerStrike() -> Any:
    """``UtilityAI_PetAttack.au3:81`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_ScavengerStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:86`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MelandrusAssault() -> Any:
    """``UtilityAI_PetAttack.au3:101`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_MelandrusAssault(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:106`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_FerociousStrike() -> Any:
    """``UtilityAI_PetAttack.au3:117`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_FerociousStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:122`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PredatorsPounce() -> Any:
    """``UtilityAI_PetAttack.au3:133`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_PredatorsPounce(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:138`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_BrutalStrike() -> Any:
    """``UtilityAI_PetAttack.au3:149`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_BrutalStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:154`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBelow50HP")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DisruptingLunge() -> Any:
    """``UtilityAI_PetAttack.au3:169`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_DisruptingLunge(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:174`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SavagePounce() -> Any:
    """``UtilityAI_PetAttack.au3:189`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_SavagePounce(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:194`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnragedLunge() -> Any:
    """``UtilityAI_PetAttack.au3:209`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_EnragedLunge(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:214`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotDeepWounded")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_BestialMauling() -> Any:
    """``UtilityAI_PetAttack.au3:229`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_BestialMauling(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:234`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PoisonousBite() -> Any:
    """``UtilityAI_PetAttack.au3:249`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_PoisonousBite(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:254`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotPoisoned")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Pounce() -> Any:
    """``UtilityAI_PetAttack.au3:269`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_Pounce(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:274`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MelandrusAssaultPvP() -> Any:
    """``UtilityAI_PetAttack.au3:289`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_MelandrusAssaultPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:294`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnragedLungePvP() -> Any:
    """``UtilityAI_PetAttack.au3:313`` -- transcribed from GwAu3's own body."""

    if Anti_PetAttack():
        return False
    return True


def BestTarget_EnragedLungePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_PetAttack.au3:318`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


__all__ = [
    "BestTarget_BestialMauling",
    "BestTarget_BestialPounce",
    "BestTarget_BrutalStrike",
    "BestTarget_DisruptingLunge",
    "BestTarget_EnragedLunge",
    "BestTarget_EnragedLungePvP",
    "BestTarget_FeralLunge",
    "BestTarget_FerociousStrike",
    "BestTarget_MaimingStrike",
    "BestTarget_MelandrusAssault",
    "BestTarget_MelandrusAssaultPvP",
    "BestTarget_PoisonousBite",
    "BestTarget_Pounce",
    "BestTarget_PredatorsPounce",
    "BestTarget_SavagePounce",
    "BestTarget_ScavengerStrike",
    "CanUse_BestialMauling",
    "CanUse_BestialPounce",
    "CanUse_BrutalStrike",
    "CanUse_DisruptingLunge",
    "CanUse_EnragedLunge",
    "CanUse_EnragedLungePvP",
    "CanUse_FeralLunge",
    "CanUse_FerociousStrike",
    "CanUse_MaimingStrike",
    "CanUse_MelandrusAssault",
    "CanUse_MelandrusAssaultPvP",
    "CanUse_PoisonousBite",
    "CanUse_Pounce",
    "CanUse_PredatorsPounce",
    "CanUse_SavagePounce",
    "CanUse_ScavengerStrike",
]
