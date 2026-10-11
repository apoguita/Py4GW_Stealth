"""GwAu3's ``UtilityAI_Form.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **34 of this file's 34 are transcribed and 0
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
from .uai_agent import UAI_GetPlayerInfo
from .uai_effects import UAI_GetPlayerEffectInfo


def CanUse_AvatarOfBalthazar() -> Any:
    """``UtilityAI_Form.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_Form():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_BALTHAZAR, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AvatarOfBalthazar(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:14`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfDwayna() -> Any:
    """``UtilityAI_Form.au3:23`` -- transcribed from GwAu3's own body."""

    if Anti_Form():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_DWAYNA, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AvatarOfDwayna(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:29`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfGrenth() -> Any:
    """``UtilityAI_Form.au3:38`` -- transcribed from GwAu3's own body."""

    if Anti_Form():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_GRENTH, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AvatarOfGrenth(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:44`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfLyssa() -> Any:
    """``UtilityAI_Form.au3:53`` -- transcribed from GwAu3's own body."""

    if Anti_Form():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_LYSSA, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AvatarOfLyssa(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:59`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfMelandru() -> Any:
    """``UtilityAI_Form.au3:68`` -- transcribed from GwAu3's own body."""

    if Anti_Form():
        return False
    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_MELANDRU, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AvatarOfMelandru(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:74`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfGrenthSnowFightingSkill() -> Any:
    """``UtilityAI_Form.au3:83`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_GRENTH_SNOW_FIGHTING_SKILL, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_AvatarOfGrenthSnowFightingSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:89`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfDwaynaSnowFightingSkill() -> Any:
    """``UtilityAI_Form.au3:98`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_DWAYNA_SNOW_FIGHTING_SKILL, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_AvatarOfDwaynaSnowFightingSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:104`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanBlessing() -> Any:
    """``UtilityAI_Form.au3:113`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_URSAN_BLESSING, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_UrsanBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:119`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenBlessing() -> Any:
    """``UtilityAI_Form.au3:128`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VOLFEN_BLESSING, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_VolfenBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:134`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenBlessing() -> Any:
    """``UtilityAI_Form.au3:143`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_RAVEN_BLESSING, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_RavenBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:149`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BearForm() -> Any:
    """``UtilityAI_Form.au3:158`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BEAR_FORM, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_BearForm(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:164`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SiegeDevourer() -> Any:
    """``UtilityAI_Form.au3:173`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SIEGE_DEVOURER, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_SiegeDevourer(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:179`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Hide() -> Any:
    """``UtilityAI_Form.au3:188`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_HIDE, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_Hide(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:194`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeignDeath() -> Any:
    """``UtilityAI_Form.au3:203`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_FEIGN_DEATH, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_FeignDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:209`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfGrenthPvP() -> Any:
    """``UtilityAI_Form.au3:218`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_GRENTH_PVP, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_AvatarOfGrenthPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:224`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfDwaynaPvP() -> Any:
    """``UtilityAI_Form.au3:233`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_DWAYNA_PVP, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_AvatarOfDwaynaPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AvatarOfMelandruPvP() -> Any:
    """``UtilityAI_Form.au3:248`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AVATAR_OF_MELANDRU_PVP, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    if Anti_Form():
        return False
    return True


def BestTarget_AvatarOfMelandruPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Form.au3:254`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AvatarOfBalthazar",
    "BestTarget_AvatarOfDwayna",
    "BestTarget_AvatarOfDwaynaPvP",
    "BestTarget_AvatarOfDwaynaSnowFightingSkill",
    "BestTarget_AvatarOfGrenth",
    "BestTarget_AvatarOfGrenthPvP",
    "BestTarget_AvatarOfGrenthSnowFightingSkill",
    "BestTarget_AvatarOfLyssa",
    "BestTarget_AvatarOfMelandru",
    "BestTarget_AvatarOfMelandruPvP",
    "BestTarget_BearForm",
    "BestTarget_FeignDeath",
    "BestTarget_Hide",
    "BestTarget_RavenBlessing",
    "BestTarget_SiegeDevourer",
    "BestTarget_UrsanBlessing",
    "BestTarget_VolfenBlessing",
    "CanUse_AvatarOfBalthazar",
    "CanUse_AvatarOfDwayna",
    "CanUse_AvatarOfDwaynaPvP",
    "CanUse_AvatarOfDwaynaSnowFightingSkill",
    "CanUse_AvatarOfGrenth",
    "CanUse_AvatarOfGrenthPvP",
    "CanUse_AvatarOfGrenthSnowFightingSkill",
    "CanUse_AvatarOfLyssa",
    "CanUse_AvatarOfMelandru",
    "CanUse_AvatarOfMelandruPvP",
    "CanUse_BearForm",
    "CanUse_FeignDeath",
    "CanUse_Hide",
    "CanUse_RavenBlessing",
    "CanUse_SiegeDevourer",
    "CanUse_UrsanBlessing",
    "CanUse_VolfenBlessing",
]
