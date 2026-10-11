"""GwAu3's ``UtilityAI_Preparation.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **36 of this file's 36 are transcribed and 0
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


def CanUse_MelandrusArrows() -> Any:
    """``UtilityAI_Preparation.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_MelandrusArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:13`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MarksmansWager() -> Any:
    """``UtilityAI_Preparation.au3:18`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_MarksmansWager(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:23`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IgniteArrows() -> Any:
    """``UtilityAI_Preparation.au3:28`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_IgniteArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:33`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReadTheWind() -> Any:
    """``UtilityAI_Preparation.au3:42`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_ReadTheWind(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:47`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KindleArrows() -> Any:
    """``UtilityAI_Preparation.au3:56`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_KindleArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:61`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChokingGas() -> Any:
    """``UtilityAI_Preparation.au3:70`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_ChokingGas(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:75`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ApplyPoison() -> Any:
    """``UtilityAI_Preparation.au3:84`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_ApplyPoison(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:89`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SeekingArrows() -> Any:
    """``UtilityAI_Preparation.au3:98`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_SeekingArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:103`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TrappersFocus() -> Any:
    """``UtilityAI_Preparation.au3:112`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_TrappersFocus(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:117`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_YellowSnow() -> Any:
    """``UtilityAI_Preparation.au3:122`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_YellowSnow(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:127`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CorruptedBreath() -> Any:
    """``UtilityAI_Preparation.au3:136`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_CorruptedBreath(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:141`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlassArrows() -> Any:
    """``UtilityAI_Preparation.au3:150`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_GlassArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:155`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BarbedArrows() -> Any:
    """``UtilityAI_Preparation.au3:164`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_BarbedArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:169`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisruptingAccuracy() -> Any:
    """``UtilityAI_Preparation.au3:178`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_DisruptingAccuracy(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:183`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RapidFire() -> Any:
    """``UtilityAI_Preparation.au3:192`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_RapidFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:197`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExpertFocus() -> Any:
    """``UtilityAI_Preparation.au3:206`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_ExpertFocus(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:211`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReadTheWindPvP() -> Any:
    """``UtilityAI_Preparation.au3:220`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_ReadTheWindPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:225`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlassArrowsPvP() -> Any:
    """``UtilityAI_Preparation.au3:230`` -- transcribed from GwAu3's own body."""

    if Anti_Preparation():
        return False
    return True


def BestTarget_GlassArrowsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Preparation.au3:235`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_ApplyPoison",
    "BestTarget_BarbedArrows",
    "BestTarget_ChokingGas",
    "BestTarget_CorruptedBreath",
    "BestTarget_DisruptingAccuracy",
    "BestTarget_ExpertFocus",
    "BestTarget_GlassArrows",
    "BestTarget_GlassArrowsPvP",
    "BestTarget_IgniteArrows",
    "BestTarget_KindleArrows",
    "BestTarget_MarksmansWager",
    "BestTarget_MelandrusArrows",
    "BestTarget_RapidFire",
    "BestTarget_ReadTheWind",
    "BestTarget_ReadTheWindPvP",
    "BestTarget_SeekingArrows",
    "BestTarget_TrappersFocus",
    "BestTarget_YellowSnow",
    "CanUse_ApplyPoison",
    "CanUse_BarbedArrows",
    "CanUse_ChokingGas",
    "CanUse_CorruptedBreath",
    "CanUse_DisruptingAccuracy",
    "CanUse_ExpertFocus",
    "CanUse_GlassArrows",
    "CanUse_GlassArrowsPvP",
    "CanUse_IgniteArrows",
    "CanUse_KindleArrows",
    "CanUse_MarksmansWager",
    "CanUse_MelandrusArrows",
    "CanUse_RapidFire",
    "CanUse_ReadTheWind",
    "CanUse_ReadTheWindPvP",
    "CanUse_SeekingArrows",
    "CanUse_TrappersFocus",
    "CanUse_YellowSnow",
]
